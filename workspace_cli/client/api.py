import httpx
import os
from typing import Optional, List
from workspace_cli.models import DaemonStatus

class DaemonClient:
    def __init__(self, port: int = None):
        if port is None:
            port = int(os.environ.get("WORKSPACE_DAEMON_PORT", 9000))
        self.base_url = f"http://localhost:{port}"
        self.client = httpx.Client(base_url=self.base_url, timeout=5.0)

    def is_running(self) -> bool:
        try:
            response = self.client.get("/status")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def get_status(self) -> DaemonStatus:
        response = self.client.get("/status")
        response.raise_for_status()
        return DaemonStatus(**response.json())

    def switch_preview(self, workspace_name: str, rebuild: bool = False):
        from workspace_cli.config import find_config_root
        from pathlib import Path
        
        project_root = find_config_root(Path.cwd())
        
        response = self.client.post("/preview", json={
            "workspace_name": workspace_name, 
            "rebuild": rebuild,
            "project_root": str(project_root.parent) if project_root else None
        })
        response.raise_for_status()

    def create_workspaces(self, names: List[str], base_path: Optional[str] = None):
        from workspace_cli.config import find_config_root
        from pathlib import Path
        
        if not base_path:
             project_root = find_config_root(Path.cwd())
             if project_root:
                 base_path = str(project_root.parent)

        response = self.client.post("/workspaces", json={"names": names, "base_path": base_path})
        response.raise_for_status()

    def delete_workspace(self, name: str):
        response = self.client.delete(f"/workspaces/{name}")
        response.raise_for_status()

    def sync_workspace(self, workspace_name: str, sync_all: bool = False, rebuild_preview: bool = True):
        from workspace_cli.config import find_config_root
        from pathlib import Path
        
        project_root = find_config_root(Path.cwd())
        
        response = self.client.post("/sync", json={
            "workspace_name": workspace_name,
            "sync_all": sync_all,
            "rebuild_preview": rebuild_preview,
            "project_root": str(project_root.parent) if project_root else None
        })
        response.raise_for_status()

    def stream_logs(self):
        with self.client.stream("GET", "/preview/logs", timeout=None) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                yield line
