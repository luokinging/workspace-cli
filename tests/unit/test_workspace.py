import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.core.workspace import create_workspace, delete_workspace, WorkspaceError
from workspace_cli.models import WorkspaceConfig, WorkspaceEntry

@pytest.fixture
def mock_config():
    return WorkspaceConfig(
        base_path=Path("/base"),
        workspaces={"test": WorkspaceEntry(path="test")}
    )

@patch("workspace_cli.core.workspace.save_config")
@patch("workspace_cli.core.workspace.create_worktree")
@patch("pathlib.Path.mkdir")
@patch("workspace_cli.core.workspace.submodule_update")
@patch("pathlib.Path.exists")
def test_create_workspace(mock_exists, mock_submodule_update, mock_mkdir, mock_create_worktree, mock_save_config, mock_config):
    # Mock paths
    mock_exists.side_effect = [False, True] # workspace dir, source repo
    
    create_workspace("test", mock_config)
    
    mock_create_worktree.assert_called()
    mock_submodule_update.assert_called()
    mock_save_config.assert_called()

@patch("workspace_cli.core.workspace.create_worktree")
@patch("pathlib.Path.exists")
def test_create_workspace_exists(mock_exists, mock_create_worktree, mock_config):
    mock_exists.return_value = True
    with pytest.raises(WorkspaceError):
        create_workspace("test", mock_config)

@patch("workspace_cli.core.workspace.save_config")
@patch("shutil.rmtree")
@patch("workspace_cli.core.workspace.remove_worktree")
@patch("pathlib.Path.exists")
def test_delete_workspace(mock_exists, mock_remove_worktree, mock_rmtree, mock_save_config, mock_config):
    mock_exists.return_value = True
    
    delete_workspace("test", mock_config)
    
    mock_remove_worktree.assert_called()
    # rmtree is NOT called if remove_worktree succeeds
    mock_rmtree.assert_not_called()
    mock_save_config.assert_called()
