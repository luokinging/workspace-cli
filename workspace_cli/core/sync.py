import shutil
import time
import subprocess
import os
import signal
import typer
from pathlib import Path
from typing import List, Optional
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.utils.git import (
    run_git_cmd, get_diff_files, checkout_new_branch, GitError, get_current_branch,
    get_merge_base, submodule_update, fetch_remote, merge_branch, get_commit_hash
)

class SyncError(Exception):
    pass

def _get_pid_file(config: WorkspaceConfig) -> Path:
    return config.base_path.parent / ".workspace_preview.pid"

def _check_pid_file(pid_file: Path):
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)
            
            typer.secho(f"Warning: Another preview process (PID {pid}) is running.", fg=typer.colors.YELLOW)
            typer.secho("Stopping it to start new preview...", fg=typer.colors.YELLOW)
            
            try:
                os.kill(pid, signal.SIGTERM)
                # Wait for it to exit
                for _ in range(50):  # Wait up to 5 seconds
                    time.sleep(0.1)
                    os.kill(pid, 0)
                
                # If still running, force kill
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Process is gone
                
        except ProcessLookupError:
            # Stale PID file
            pid_file.unlink()
        except ValueError:
            # Corrupt PID file
            pid_file.unlink()

def _create_pid_file(pid_file: Path):
    pid_file.write_text(str(os.getpid()))

def _remove_pid_file(pid_file: Path):
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            if pid == os.getpid():
                pid_file.unlink()
        except (ValueError, ProcessLookupError, OSError):
            pass

def _get_current_workspace_path(config: WorkspaceConfig) -> Optional[Path]:
    cwd = Path.cwd()
    base_name = config.base_path.name
    # Check parents up to root
    for parent in [cwd] + list(cwd.parents):
        if (parent.name == base_name or parent.name.startswith(f"{base_name}-")) and parent.parent == config.base_path.parent:
            return parent
    return None

def init_preview(workspace_name: str, config: WorkspaceConfig) -> None:
    """Initialize preview workspace."""
    typer.secho(f"Initializing preview for workspace: {workspace_name}", fg=typer.colors.BLUE)
    
    pid_file = _get_pid_file(config)
    _check_pid_file(pid_file)
    _create_pid_file(pid_file)

    try:
        # 1. Identify Source and Preview Workspaces
        source_workspace_path = config.base_path.parent / f"{config.base_path.name}-{workspace_name}"
        target_workspace_path = config.base_path
        
        if not source_workspace_path.exists():
            raise SyncError(f"Source workspace not found: {source_workspace_path}")
            
        print(f"Source: {source_workspace_path}")
        print(f"Target: {target_workspace_path}")
        
        # 2. Iterate over repos (submodules)
        for repo in config.repos:
            source_repo_path = source_workspace_path / repo.path
            target_repo_path = target_workspace_path / repo.path
            
            if not source_repo_path.exists():
                print(f"Skipping {repo.name}: Source not found.")
                continue
                
            print(f"Syncing repo: {repo.name}")
            
            try:
                # 2.1 Target Side: Update to latest main
                print(f"  Updating target {repo.name} to origin/main...")
                fetch_remote(target_repo_path)
                merge_branch(target_repo_path, "origin/main")
                target_main_commit = get_commit_hash(target_repo_path, "HEAD")

                # 2.2 Source Side: Get current commit
                source_commit = get_commit_hash(source_repo_path, "HEAD")

                # 2.3 Find Common Root
                common_root = get_merge_base(target_repo_path, source_commit, target_main_commit) # Wait, need source commit in target repo?
                # Git merge-base requires both commits to be present in the repo.
                # Since source and target are different worktrees/clones, they might not have each other's objects if not pushed.
                # BUT, here we assume they share the same remote.
                # If source has local commits not pushed, target won't know them.
                # So we can only find common root based on what target knows.
                # Actually, if we use file sync, we don't strictly need the common root for git operations IF we just overwrite files.
                # BUT the requirement says: "Reset to Common Root".
                # If Source has local commits, Target can't reset to them.
                # Target can only reset to a commit it has.
                # If Source hasn't pushed, Target only has origin/main.
                # So Common Root is likely origin/main (or whatever Source branched from).
                
                # Issue: `git merge-base` needs both commits in the SAME repo object database.
                # If these are separate clones, they don't share objects.
                # If they are worktrees of the same repo, they share objects!
                # Are submodules worktrees? Usually no, they are separate .git dirs inside the parent worktree.
                # UNLESS we set them up as worktrees too? No, standard submodules are separate clones (or share .git/modules).
                # If they share .git/modules, they might share objects.
                
                # Assumption: Submodules are standard.
                # If we can't find the source commit in target, we fallback to target's HEAD (main)?
                # Or we fetch source's objects into target?
                # `git fetch source_repo_path`?
                
                # Let's try to fetch from source repo into target repo to ensure we have the objects.
                print(f"  Fetching objects from source submodule...")
                run_git_cmd(["fetch", str(source_repo_path)], target_repo_path)
                
                # Now we can find merge base
                common_root = get_merge_base(target_repo_path, source_commit, target_main_commit)
                print(f"  Common root: {common_root[:7]}")

                # 2.4 Prepare Preview Branch in Target
                preview_branch = "preview"
                # Reset to common root
                # checkout -B preview <common_root>
                run_git_cmd(["checkout", "-B", preview_branch, common_root], target_repo_path)
                
                # 2.5 Sync Files (Copy)
                # We want to copy ALL tracked files from source to target.
                # Or just copy everything excluding ignored?
                # `shutil.copytree` with `dirs_exist_ok=True` copies everything.
                # We should respect .gitignore.
                # A simple way: `git ls-files` in source, then copy those.
                
                source_files = run_git_cmd(["ls-files"], source_repo_path).splitlines()
                # Also need to handle untracked but not ignored?
                # `git ls-files --others --exclude-standard`
                untracked_files = run_git_cmd(["ls-files", "--others", "--exclude-standard"], source_repo_path).splitlines()
                all_files = source_files + untracked_files
                
                print(f"  Syncing {len(all_files)} files...")
                for file_rel_path in all_files:
                    src_file = source_repo_path / file_rel_path
                    dst_file = target_repo_path / file_rel_path
                    
                    if src_file.exists():
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                
                # What about deleted files?
                # If file exists in Target (from Common Root) but not in Source, it should be deleted.
                # We can list files in Target (current preview branch) and check if they exist in Source.
                target_files = run_git_cmd(["ls-files"], target_repo_path).splitlines()
                for file_rel_path in target_files:
                    src_file = source_repo_path / file_rel_path
                    dst_file = target_repo_path / file_rel_path
                    if not src_file.exists() and dst_file.exists():
                        dst_file.unlink()
                        # print(f"    Deleted: {file_rel_path}")

            except GitError as e:
                print(f"  Git Error in {repo.name}: {e}")
                raise SyncError(f"Sync failed for {repo.name}")
    except Exception:
        _remove_pid_file(pid_file)
        raise

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Watcher(FileSystemEventHandler):
    def __init__(self, source_root: Path, target_root: Path, repo_path: Path):
        self.source_root = source_root
        self.target_root = target_root
        self.repo_path = repo_path # Relative path of repo in workspace

    def _is_ignored(self, path: str) -> bool:
        try:
            cwd = self.source_root / self.repo_path
            rel_path = Path(path).relative_to(cwd)
            subprocess.run(
                ["git", "check-ignore", "-q", str(rel_path)],
                cwd=str(cwd),
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            return False

    def _sync_file(self, src_path: str, event_type: str = "UPDATED"):
        try:
            rel_path = Path(src_path).relative_to(self.source_root / self.repo_path)
            dst_path = self.target_root / self.repo_path / rel_path
            
            if self._is_ignored(src_path):
                return

            color = typer.colors.WHITE
            if event_type == "CREATED":
                color = typer.colors.GREEN
            elif event_type == "DELETED":
                color = typer.colors.RED
            elif event_type == "UPDATED":
                color = typer.colors.YELLOW

            if Path(src_path).exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                typer.secho(f"[{event_type}] {rel_path}", fg=color)
            else:
                if dst_path.exists():
                    dst_path.unlink()
                    typer.secho(f"[{event_type}] {rel_path}", fg=color)
        except Exception as e:
            print(f"Error syncing {src_path}: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path, "UPDATED")

    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path, "CREATED")

    def on_deleted(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path, "DELETED")
            
    def on_moved(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path, "DELETED")
            self._sync_file(event.dest_path, "CREATED")

def start_preview(workspace_name: str, config: WorkspaceConfig, once: bool = False) -> None:
    """Start preview sync and watch."""
    try:
        init_preview(workspace_name, config)
    except SyncError as e:
        typer.secho(str(e), err=True, fg=typer.colors.RED)
        return

    if once:
        typer.secho("Preview sync completed (once mode).", fg=typer.colors.GREEN)
        _remove_pid_file(_get_pid_file(config))
        return
    
    source_workspace_path = config.base_path.parent / f"{config.base_path.name}-{workspace_name}"
    target_workspace_path = config.base_path
    
    observers = []
    
    print("Starting watchers...")
    
    for repo in config.repos:
        source_repo_path = source_workspace_path / repo.path
        
        if not source_repo_path.exists():
            continue
            
        event_handler = Watcher(source_workspace_path, target_workspace_path, repo.path)
        observer = Observer()
        observer.schedule(event_handler, str(source_repo_path), recursive=True)
        observer.start()
        observers.append(observer)
        print(f"Watching {repo.name} at {source_repo_path}")
    
    # Handle SIGTERM to ensure cleanup
    def handle_sigterm(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping preview...")
        for o in observers:
            o.stop()
        for o in observers:
            o.join()
    finally:
        _remove_pid_file(_get_pid_file(config))

def sync_workspaces(config: WorkspaceConfig) -> None:
    """
    Sync all workspaces.
    1. Update Base Workspace (pull origin main).
    2. Update all sibling workspaces (merge origin/main + update submodules).
    """
    base_path = config.base_path
    print(f"Syncing Base Workspace: {base_path}")
    
    try:
        # 1. Update Base
        print("  Pulling origin main...")
        run_git_cmd(["pull", "origin", "main"], base_path)
        print("  Updating submodules...")
        submodule_update(base_path)
    except GitError as e:
        print(f"Error updating Base Workspace: {e}")
        return

    # 2. Update Siblings
    base_name = base_path.name
    parent_dir = base_path.parent
    
    print("Syncing Sibling Workspaces...")
    for path in parent_dir.iterdir():
        if path.is_dir() and path.name.startswith(f"{base_name}-") and path.name != base_name:
            ws_name = path.name[len(base_name)+1:]
            print(f"  Syncing {ws_name}...")
            
            try:
                # Merge origin/main
                # Note: We are merging origin/main into the current branch (stand)
                print(f"    Merging origin/main...")
                fetch_remote(path)
                merge_branch(path, "origin/main")
                
                # Update submodules
                print(f"    Updating submodules...")
                submodule_update(path)
                
            except GitError as e:
                print(f"    Failed to sync {ws_name}: {e}")

    # 3. Handle workspace_expand_folder
    if config.workspace_expand_folder:
        expand_folder_name = config.workspace_expand_folder
        source_expand_path = base_path / expand_folder_name
        
        if not source_expand_path.exists():
            print(f"Expand folder '{expand_folder_name}' not found in Base Workspace.")
            return

        print(f"Expanding content from '{expand_folder_name}' to all sibling workspaces...")
        
        # Get list of items to expand
        items_to_expand = list(source_expand_path.iterdir())
        if not items_to_expand:
            print(f"No items found in '{expand_folder_name}'.")
            return

        for path in parent_dir.iterdir():
            if path.is_dir() and path.name.startswith(f"{base_name}-") and path.name != base_name:
                ws_name = path.name[len(base_name)+1:]
                print(f"  Expanding to {ws_name}...")
                
                for item in items_to_expand:
                    rel_name = item.name
                    target_path = path / rel_name
                    
                    try:
                        # 1. Delete existing
                        if target_path.exists():
                            if target_path.is_dir():
                                shutil.rmtree(target_path)
                            else:
                                target_path.unlink()
                        
                        # 2. Copy new
                        if item.is_dir():
                            shutil.copytree(item, target_path)
                        else:
                            shutil.copy2(item, target_path)
                        # print(f"    Expanded: {rel_name}")
                        
                    except Exception as e:
                        print(f"    Error expanding {rel_name} to {ws_name}: {e}")
