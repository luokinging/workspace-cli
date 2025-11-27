import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.core.workspace import create_workspace, delete_workspace, WorkspaceError
from workspace_cli.models import WorkspaceConfig, RepoConfig

@pytest.fixture
def mock_config():
    return WorkspaceConfig(
        base_path=Path("/base"),
        repos=[RepoConfig(name="repo1", path=Path("repo1"))]
    )

@patch("workspace_cli.core.workspace.create_worktree")
@patch("pathlib.Path.mkdir")
@patch("pathlib.Path.exists")
def test_create_workspace(mock_exists, mock_mkdir, mock_create_worktree, mock_config):
    # Mock paths
    mock_exists.side_effect = [False, True] # workspace dir, source repo
    
    create_workspace("test", mock_config)
    
    mock_mkdir.assert_called()
    mock_create_worktree.assert_called()

@patch("workspace_cli.core.workspace.create_worktree")
@patch("pathlib.Path.exists")
def test_create_workspace_exists(mock_exists, mock_create_worktree, mock_config):
    mock_exists.return_value = True
    with pytest.raises(WorkspaceError):
        create_workspace("test", mock_config)

@patch("shutil.rmtree")
@patch("workspace_cli.core.workspace.remove_worktree")
@patch("pathlib.Path.exists")
def test_delete_workspace(mock_exists, mock_remove_worktree, mock_rmtree, mock_config):
    mock_exists.return_value = True
    
    delete_workspace("test", mock_config)
    
    mock_remove_worktree.assert_called()
    mock_rmtree.assert_called()
