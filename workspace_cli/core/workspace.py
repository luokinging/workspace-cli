import shutil
from pathlib import Path
from typing import List
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.utils.git import create_worktree, remove_worktree, GitError, checkout_new_branch

class WorkspaceError(Exception):
    pass

def create_workspace(name: str, config: WorkspaceConfig) -> None:
    """Create a new workspace."""
    # 1. Define new workspace path
    workspace_path = config.base_path.parent / f"{config.base_path.name}-{name}"
    
    if workspace_path.exists():
        raise WorkspaceError(f"Workspace directory already exists: {workspace_path}")
    
    workspace_path.mkdir(parents=True)
    
    # 2. Iterate over repos and create worktrees
    for repo in config.repos:
        # Source repo path (in the base workspace)
        source_repo_path = config.base_path / repo.path
        
        if not source_repo_path.exists():
            print(f"Warning: Source repo not found at {source_repo_path}, skipping.")
            continue
            
        # Target repo path (in the new workspace)
        target_repo_path = workspace_path / repo.path
        
        # Create parent dirs if needed
        target_repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Branch name: workspace-{name}/stand
        branch_name = f"workspace-{name}/stand"
        
        try:
            print(f"Creating worktree for {repo.name} at {target_repo_path}...")
            create_worktree(source_repo_path, branch_name, target_repo_path)
        except GitError as e:
            # Cleanup on failure?
            # For now, just raise
            raise WorkspaceError(f"Failed to create worktree for {repo.name}: {e}")

    print(f"Workspace '{name}' created successfully at {workspace_path}")
    # We do not switch base repos to preview branch here anymore.
    # The preview command will handle that when needed.

def delete_workspace(name: str, config: WorkspaceConfig) -> None:
    """Delete a workspace."""
    workspace_path = config.base_path.parent / f"{config.base_path.name}-{name}"
    
    if not workspace_path.exists():
        raise WorkspaceError(f"Workspace not found: {workspace_path}")
    
    # 1. Remove worktrees
    # We need to know which repos are in there. We can use the config.
    for repo in config.repos:
        target_repo_path = workspace_path / repo.path
        if target_repo_path.exists():
            try:
                print(f"Removing worktree for {repo.name}...")
                remove_worktree(target_repo_path)
            except GitError as e:
                print(f"Warning: Failed to remove worktree {repo.name}: {e}")
                # Continue to try deleting others and the dir
    
    # 2. Delete directory
    try:
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
            print(f"Workspace '{name}' deleted.")
    except Exception as e:
        raise WorkspaceError(f"Failed to delete workspace directory: {e}")

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
