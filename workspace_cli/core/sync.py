import shutil
import time
import subprocess
import os
import signal
import typer
from pathlib import Path
from typing import List
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.utils.git import (
    run_git_cmd, get_diff_files, checkout_new_branch, GitError, get_current_branch
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
            typer.secho(f"Warning: Another preview process (PID {pid}) might be running.", fg=typer.colors.YELLOW)
            typer.secho("Please stop it before starting a new one, or remove the PID file if it's stale.", fg=typer.colors.YELLOW)
            # We could exit here, or just warn. User said "previous one didn't stop".
            # Let's try to kill it? No, that's dangerous.
            # Let's just warn for now, or maybe fail?
            # User said "workspace file accumulation problem".
            # If we run two previews, they might fight over the same branch.
            raise SyncError(f"Preview already running (PID {pid}). Please stop it first.")
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
        pid_file.unlink()

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
        
        # 2. Iterate over repos
        for repo in config.repos:
            source_repo_path = source_workspace_path / repo.path
            target_repo_path = target_workspace_path / repo.path
            
            if not source_repo_path.exists():
                print(f"Skipping {repo.name}: Source not found.")
                continue
                
            print(f"Syncing repo: {repo.name}")
            
            try:
                # 2.1 Source Side: Get changed files
                run_git_cmd(["add", "-u"], source_repo_path)
                changed_files = get_diff_files(source_repo_path, "main")
                
                # 2.2 Target Side: Prepare Preview Branch
                # Always use 'preview' branch
                preview_branch = "preview"
                
                # Checkout main first to be clean (if needed, or just force checkout preview)
                # If we are already on preview, we might want to reset it?
                # Let's try to checkout main then delete preview then create preview?
                # Or just force create/reset preview.
                
                # If we are on preview branch, we can't delete it.
                # So checkout main first.
                try:
                    run_git_cmd(["checkout", "main"], target_repo_path)
                except GitError:
                    pass # Maybe main doesn't exist?
                
                checkout_new_branch(target_repo_path, preview_branch, force=True)
                
                # Clean target
                run_git_cmd(["clean", "-fd"], target_repo_path)
                run_git_cmd(["restore", "."], target_repo_path)
                
                if not changed_files:
                    print(f"  No changes in {repo.name}")
                    continue
                    
                print(f"  Found {len(changed_files)} changed files.")
                
                # 2.3 Copy Files
                for file_rel_path in changed_files:
                    src_file = source_repo_path / file_rel_path
                    dst_file = target_repo_path / file_rel_path
                    
                    if src_file.exists():
                        # Copy file
                        dst_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dst_file)
                        typer.secho(f"    Copied: {file_rel_path}", fg=typer.colors.GREEN)
                    else:
                        # File deleted in source?
                        if dst_file.exists():
                            dst_file.unlink()
                            typer.secho(f"    Deleted: {file_rel_path}", fg=typer.colors.RED)
                            
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

def sync_rules(config: WorkspaceConfig) -> None:
    """Sync rules repo."""
    if not config.rules_repo_name:
        print("No rules repo configured.")
        return

    # Find rules repo config
    rules_repo_config = next((r for r in config.repos if r.name == config.rules_repo_name), None)
    if not rules_repo_config:
        print(f"Rules repo '{config.rules_repo_name}' not found in repos list.")
        return

    # 1. Locate Rules Repo in current workspace (Source)
    # We assume we are running this from the source workspace
    # How do we know the source workspace?
    # The CLI doesn't take workspace arg for syncrule, it assumes current context.
    # But `load_config` tries to find workspace.json.
    # If we are in a workspace directory, `config.base_path` is the root.
    # We need to know WHICH workspace we are in.
    
    # Let's try to infer current workspace name from CWD
    cwd = Path.cwd()
    base_name = config.base_path.name
    
    # Check if we are in a workspace dir: {base_name}-{name}
    # Or if we are in a repo subdir
    
    # This is tricky without explicit context.
    # Let's assume the user runs this from the workspace root or a repo inside it.
    
    current_workspace_path = None
    for parent in [cwd] + list(cwd.parents):
        if parent.name.startswith(f"{base_name}-") and parent.parent == config.base_path.parent:
            current_workspace_path = parent
            break
    
    if not current_workspace_path:
        print("Could not determine current workspace. Please run from within a workspace.")
        return

    workspace_name = current_workspace_path.name[len(base_name)+1:]
    print(f"Syncing rules from workspace: {workspace_name}")

    source_rules_path = current_workspace_path / rules_repo_config.path
    
    if not source_rules_path.exists():
        print(f"Rules repo not found at {source_rules_path}")
        return

    try:
        # 2. Commit and Push in Source
        print("Committing changes in rules repo...")
        run_git_cmd(["add", "."], source_rules_path)
        try:
            run_git_cmd(["commit", "-m", f"Sync rules from {workspace_name}"], source_rules_path)
        except GitError:
            print("Nothing to commit.")
        
        print("Pushing changes...")
        current_branch = get_current_branch(source_rules_path)
        # Push to main so others can pull it
        run_git_cmd(["push", "origin", f"{current_branch}:main"], source_rules_path)
        
        # 3. Update other workspaces
        # Iterate over all sibling workspaces
        parent_dir = config.base_path.parent
        for path in parent_dir.iterdir():
            if path.is_dir() and path.name.startswith(f"{base_name}-") and path != current_workspace_path:
                other_ws_name = path.name[len(base_name)+1:]
                other_rules_path = path / rules_repo_config.path
                
                if other_rules_path.exists():
                    print(f"Updating rules in {other_ws_name}...")
                    try:
                        run_git_cmd(["pull", "origin", "main"], other_rules_path)
                        # Or merge?
                        # run_git_cmd(["merge", "origin/main"], other_rules_path)
                    except GitError as e:
                        print(f"Failed to update {other_ws_name}: {e}")
                        
    except GitError as e:
        print(f"Git error during sync: {e}")
