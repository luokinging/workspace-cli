import shutil
import time
import subprocess
from pathlib import Path
from typing import List
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.utils.git import (
    run_git_cmd, get_diff_files, checkout_new_branch, GitError, get_current_branch
)

class SyncError(Exception):
    pass

def init_preview(workspace_name: str, config: WorkspaceConfig) -> None:
    """Initialize preview workspace."""
    print(f"Initializing preview for workspace: {workspace_name}")
    
    # 1. Identify Source and Preview Workspaces
    # Source: The workspace we are syncing FROM (workspace_name)
    # Preview: The base workspace (config.base_path) acting as the preview environment?
    # Wait, the design says: "将 `workspace-lulu` 内容同步到 preview workspace。"
    # And "Preview workspace" usually implies a dedicated place or the main workspace.
    # Let's assume:
    # Source: The feature workspace (e.g. workspace-lulu)
    # Target (Preview): The base workspace (e.g. main-web-ui) OR a specific preview workspace.
    # The design says: "显示 preview workspace preview branch"
    # And "将 Source 侧的变更文件复制过来"
    
    # Let's assume the Target is the `config.base_path` (the root workspace).
    # And we are syncing FROM `workspace_name` TO `base_path`.
    
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
        
        # 2.1 Source Side: Get changed files
        # We need to see what changed in the source workspace compared to main?
        # Or just take whatever is currently there?
        # Design: "git add -u", "git diff --name-only main"
        
        try:
            # Ensure we are tracking all changes
            run_git_cmd(["add", "-u"], source_repo_path)
            
            # Get changed files relative to main
            # Assuming 'main' is the base branch. 
            # We might need to fetch main first?
            # Let's assume main is available.
            changed_files = get_diff_files(source_repo_path, "main")
            
            if not changed_files:
                print(f"  No changes in {repo.name}")
                continue
                
            print(f"  Found {len(changed_files)} changed files.")
            
            # 2.2 Target Side: Prepare Preview Branch
            # Checkout main first to be clean
            run_git_cmd(["checkout", "main"], target_repo_path)
            
            # Create/Reset preview branch
            preview_branch = f"workspace-{workspace_name}/preview"
            checkout_new_branch(target_repo_path, preview_branch, force=True)
            
            # Clean target
            # git clean -fd
            run_git_cmd(["clean", "-fd"], target_repo_path)
            # git restore .
            run_git_cmd(["restore", "."], target_repo_path)
            
            # 2.3 Copy Files
            for file_rel_path in changed_files:
                src_file = source_repo_path / file_rel_path
                dst_file = target_repo_path / file_rel_path
                
                if src_file.exists():
                    # Copy file
                    dst_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_file, dst_file)
                    print(f"    Copied: {file_rel_path}")
                else:
                    # File deleted in source?
                    if dst_file.exists():
                        dst_file.unlink()
                        print(f"    Deleted: {file_rel_path}")
                        
        except GitError as e:
            print(f"  Git Error in {repo.name}: {e}")
            raise SyncError(f"Sync failed for {repo.name}")

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class Watcher(FileSystemEventHandler):
    def __init__(self, source_root: Path, target_root: Path, repo_path: Path):
        self.source_root = source_root
        self.target_root = target_root
        self.repo_path = repo_path # Relative path of repo in workspace

    def _is_ignored(self, path: str) -> bool:
        # Check if file is ignored by git
        # We need to run git check-ignore in the source repo
        try:
            # path is absolute, we need relative to source repo root
            # source_repo_root = self.source_root / self.repo_path
            # But wait, the observer is watching the source_repo_root?
            # Let's assume we set up one observer per repo.
            
            cwd = self.source_root / self.repo_path
            rel_path = Path(path).relative_to(cwd)
            
            # git check-ignore -q <path> returns 0 if ignored, 1 if not
            subprocess.run(
                ["git", "check-ignore", "-q", str(rel_path)],
                cwd=str(cwd),
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False
        except Exception:
            # If relative_to fails (shouldn't happen if logic is correct), assume not ignored?
            return False

    def _sync_file(self, src_path: str):
        # Calculate target path
        try:
            rel_path = Path(src_path).relative_to(self.source_root / self.repo_path)
            dst_path = self.target_root / self.repo_path / rel_path
            
            if self._is_ignored(src_path):
                return

            print(f"Syncing: {rel_path}")
            if Path(src_path).exists():
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
            else:
                if dst_path.exists():
                    dst_path.unlink()
        except Exception as e:
            print(f"Error syncing {src_path}: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._sync_file(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory:
            # Handle move as delete + create
            # Or just sync dest
            self._sync_file(event.dest_path)
            # And delete src?
            # _sync_file handles deletion if src doesn't exist, 
            # but here src_path is the OLD path.
            # So we should sync both.
            self._sync_file(event.src_path)

def start_preview(workspace_name: str, config: WorkspaceConfig) -> None:
    """Start preview sync and watch."""
    init_preview(workspace_name, config)
    
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
