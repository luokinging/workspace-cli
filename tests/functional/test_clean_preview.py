import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from workspace_cli.core import sync as sync_core
from workspace_cli.models import WorkspaceConfig, RepoConfig

@pytest.fixture
def mock_config(tmp_path):
    base_path = tmp_path / "base"
    base_path.mkdir()
    return WorkspaceConfig(
        base_path=base_path,
        workspaces={
            "feature-a": {"path": "feature-a"}
        }
    )

@patch("workspace_cli.core.sync._get_pid_file")
@patch("workspace_cli.core.sync._check_pid_file")
@patch("workspace_cli.core.sync._remove_pid_file")
@patch("workspace_cli.core.sync.run_git_cmd")
@patch("workspace_cli.core.sync.get_managed_repos")
def test_clean_preview(mock_get_repos, mock_run_git, mock_remove_pid, mock_check_pid, mock_get_pid, mock_config):
    # Setup
    mock_get_pid.return_value = Path("/tmp/pid")
    mock_get_repos.return_value = [RepoConfig(name="repo1", path="repo1")]
    
    # Mock repo path existence
    with patch("pathlib.Path.exists", return_value=True):
        # Execute
        sync_core.clean_preview(mock_config)
    
    # Verify
    mock_check_pid.assert_called_once()
    mock_remove_pid.assert_called_once()
    
    # Verify git commands on base workspace
    # checkout main, clean -fd
    assert mock_run_git.call_count >= 4 # base: checkout, clean; repo: checkout, branch -D, clean
    
    # Check specific calls
    # Base workspace
    mock_run_git.assert_any_call(["checkout", "main"], mock_config.base_path)
    mock_run_git.assert_any_call(["clean", "-fd"], mock_config.base_path)
    
    # Repo
    repo_path = mock_config.base_path / "repo1"
    mock_run_git.assert_any_call(["checkout", "main"], repo_path)
    mock_run_git.assert_any_call(["clean", "-fd"], repo_path)
    # branch -D preview might be called
    mock_run_git.assert_any_call(["branch", "-D", "preview"], repo_path)

@patch("workspace_cli.core.sync.clean_preview")
@patch("workspace_cli.core.sync.sync_workspaces")
@patch("workspace_cli.core.sync.rebuild_preview")
@patch("workspace_cli.main.load_config")
@patch("pathlib.Path.cwd")
def test_sync_command_rebuild(mock_cwd, mock_load_config, mock_rebuild, mock_sync_ws, mock_clean, mock_config):
    from workspace_cli.main import sync
    
    # Setup
    mock_load_config.return_value = mock_config
    # Mock CWD to be inside feature-a
    feature_a_path = mock_config.base_path / "feature-a"
    mock_cwd.return_value = feature_a_path
    
    # Execute sync with rebuild_preview=True (default)
    sync(all=False, rebuild_preview=True)
    
    # Verify
    mock_clean.assert_called_once_with(mock_config)
    mock_sync_ws.assert_called_once_with(mock_config, sync_all=False)
    mock_rebuild.assert_called_once_with("feature-a", mock_config)

@patch("workspace_cli.core.sync.clean_preview")
@patch("workspace_cli.core.sync.sync_workspaces")
@patch("workspace_cli.core.sync.rebuild_preview")
@patch("workspace_cli.main.load_config")
def test_sync_command_no_rebuild(mock_load_config, mock_rebuild, mock_sync_ws, mock_clean, mock_config):
    from workspace_cli.main import sync
    
    # Setup
    mock_load_config.return_value = mock_config
    
    # Execute sync with rebuild_preview=False
    sync(all=False, rebuild_preview=False)
    
    # Verify
    mock_clean.assert_not_called()
    mock_sync_ws.assert_called_once_with(mock_config, sync_all=False)
    mock_rebuild.assert_not_called()
