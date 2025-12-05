import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.client.api import DaemonClient

@pytest.mark.asyncio
async def test_lazy_config_initialization(tmp_path, caplog):
    # Setup project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "workspace.json").write_text('{"base_path": ".", "workspaces": {}}')
    
    # Initialize Manager with dummy path (simulating daemon started in ~)
    dummy_path = tmp_path / "home"
    dummy_path.mkdir()
    
    # Reset singleton
    WorkspaceManager._instance = None
    manager = WorkspaceManager.get_instance(dummy_path)
    
    # Capture stdout
    # Capture logs
    import logging
    with caplog.at_level(logging.INFO):
        # Expect FileNotFoundError
        with pytest.raises(FileNotFoundError, match="No workspace.json found"):
            await manager.initialize()
        
    # Verify config is None (failed to load)
    assert manager.config is None
    
    # Call ensure_config with valid project root
    await manager.ensure_config(str(project_root))
    
    # Verify config is loaded and base_path updated
    assert manager.config is not None
    assert manager.base_path == project_root
    assert manager.runner.base_path == project_root

@pytest.mark.asyncio
async def test_parent_directory_config_detection(tmp_path):
    # Setup: root/workspace.json
    #        root/subdir/
    root = tmp_path / "root"
    root.mkdir()
    (root / "workspace.json").write_text('{"base_path": ".", "workspaces": {}}')
    
    subdir = root / "subdir"
    subdir.mkdir()
    
    # Reset singleton
    WorkspaceManager._instance = None
    # Initialize manager from subdir
    manager = WorkspaceManager.get_instance(subdir)
    
    await manager.initialize()
    
    assert manager.config is not None
    # The base_path should be updated to root (where config is)? 
    # Actually, manager uses config path related logic.
    # In manager.py: 
    # self.config = load_config(config_path)
    # checking base_path from config...
    # If base_path in json is ".", it resolves to config dir.
    # So base_path should be 'root'.
    
    assert manager.base_path == root

@pytest.mark.asyncio
async def test_client_sends_project_root(tmp_path):
    # Setup project structure
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / "workspace.json").write_text('{"base_path": ".", "workspaces": {}}')
    
    # Mock httpx client
    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        
        # Run client from project root
        cwd = project_root
        with patch("pathlib.Path.cwd", return_value=cwd):
            client = DaemonClient()
            client.switch_preview("test")
            
            # Verify post call included project_root
            args, kwargs = mock_client.post.call_args
            assert kwargs["json"]["project_root"] == str(project_root)
