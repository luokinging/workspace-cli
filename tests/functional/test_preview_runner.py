import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.models import WorkspaceConfig, PreviewHooks

@pytest.mark.asyncio
async def test_preview_runner_integration():
    # Setup
    base_path = Path("/tmp/base")
    mock_git = MagicMock()
    mock_git.get_current_branch.return_value = "main"
    mock_git.get_commit_hash.return_value = "hash"
    mock_git.get_common_base.return_value = "base_hash"
    
    # Reset singleton
    WorkspaceManager._instance = None
    manager = WorkspaceManager.get_instance(base_path, mock_git)
    
    # Mock config
    manager.config = WorkspaceConfig(
        base_path=base_path,
        preview=["echo 'Preview Running'"],
        preview_hook=PreviewHooks(
            before_clear=["echo 'Before Clear'"],
            after_preview=["echo 'After Preview'"]
        )
    )
    
    # Mock workspace
    manager.workspaces["A"] = MagicMock()
    manager.workspaces["A"].path = "/tmp/base-A"
    
    # Set initial preview session to trigger stop()
    from workspace_cli.models import PreviewSession, PreviewStatus
    from datetime import datetime
    manager.preview_session = PreviewSession(
        workspace_name="B",
        start_time=datetime.now(),
        status=PreviewStatus.RUNNING
    )
    
    # Mock Runner methods to avoid real subprocess
    manager.runner.run_hooks = AsyncMock()
    manager.runner.start_preview = AsyncMock()
    manager.runner.stop = AsyncMock()
    
    # Mock Watcher and shutil
    with patch("workspace_cli.server.manager.Watcher"), \
         patch("shutil.copytree"):
        
        # Execute
        await manager.switch_preview("A")
        
        # Verify
        # 1. Stop called
        manager.runner.stop.assert_called_once()
        
        # 2. Before Clear Hook called
        manager.runner.run_hooks.assert_any_call(["echo 'Before Clear'"], "before_clear")
        
        # 3. Start Preview called
        manager.runner.start_preview.assert_called_once_with(["echo 'Preview Running'"])
        
        # 4. After Preview Hook called
        manager.runner.run_hooks.assert_any_call(["echo 'After Preview'"], "after_preview")
