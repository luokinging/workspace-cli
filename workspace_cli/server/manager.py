import asyncio
from typing import Dict, Optional, List
from pathlib import Path
from workspace_cli.models import Workspace, PreviewSession, DaemonStatus, PreviewStatus
from workspace_cli.server.git import GitProvider, ShellGitProvider
from workspace_cli.server.watcher import Watcher
from workspace_cli.server.runner import PreviewRunner
from workspace_cli.config import load_config

from workspace_cli.utils.logger import get_logger
logger = get_logger()

class WorkspaceManager:
    _instance = None

    def __init__(self, base_path: Path, git_provider: GitProvider = None):
        self.base_path = base_path
        self.git = git_provider or ShellGitProvider()
        self.workspaces: Dict[str, Workspace] = {}
        self.preview_session: Optional[PreviewSession] = None
        self.watcher = None
        self.runner = PreviewRunner(base_path)
        self.is_syncing: bool = False
        self._lock = asyncio.Lock()
        self.config = None

    @classmethod
    def get_instance(cls, base_path: Path = None, git_provider: GitProvider = None) -> 'WorkspaceManager':
        if cls._instance is None:
            if base_path is None:
                raise ValueError("Base path required for initialization")
            cls._instance = cls(base_path, git_provider)
        return cls._instance

    async def get_status(self) -> DaemonStatus:
        async with self._lock:
            # logger.debug(f"get_status called. Workspaces: {list(self.workspaces.keys())}")
            return DaemonStatus(
                active_preview=self.preview_session.workspace_name if self.preview_session else None,
                workspaces=list(self.workspaces.values()),
                is_syncing=self.is_syncing
            )

    async def initialize(self):
        """Load existing workspaces from disk/config"""
        try:
            self.config = load_config(self.base_path / "workspace.json")
            
            # Update base_path from config to ensure we use the true base
            if self.config.base_path != self.base_path:
                logger.debug(f"Updating base_path from config: {self.config.base_path}")
                self.base_path = self.config.base_path
                self.runner.base_path = self.base_path
                
            # Configure logging if log_path is set
            if self.config.log_path:
                import os
                from workspace_cli.utils.logger import setup_logging
                debug_mode = os.environ.get("WORKSPACE_DEBUG") == "1"
                setup_logging(debug=debug_mode, log_file=self.config.log_path)
                logger.debug(f"Logging configured to {self.config.log_path}")

            self.workspaces = {}
            for name, entry in self.config.workspaces.items():
                ws_path = Path(entry.path)
                if not ws_path.is_absolute():
                    ws_path = (self.base_path / ws_path).resolve()
                
                # Try to detect branch if possible, otherwise default
                branch = f"workspace-{name}/stand"
                if ws_path.exists():
                    try:
                        branch = self.git.get_current_branch(ws_path)
                    except Exception:
                        pass

                self.workspaces[name] = Workspace(
                    name=name,
                    path=str(ws_path),
                    branch=branch
                )
            # logger.debug(f"Loaded config with workspaces: {list(self.workspaces.keys())}")
        except FileNotFoundError:
            logger.info(f"No workspace.json found at {self.base_path}. Daemon is ready to accept connections.")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    async def ensure_config(self, project_root: str):
        """Ensure configuration is loaded from project_root."""
        async with self._lock:
            if self.config is None:
                logger.debug(f"Initializing config from {project_root}")
                self.base_path = Path(project_root)
                self.runner.base_path = self.base_path # Update runner base path too
                await self.initialize()
            elif str(self.base_path) != str(project_root):
                # Check if project_root is actually a feature workspace pointing to same base
                try:
                    # If we load config from project_root, does it match our base?
                    temp_config = load_config(Path(project_root) / "workspace.json")
                    if temp_config.base_path == self.base_path:
                        # It's fine, just a feature workspace
                        pass
                    else:
                        logger.warning(f"Daemon is running for {self.base_path}, but request is for {project_root} (base: {temp_config.base_path}). Ignoring request root.")
                except Exception:
                     logger.warning(f"Daemon is running for {self.base_path}, but request is for {project_root}. Ignoring request root.")

    async def switch_preview(self, workspace_name: str, rebuild: bool = False):
        async with self._lock:
            await self._switch_preview_internal(workspace_name, rebuild)

    async def _switch_preview_internal(self, workspace_name: str, rebuild: bool = False):
        if workspace_name not in self.workspaces:
            # Auto-register if path exists
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
        if self.preview_session:
            print(f"DEBUG: Stopping existing preview for {self.preview_session.workspace_name}")
            if self.watcher:
                self.watcher.stop()
                self.watcher = None
            await self.runner.stop()

        # 2. Clean Preview Workspace (Base Path)
        target_path = self.base_path
        
        # Run before_clear hooks
        if self.config and self.config.preview_hook.before_clear:
            await self.runner.run_hooks(self.config.preview_hook.before_clear, "before_clear")

        self.git.clean(target_path)

        # 3. Find Common Base
        feature_path = Path(workspace.path)
        feature_commit = self.git.get_commit_hash(feature_path, "HEAD")
        main_commit = self.git.get_commit_hash(target_path, "main") # Or origin/main
        
        common_base = self.git.get_common_base(target_path, feature_commit, main_commit)

        # 4. Checkout Preview Workspace to Base
        # Create/Reset 'preview' branch to common_base
        # Use checkout -B to force create/reset and checkout
        try:
            self.git.run_git_cmd(["checkout", "-B", "preview", common_base], target_path)
        except Exception as e:
            print(f"Warning: Failed to checkout -B preview: {e}")
            # Fallback to detached HEAD
            self.git.checkout(target_path, common_base, force=True)

        # 5. Sync Files (Copy)
        import shutil
        def ignore_git(dir, files):
            return [f for f in files if f == '.git' or f == 'node_modules'] # Basic ignore
        
        shutil.copytree(feature_path, target_path, dirs_exist_ok=True, ignore=ignore_git)

        # 6. Start Watcher
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting Watcher from {feature_path} to {target_path}")
        self.watcher = Watcher(feature_path, target_path)
        self.watcher.start()

        # 7. Run Preview Commands and After Hooks
        if self.config:
            if self.config.preview:
                await self.runner.start_preview(self.config.preview)
            if self.config.preview_hook.after_preview:
                # Run after hooks (maybe in background or parallel?)
                # Usually after_preview might be "open browser" etc.
                await self.runner.run_hooks(self.config.preview_hook.after_preview, "after_preview")

        # Update Session
        from datetime import datetime
        self.preview_session = PreviewSession(
            workspace_name=workspace_name,
            start_time=datetime.now(),
            status=PreviewStatus.RUNNING
        )
        workspace.is_active = True

    async def create_workspace(self, names: List[str], base_path: Path = None):
        logger.debug(f"create_workspace called with names={names}")
        async with self._lock:
            for name in names:
                if name in self.workspaces:
                    logger.debug(f"Workspace {name} already exists")
                    continue # Already exists
                
                # Logic to create workspace worktree
                # 1. Define path
                ws_path = self.base_path.parent / f"{self.base_path.name}-{name}"
                
                if ws_path.exists():
                    pass
                else:
                    # 2. Create Worktree
                    # We need to pick a branch name.
                    # Default: workspace-{name}/stand
                    branch_name = f"workspace-{name}/stand"
                    
                    logger.debug(f"Creating worktree at {ws_path} with branch {branch_name}")
                    self.git.create_worktree(self.base_path, branch_name, ws_path)
                    self.git.update_submodules(ws_path)
                    self.git.set_upstream(self.base_path, branch_name, "origin/main")
                
                # 3. Register
                self.workspaces[name] = Workspace(
                    name=name,
                    path=str(ws_path),
                    branch=f"workspace-{name}/stand"
                )
                logger.debug(f"Registered workspace {name}. Current workspaces: {list(self.workspaces.keys())}")

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
                
                # If sync_all, also sync base workspace
                if sync_all:
                    # We treat base workspace as a target too, but it's not in self.workspaces
                    # We can handle it separately or add to targets if we handle path resolution
                    pass 

                # Helper to sync a path
                def sync_path(path: Path):
                    self.git.fetch(path)
                    self.git.pull(path, rebase=True)
                    self.git.update_submodules(path)

                if sync_all:
                    # Sync base
                    # print(f"DEBUG: Syncing base path: {self.base_path}")
                    sync_path(self.base_path)

                for name in targets:
                    if name not in self.workspaces:
                        continue
                    
                    workspace = self.workspaces[name]
                    path = Path(workspace.path)
                    sync_path(path)
                
                # 3. Rebuild Preview if needed
                if rebuild_preview:
                    if self.preview_session and self.preview_session.workspace_name in targets:
                        # We need to be careful with lock reentrancy here.
                        # Since we extracted _switch_preview_internal, we can call it?
                        # No, _switch_preview_internal does NOT acquire lock.
                        # So it is safe to call it here since we hold the lock.
                        await self._switch_preview_internal(self.preview_session.workspace_name, rebuild=True)
                        
            finally:
                self.is_syncing = False

    async def subscribe_to_logs(self):
        """Subscribe to preview logs."""
        queue = await self.runner.add_observer()
        try:
            while True:
                line = await queue.get()
                if line is None:
                    break
                yield line
        finally:
            self.runner.remove_observer(queue)
