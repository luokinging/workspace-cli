from fastapi import FastAPI
from contextlib import asynccontextmanager
from pathlib import Path
import os
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.models import DaemonStatus

# Default base path, should be configured via args
BASE_PATH = Path(os.getcwd())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    if os.environ.get("WORKSPACE_DEBUG"):
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("workspace_cli").setLevel(logging.DEBUG)
        print("DEBUG: Logging configured to DEBUG level")
    
    manager = WorkspaceManager.get_instance(BASE_PATH)
    await manager.initialize()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)

@app.get("/status", response_model=DaemonStatus)
async def get_status():
    manager = WorkspaceManager.get_instance()
    return await manager.get_status()

from pydantic import BaseModel
from typing import List, Optional
class PreviewRequest(BaseModel):
    workspace_name: str
    rebuild: bool = False
    project_root: Optional[str] = None

@app.post("/preview")
async def switch_preview(request: PreviewRequest):
    manager = WorkspaceManager.get_instance()
    if request.project_root:
        await manager.ensure_config(request.project_root)
    await manager.switch_preview(request.workspace_name, request.rebuild)
    return {"status": "ok"}

from fastapi.responses import StreamingResponse
@app.get("/preview/logs")
async def preview_logs():
    manager = WorkspaceManager.get_instance()
    
    async def event_generator():
        async for line in manager.subscribe_to_logs():
            yield f"{line}\n"
            
    return StreamingResponse(event_generator(), media_type="text/plain")

class CreateRequest(BaseModel):
    names: List[str]
    base_path: Optional[str] = None

@app.post("/workspaces")
async def create_workspaces(request: CreateRequest):
    manager = WorkspaceManager.get_instance()
    if request.base_path:
        await manager.ensure_config(request.base_path)
    await manager.create_workspace(request.names)
    return {"status": "created"}

@app.delete("/workspaces/{name}")
async def delete_workspace(name: str):
    manager = WorkspaceManager.get_instance()
    await manager.delete_workspace(name)
    return {"status": "deleted"}

class SyncRequest(BaseModel):
    workspace_name: str
    sync_all: bool = False
    rebuild_preview: bool = True
    project_root: Optional[str] = None

@app.post("/sync")
async def sync_workspace(request: SyncRequest):
    manager = WorkspaceManager.get_instance()
    if request.project_root:
        await manager.ensure_config(request.project_root)
    await manager.sync_workspace(request.workspace_name, request.sync_all, request.rebuild_preview)
    return {"status": "synced"}
