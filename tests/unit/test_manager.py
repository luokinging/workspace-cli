import pytest
import asyncio
from pathlib import Path
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.server.git import MockGitProvider

@pytest.fixture
def manager():
    # Reset singleton
    WorkspaceManager._instance = None
    git = MockGitProvider()
    return WorkspaceManager.get_instance(Path("/tmp/base"), git_provider=git)

def test_manager_initialization(manager):
    async def _test():
        assert manager.base_path == Path("/tmp/base")
        assert isinstance(manager.git, MockGitProvider)
        assert manager.workspaces == {}
    asyncio.run(_test())

def test_get_status(manager):
    async def _test():
        status = await manager.get_status()
        assert status.active_preview is None
        assert status.workspaces == []
        assert status.is_syncing is False
    asyncio.run(_test())
