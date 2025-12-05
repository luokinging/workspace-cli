from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum
from pathlib import Path
from datetime import datetime

class Workspace(BaseModel):
    name: str
    path: str
    branch: str
    is_active: bool = False

class PreviewStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"

class PreviewSession(BaseModel):
    workspace_name: str
    start_time: datetime
    pid: Optional[int] = None
    status: PreviewStatus

class DaemonStatus(BaseModel):
    active_preview: Optional[str] = None
    workspaces: List[Workspace]
    is_syncing: bool = False

# Legacy Models (to be refactored/removed)
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
    log_path: Optional[Path] = None

class Context(BaseModel):
    root_path: Path
    current_workspace_name: str
    config: WorkspaceConfig
