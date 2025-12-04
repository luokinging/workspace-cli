import json
import configparser
from pathlib import Path
from typing import List
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

def load_config(path: Path = Path("workspace.json")) -> WorkspaceConfig:
    """Load workspace configuration from JSON file."""
    if not path.exists():
        # Fallback or error?
        # For now, let's assume we are in the root of the base workspace or a child workspace
        # and try to find workspace.json in current or parent dirs.
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            config_path = parent / "workspace.json"
            if config_path.exists():
                path = config_path
                break
        else:
             raise FileNotFoundError("workspace.json not found in current or parent directories.")

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
        preview_hook=data.get("preview_hook") or {}
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
        "preview_hook": config.preview_hook.model_dump()
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
