from pydantic import BaseModel
from typing import List, Dict, Optional
from pathlib import Path

class RepoConfig(BaseModel):
    name: str
    path: Path  # Relative path to workspace root
    url: Optional[str] = None

class WorkspaceEntry(BaseModel):
    path: str  # Relative or absolute path

class WorkspaceConfig(BaseModel):
    base_path: Path
    workspaces: Dict[str, WorkspaceEntry] = {}

class Context(BaseModel):
    root_path: Path
    current_workspace_name: str
    config: WorkspaceConfig
