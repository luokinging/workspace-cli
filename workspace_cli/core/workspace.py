import shutil
from pathlib import Path
from typing import List
from workspace_cli.models import WorkspaceConfig, RepoConfig, WorkspaceEntry
from workspace_cli.utils.git import create_worktree, remove_worktree, GitError, submodule_update
from workspace_cli.config import save_config

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
    
    # 4. Update Config
    config.workspaces[name] = WorkspaceEntry(path=str(workspace_path))
    save_config(config, Path.cwd() / "workspace.json") # Assuming cwd is correct place? Or config.base_path.parent?
    # We should probably save to where we loaded from, but we don't have that path here easily unless we pass it.
    # For now, let's assume we save to base_path/workspace.json or similar.
    # Actually, config.py load_config searches.
    # Let's assume standard location: base_path/workspace.json? 
    # Or better, we should pass the config path to create_workspace or save_config.
    # Let's try to save to base_path / "workspace.json" for now as default.
    save_path = config.base_path / "workspace.json"
    save_config(config, save_path)
    print(f"Updated config at {save_path}")

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
    
    # 2. Update Config
    if name in config.workspaces:
        del config.workspaces[name]
        save_path = config.base_path / "workspace.json"
        save_config(config, save_path)
        print(f"Updated config at {save_path}")

def get_status(config: WorkspaceConfig) -> None:
    """Print status of workspaces."""
    # List all directories matching pattern
    base_name = config.base_path.name
    parent_dir = config.base_path.parent
    
    print(f"Base Workspace: {base_name} ({config.base_path})")
    print("Workspaces:")
    
    for name, entry in config.workspaces.items():
        print(f"  - {name} ({entry.path})")
