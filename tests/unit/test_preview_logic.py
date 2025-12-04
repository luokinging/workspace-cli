import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.server.git import MockGitProvider
from workspace_cli.models import Workspace

@pytest.fixture
def manager():
    WorkspaceManager._instance = None
    git = MockGitProvider()
    mgr = WorkspaceManager.get_instance(Path("/tmp/base"), git_provider=git)
    # Mock watcher
    mgr.watcher = MagicMock()
    return mgr

def test_switch_preview(manager):
    async def _test():
        # Setup
        manager.workspaces["feature"] = Workspace(name="feature", path="/tmp/feature", branch="feature")
        manager.git.responses["get_commit_hash:HEAD"] = "feature_hash"
        manager.git.responses["get_commit_hash:main"] = "main_hash"
        manager.git.responses["get_common_base"] = "base_hash"
        
        with patch("shutil.copytree") as mock_copy:
            with patch("workspace_cli.server.watcher.Watcher") as MockWatcher:
                mock_watcher_instance = MockWatcher.return_value
                
                await manager.switch_preview("feature")
                
                # Verify Git Ops
                assert ("clean", Path("/tmp/base")) in manager.git.calls
                assert ("get_common_base", Path("/tmp/base"), "feature_hash", "main_hash") in manager.git.calls
                assert ("checkout", Path("/tmp/base"), "base_hash", True) in manager.git.calls
                
                # Verify Copy
                mock_copy.assert_called()
                
                # Verify Watcher
                MockWatcher.assert_called_with(Path("/tmp/feature"), Path("/tmp/base"))
                mock_watcher_instance.start.assert_called()
                
                # Verify Session
                assert manager.preview_session is not None
                assert manager.preview_session.workspace_name == "feature"
                assert manager.preview_session.status == "RUNNING"

    asyncio.run(_test())
