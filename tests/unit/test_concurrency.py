import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.server.git import MockGitProvider

@pytest.fixture
def manager():
    WorkspaceManager._instance = None
    git = MockGitProvider()
    return WorkspaceManager.get_instance(Path("/tmp/base"), git_provider=git)

def test_concurrent_create(manager):
    async def _test():
        # Simulate concurrent create requests
        # We want to ensure they are processed sequentially or at least safely.
        # Since we use asyncio.Lock, only one should enter the critical section at a time.
        
        # We can verify this by checking if the lock is held?
        # Or just verify the end result is correct and no race conditions (e.g. duplicate worktrees).
        
        tasks = [
            manager.create_workspace(["ws1"]),
            manager.create_workspace(["ws2"]),
            manager.create_workspace(["ws3"])
        ]
        
        await asyncio.gather(*tasks)
        
        assert "ws1" in manager.workspaces
        assert "ws2" in manager.workspaces
        assert "ws3" in manager.workspaces
        
        # Verify git calls
        # We expect 3 create_worktree calls
        create_calls = [c for c in manager.git.calls if c[0] == "create_worktree"]
        assert len(create_calls) == 3

    asyncio.run(_test())

def test_concurrent_mixed_ops(manager):
    async def _test():
        # Create ws1 first
        await manager.create_workspace(["ws1"])
        
        # Concurrent create ws2 and delete ws1
        tasks = [
            manager.create_workspace(["ws2"]),
            manager.delete_workspace("ws1")
        ]
        
        await asyncio.gather(*tasks)
        
        assert "ws1" not in manager.workspaces
        assert "ws2" in manager.workspaces

    asyncio.run(_test())
