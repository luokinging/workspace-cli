from pydantic import BaseModel
from typing import List, Dict, Optional
from pathlib import Path

class RepoConfig(BaseModel):
    name: str
    path: Path  # Relative path to workspace root
    url: Optional[str] = None

class WorkspaceEntry(BaseModel):
    path: str  # Relative or absolute path

class PreviewHooks(BaseModel):
    before_clear: List[str] = []
    after_preview: List[str] = []

class WorkspaceConfig(BaseModel):
    base_path: Path
    workspaces: Dict[str, WorkspaceEntry] = {}
    preview: List[str] = []
    preview_hook: PreviewHooks = PreviewHooks()

class Context(BaseModel):
    root_path: Path
    current_workspace_name: str
    config: WorkspaceConfig
