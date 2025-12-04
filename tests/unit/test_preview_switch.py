import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.models import PreviewSession, PreviewStatus
from datetime import datetime

@pytest.mark.asyncio
async def test_switch_preview_stops_existing_watcher():
    # Setup
    base_path = Path("/tmp/base")
    mock_git = MagicMock()
    # Mock git methods to avoid errors
    mock_git.get_current_branch.return_value = "main"
    mock_git.get_commit_hash.return_value = "hash"
    mock_git.get_common_base.return_value = "base_hash"
    
    manager = WorkspaceManager(base_path, mock_git)
    
    # Mock existing session and watcher
    manager.preview_session = PreviewSession(
        workspace_name="A",
        start_time=datetime.now(),
        status=PreviewStatus.RUNNING
    )
    mock_watcher = MagicMock()
    manager.watcher = mock_watcher
    
    # Mock workspace B existence
    manager.workspaces["B"] = MagicMock()
    manager.workspaces["B"].path = "/tmp/base-B"
    
    # Mock Watcher class to return a new mock
    with patch("workspace_cli.server.manager.Watcher") as MockWatcherClass:
        new_watcher = MagicMock()
        MockWatcherClass.return_value = new_watcher
        
        # Mock shutil.copytree to avoid FS errors
        with patch("shutil.copytree"):
            # Execute
            await manager.switch_preview("B")
            
            # Verify
            # 1. Old watcher should be stopped
            mock_watcher.stop.assert_called_once()
            
            # 2. New watcher should be started
            new_watcher.start.assert_called_once()
            
            # 3. Session should be updated
            assert manager.preview_session.workspace_name == "B"
