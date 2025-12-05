import json
import configparser
from pathlib import Path
from typing import List, Optional
from workspace_cli.models import WorkspaceConfig, RepoConfig, WorkspaceEntry

def get_managed_repos(base_path: Path) -> List[RepoConfig]:
    """
    Parse .gitmodules in base_path to get list of managed repos.
    """
    gitmodules_path = base_path / ".gitmodules"
    repos = []
    
    if not gitmodules_path.exists():
        return repos

    config = configparser.ConfigParser()
    config.read(gitmodules_path)
    
    for section in config.sections():
        # Section format: submodule "path/to/module"
        if section.startswith('submodule "'):
            path_str = config[section].get("path")
            url = config[section].get("url")
            if path_str:
                repos.append(RepoConfig(
                    name=Path(path_str).name,
                    path=Path(path_str),
                    url=url
                ))
    return repos

def find_config_root(start_path: Path = None) -> Optional[Path]:
    """Find workspace.json in start_path or its parents."""
    if start_path is None:
        start_path = Path.cwd()
    
    for parent in [start_path] + list(start_path.parents):
        config_path = parent / "workspace.json"
        if config_path.exists():
            return config_path
            
        # Check if we are in a git worktree
        git_file = parent / ".git"
        if git_file.exists() and git_file.is_file():
            # Read gitdir from .git file
            try:
                content = git_file.read_text().strip()
                if content.startswith("gitdir:"):
                    gitdir_path = Path(content.split(":", 1)[1].strip())
                    if not gitdir_path.is_absolute():
                        gitdir_path = (parent / gitdir_path).resolve()
                    
                    # gitdir is usually /path/to/base/.git/worktrees/name
                    # We want /path/to/base
                    # Check if it follows the worktree structure
                    if "worktrees" in gitdir_path.parts:
                        # Go up until we find .git directory or workspace.json
                        # Usually base is gitdir_path.parent.parent.parent (worktrees/name/../../..)
                        # But let's be safer.
                        # The gitdir is inside .git of the base repo.
                        # So gitdir_path.parent.parent should be the .git dir of base.
                        # And gitdir_path.parent.parent.parent should be the base root.
                        
                        # Example: /base/.git/worktrees/feature
                        # parent -> /base/.git/worktrees
                        # parent.parent -> /base/.git
                        # parent.parent.parent -> /base
                        
                        base_candidate = gitdir_path.parent.parent.parent
                        if (base_candidate / "workspace.json").exists():
                            return base_candidate / "workspace.json"
            except Exception:
                pass
                
    return None

def load_config(path: Path = None) -> WorkspaceConfig:
    """Load workspace configuration from JSON file."""
    if path is None:
        path = find_config_root()
        if path is None:
             raise FileNotFoundError("workspace.json not found in current or parent directories.")
    elif not path.exists():
        # If path is provided but doesn't exist, try to find it?
        # Or just error?
        # If path is "workspace.json" (relative), we might want to search.
        if path.name == "workspace.json" and not path.is_absolute():
             found = find_config_root()
             if found:
                 path = found
             else:
                 raise FileNotFoundError(f"{path} not found.")
        else:
             raise FileNotFoundError(f"{path} not found.")

    with open(path, "r") as f:
        data = json.load(f)
    
    # Ensure base_path is absolute
    base_path_raw = data.get("base_path", path.parent)
    if not Path(base_path_raw).is_absolute():
        base_path = (path.parent / base_path_raw).resolve()
    else:
        base_path = Path(base_path_raw).resolve()
    
    # Parse workspaces
    workspaces = {}
    for name, entry in data.get("workspaces", {}).items():
        workspaces[name] = WorkspaceEntry(**entry)

    return WorkspaceConfig(
        base_path=base_path,
        workspaces=workspaces,
        preview=data.get("preview") or [],
        preview_hook=data.get("preview_hook") or {},
        log_path=Path(data["log_path"]) if data.get("log_path") else None
    )

def save_config(config: WorkspaceConfig, path: Path) -> None:
    """Save workspace configuration to JSON file."""
    data = {
        "base_path": str(config.base_path),
        "workspaces": {
            name: entry.model_dump() 
            for name, entry in config.workspaces.items()
        },
        "preview": config.preview,
        "preview_hook": config.preview_hook.model_dump(),
        "log_path": str(config.log_path) if config.log_path else None
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def detect_current_workspace() -> str:
    """
    Detect the current workspace name based on the current working directory.
    Returns None if not inside a known workspace.
    """
    try:
        config = load_config()
    except FileNotFoundError:
        return None

    cwd = Path.cwd().resolve()
    
    # Check feature workspaces
    for name, entry in config.workspaces.items():
        if not Path(entry.path).is_absolute():
            ws_path = (config.base_path / entry.path).resolve()
        else:
            ws_path = Path(entry.path).resolve()
        
        try:
            cwd.relative_to(ws_path)
            return name
        except ValueError:
            continue
            
    # Check base workspace (optional, maybe return "base" or None?)
    # For preview command, we usually want a feature workspace.
    # But for sync, base is valid.
    # Let's return None for base for now, or handle it in caller.
    # Actually, if we are in base, we might want to know.
    try:
        cwd.relative_to(config.base_path.resolve())
        return "base"
    except ValueError:
        pass
        
    return None
