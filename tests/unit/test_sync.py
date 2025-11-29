import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.core.sync import Watcher
from workspace_cli.models import WorkspaceConfig, RepoConfig

def test_watcher_is_ignored():
    watcher = Watcher(Path("/src"), Path("/dst"), Path("repo"))
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        assert watcher._is_ignored("/src/repo/ignored.txt") is True
        
        mock_run.side_effect = Exception("error")
        assert watcher._is_ignored("/src/repo/file.txt") is False


