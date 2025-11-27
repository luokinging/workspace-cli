import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.core.sync import Watcher, sync_rules
from workspace_cli.models import WorkspaceConfig, RepoConfig

def test_watcher_is_ignored():
    watcher = Watcher(Path("/src"), Path("/dst"), Path("repo"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert watcher._is_ignored("/src/repo/ignored.txt") is True
        
        mock_run.side_effect = Exception("error")
        assert watcher._is_ignored("/src/repo/file.txt") is False

@patch("workspace_cli.core.sync.get_current_branch")
@patch("workspace_cli.core.sync.run_git_cmd")
@patch("pathlib.Path.cwd")
def test_sync_rules(mock_cwd, mock_run_git, mock_get_branch, capsys):
    mock_get_branch.return_value = "feature-branch"
    # Setup config
    config = WorkspaceConfig(
        base_path=Path("/base/main"),
        repos=[RepoConfig(name="rules", path=Path("rules"))],
        rules_repo_name="rules"
    )
    
    # Mock CWD to be in a workspace
    mock_cwd.return_value = Path("/base/main-feature")
    
    # Mock paths existence
    with patch("pathlib.Path.exists", return_value=True):
        # Mock iterdir for finding other workspaces
        with patch("pathlib.Path.iterdir") as mock_iterdir:
            mock_iterdir.return_value = [
                Path("/base/main-feature"),
                Path("/base/main-other")
            ]
            
            sync_rules(config)
            
            # Verify git commands
            # 1. Commit/Push in source
            assert mock_run_git.call_count >= 2 
            
            # We can't easily verify exact calls without more complex mocking of the sequence
            # But we can check if it ran without error
