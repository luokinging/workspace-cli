import shutil
from pathlib import Path
from typing import List
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.utils.git import create_worktree, remove_worktree, GitError, submodule_update

class WorkspaceError(Exception):
    pass

def create_workspace(name: str, config: WorkspaceConfig) -> None:
    """Create a new workspace."""
    # 1. Define new workspace path
    workspace_path = config.base_path.parent / f"{config.base_path.name}-{name}"
    
    if workspace_path.exists():
        raise WorkspaceError(f"Workspace directory already exists: {workspace_path}")
    
    # 2. Create Worktree for the Workspace Repo
    # Branch name: workspace-{name}/stand
    branch_name = f"workspace-{name}/stand"
    
    try:
        print(f"Creating workspace worktree at {workspace_path}...")
        create_worktree(config.base_path, branch_name, workspace_path)
    except GitError as e:
        raise WorkspaceError(f"Failed to create workspace worktree: {e}")

    # 3. Initialize Submodules
    try:
        print("Initializing submodules...")
        submodule_update(workspace_path, init=True, recursive=True)
    except GitError as e:
        # Cleanup?
        raise WorkspaceError(f"Failed to initialize submodules: {e}")

    print(f"Workspace '{name}' created successfully at {workspace_path}")

def delete_workspace(name: str, config: WorkspaceConfig) -> None:
    """Delete a workspace."""
    workspace_path = config.base_path.parent / f"{config.base_path.name}-{name}"
    
    if not workspace_path.exists():
        raise WorkspaceError(f"Workspace not found: {workspace_path}")
    
    # 1. Remove worktree (Workspace Repo)
    try:
        print(f"Removing workspace worktree...")
        remove_worktree(workspace_path)
    except GitError as e:
        print(f"Warning: Failed to remove worktree: {e}")
        # Try to delete dir manually if git failed
        if workspace_path.exists():
             shutil.rmtree(workspace_path)

    print(f"Workspace '{name}' deleted.")

def get_status(config: WorkspaceConfig) -> None:
    """Print status of workspaces."""
    # List all directories matching pattern
    base_name = config.base_path.name
    parent_dir = config.base_path.parent
    
    print(f"Base Workspace: {base_name} ({config.base_path})")
    print("Workspaces:")
    
    for path in parent_dir.iterdir():
        if path.is_dir() and path.name.startswith(f"{base_name}-") and path.name != base_name:
            ws_name = path.name[len(base_name)+1:]
            print(f"  - {ws_name} ({path})")
