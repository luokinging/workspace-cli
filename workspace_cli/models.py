from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path

class RepoConfig(BaseModel):
    name: str
    path: Path  # Relative path to workspace root
    url: Optional[str] = None

class WorkspaceConfig(BaseModel):
    base_path: Path
    repos: List[RepoConfig]
    repos: List[RepoConfig]

class Context(BaseModel):
    root_path: Path
    current_workspace_name: str
    config: WorkspaceConfig
