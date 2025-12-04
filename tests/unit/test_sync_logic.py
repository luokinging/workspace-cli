import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.server.git import MockGitProvider
from workspace_cli.models import Workspace, PreviewSession, PreviewStatus

@pytest.fixture
def manager():
    WorkspaceManager._instance = None
    git = MockGitProvider()
    return WorkspaceManager.get_instance(Path("/tmp/base"), git_provider=git)

def test_sync_workspace(manager):
    async def _test():
        # Setup
        manager.workspaces["ws1"] = Workspace(name="ws1", path="/tmp/ws1", branch="feature")
        
        # Mock _switch_preview_internal
        manager._switch_preview_internal = AsyncMock()
        
        # Test Sync Single
        await manager.sync_workspace("ws1", rebuild_preview=False)
        
        assert ("fetch", Path("/tmp/ws1")) in manager.git.calls
        assert ("pull", Path("/tmp/ws1"), True) in manager.git.calls
        manager._switch_preview_internal.assert_not_called()
        
        # Test Sync with Rebuild (but no active session)
        manager.git.calls = []
        await manager.sync_workspace("ws1", rebuild_preview=True)
        manager._switch_preview_internal.assert_not_called()
        
        # Test Sync with Rebuild AND Active Session
        from datetime import datetime
        manager.preview_session = PreviewSession(
            workspace_name="ws1",
            start_time=datetime.now(),
            status=PreviewStatus.RUNNING
        )
        
        await manager.sync_workspace("ws1", rebuild_preview=True)
        manager._switch_preview_internal.assert_called_with("ws1", rebuild=True)

    asyncio.run(_test())

def test_sync_all(manager):
    async def _test():
        manager.workspaces["ws1"] = Workspace(name="ws1", path="/tmp/ws1", branch="feature")
        manager.workspaces["ws2"] = Workspace(name="ws2", path="/tmp/ws2", branch="feature")
        
        await manager.sync_workspace("ws1", sync_all=True, rebuild_preview=False)
        
        assert ("fetch", Path("/tmp/ws1")) in manager.git.calls
        assert ("fetch", Path("/tmp/ws2")) in manager.git.calls

    asyncio.run(_test())
