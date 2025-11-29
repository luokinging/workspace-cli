import json
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, RepoConfig

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
    
    repos = []
    for r in data.get("repos", []):
        if isinstance(r, str):
            # Simple string format, assume path=name
            repos.append(RepoConfig(name=r, path=Path(r)))
        else:
            repos.append(RepoConfig(**r))
            
    return WorkspaceConfig(
        base_path=base_path,
        repos=repos,
        rules_repo_name=data.get("rules_repo"),
        workspace_expand_folder=data.get("workspace_expand_folder")
    )

def save_config(config: WorkspaceConfig, path: Path) -> None:
    """Save workspace configuration to JSON file."""
    data = {
        "base_path": str(config.base_path),
        "repos": [
            {"name": r.name, "path": str(r.path), "url": r.url}
            for r in config.repos
        ],
        "rules_repo": config.rules_repo_name,
        "workspace_expand_folder": config.workspace_expand_folder
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
