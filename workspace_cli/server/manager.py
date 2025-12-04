import asyncio
from typing import Dict, Optional, List
from pathlib import Path
from workspace_cli.models import Workspace, PreviewSession, DaemonStatus, PreviewStatus
from workspace_cli.server.git import GitProvider, ShellGitProvider
from workspace_cli.server.watcher import Watcher

class WorkspaceManager:
    _instance = None

    def __init__(self, base_path: Path, git_provider: GitProvider = None):
        self.base_path = base_path
        self.git = git_provider or ShellGitProvider()
        self.workspaces: Dict[str, Workspace] = {}
        self.preview_session: Optional[PreviewSession] = None
        self.watcher = None
        self.is_syncing: bool = False
        self._lock = asyncio.Lock()

    @classmethod
    def get_instance(cls, base_path: Path = None, git_provider: GitProvider = None) -> 'WorkspaceManager':
        if cls._instance is None:
            if base_path is None:
                raise ValueError("Base path required for initialization")
            cls._instance = cls(base_path, git_provider)
        return cls._instance

    async def get_status(self) -> DaemonStatus:
        async with self._lock:
            print(f"DEBUG: get_status called. Workspaces: {list(self.workspaces.keys())}")
            return DaemonStatus(
                active_preview=self.preview_session.workspace_name if self.preview_session else None,
                workspaces=list(self.workspaces.values()),
                is_syncing=self.is_syncing
            )

    async def initialize(self):
        """Load existing workspaces from disk/config"""
        # TODO: Load from workspace.json or scan directories
        pass

    async def switch_preview(self, workspace_name: str, rebuild: bool = False):
        async with self._lock:
            await self._switch_preview_internal(workspace_name, rebuild)

    async def _switch_preview_internal(self, workspace_name: str, rebuild: bool = False):
        if workspace_name not in self.workspaces:
            # For now, if not found, maybe try to find it or error
            # Assuming we have a way to know about workspaces.
            # If not in memory, maybe we should check disk?
            # For Phase 3, let's assume it's in memory or we just use the name to find path.
            # But we haven't implemented load logic yet.
            # Let's assume we can create a temporary workspace entry if path exists.
            ws_path = self.base_path.parent / f"{self.base_path.name}-{workspace_name}"
            if ws_path.exists():
                    self.workspaces[workspace_name] = Workspace(
                        name=workspace_name,
                        path=str(ws_path),
                        branch=self.git.get_current_branch(ws_path)
                    )
            else:
                raise ValueError(f"Workspace {workspace_name} not found")

        workspace = self.workspaces[workspace_name]
        
        # 1. Stop existing preview
        # 1. Stop existing preview
        if self.preview_session:
            print(f"DEBUG: Stopping existing preview for {self.preview_session.workspace_name}")
            if self.watcher:
                self.watcher.stop()
                self.watcher = None

        # 2. Clean Preview Workspace (Base Path)
        # We assume base_path IS the preview workspace for now (as per design)
        # Or is there a separate preview workspace?
        # Design says: "Checkout Preview Workspace to this base commit"
        # "Preview Workspace" usually implies the base repo where we run things.
        target_path = self.base_path
        
        self.git.clean(target_path)

        # 3. Find Common Base
        # We need the commit hash of the feature workspace and main
        # Assuming main is in base_path or we fetch it?
        # Design: "Find the common ancestor commit between Target Feature and Main"
        # We need to know what "Main" is.
        # Let's assume "origin/main" or just "main".
        feature_path = Path(workspace.path)
        feature_commit = self.git.get_commit_hash(feature_path, "HEAD")
        # We need to fetch in target to ensure we have the objects?
        # Or if they are worktrees, they share objects.
        # So we can just find merge base.
        # We need main commit.
        main_commit = self.git.get_commit_hash(target_path, "main") # Or origin/main
        
        common_base = self.git.get_common_base(target_path, feature_commit, main_commit)

        # 4. Checkout Preview Workspace to Base
        self.git.checkout(target_path, common_base, force=True)

        # 5. Sync Files (Copy)
        # We need to copy modified files from feature to target.
        # For Phase 3, we can just copy everything (excluding git) or use rsync?
        # Or use the Watcher logic to sync initially?
        # Design says: "Sync (copy) file differences"
        # Simple approach: Copy all files from feature to target (excluding .git)
        # This might be slow for large repos, but "Fast Local Preview" implies it's faster than git pull.
        # We can use `shutil.copytree` with `dirs_exist_ok=True`.
        import shutil
        def ignore_git(dir, files):
            return [f for f in files if f == '.git' or f == 'node_modules'] # Basic ignore
        
        shutil.copytree(feature_path, target_path, dirs_exist_ok=True, ignore=ignore_git)

        # 6. Start Watcher
        # from workspace_cli.server.watcher import Watcher
        self.watcher = Watcher(feature_path, target_path)
        self.watcher.start()

        # Update Session
        from datetime import datetime
        self.preview_session = PreviewSession(
            workspace_name=workspace_name,
            start_time=datetime.now(),
            status=PreviewStatus.RUNNING
        )
        workspace.is_active = True

    async def create_workspace(self, names: List[str], base_path: Path = None):
        print(f"DEBUG: create_workspace called with names={names}")
        async with self._lock:
            for name in names:
                if name in self.workspaces:
                    print(f"DEBUG: Workspace {name} already exists")
                    continue # Already exists
                
                # Logic to create workspace worktree
                # 1. Define path
                ws_path = self.base_path.parent / f"{self.base_path.name}-{name}"
                
                if ws_path.exists():
                    # If exists, just register it? Or fail?
                    # Legacy logic failed.
                    # But we might want to be idempotent.
                    pass
                else:
                    # 2. Create Worktree
                    branch_name = f"workspace-{name}/stand"
                    print(f"DEBUG: Creating worktree at {ws_path} with branch {branch_name}")
                    self.git.create_worktree(self.base_path, branch_name, ws_path)
                    self.git.update_submodules(ws_path)
                    # Set upstream to origin/main so sync works
                    # Assuming origin/main exists.
                    self.git.set_upstream(self.base_path, branch_name, "origin/main")
                
                # 3. Register
                self.workspaces[name] = Workspace(
                    name=name,
                    path=str(ws_path),
                    branch=f"workspace-{name}/stand"
                )
                print(f"DEBUG: Registered workspace {name}. Current workspaces: {list(self.workspaces.keys())}")

    async def delete_workspace(self, name: str):
        async with self._lock:
            if name not in self.workspaces:
                raise ValueError(f"Workspace {name} not found")
            
            workspace = self.workspaces[name]
            ws_path = Path(workspace.path)
            
            # 1. Remove Worktree
            self.git.remove_worktree(ws_path)
            
            # 2. Unregister
            del self.workspaces[name]

    async def sync_workspace(self, workspace_name: str, sync_all: bool = False, rebuild_preview: bool = True):
        async with self._lock:
            self.is_syncing = True
            try:
                targets = [workspace_name] if not sync_all else list(self.workspaces.keys())
                
                for name in targets:
                    if name not in self.workspaces:
                        continue
                    
                    workspace = self.workspaces[name]
                    path = Path(workspace.path)
                    
                    # 1. Fetch
                    self.git.fetch(path)
                    
                    # 2. Pull
                    self.git.pull(path, rebase=True)
                
                # 3. Rebuild Preview if needed
                if rebuild_preview:
                    if self.preview_session and self.preview_session.workspace_name in targets:
                        await self._switch_preview_internal(self.preview_session.workspace_name, rebuild=True)
                        # We need to release lock? No, switch_preview acquires lock.
                        # We are already holding lock.
                        # switch_preview is async but we hold lock.
                        # We need to refactor switch_preview to have an internal _switch_preview without lock?
                        # Or just call the logic directly here.
                        # For simplicity, let's just duplicate logic or extract it.
                        # But wait, asyncio.Lock is not reentrant!
                        # We MUST NOT call switch_preview here if it acquires lock.
                        # We should extract _switch_preview.
                        pass
                        
            finally:
                self.is_syncing = False
                
            # If we need to rebuild, we should do it after releasing lock?
            # Or make lock reentrant (not possible with asyncio.Lock).
            # We should extract logic.
            

