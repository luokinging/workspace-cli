import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.utils.git import (
    run_git_cmd, get_current_branch, is_dirty, 
    create_worktree, remove_worktree, GitError
)

@pytest.fixture
def mock_subprocess():
    with patch("subprocess.run") as mock:
        yield mock

def test_run_git_cmd_success(mock_subprocess):
    mock_subprocess.return_value.stdout = "output"
    result = run_git_cmd(["status"], Path("/tmp"))
    assert result == "output"
    mock_subprocess.assert_called_once()

def test_run_git_cmd_failure(mock_subprocess):
    mock_subprocess.side_effect = Exception("error")
    with pytest.raises(Exception):
        run_git_cmd(["status"], Path("/tmp"))

def test_get_current_branch(mock_subprocess):
    mock_subprocess.return_value.stdout = "main"
    assert get_current_branch(Path("/tmp")) == "main"

def test_is_dirty_true(mock_subprocess):
    mock_subprocess.return_value.stdout = "M file.txt"
    assert is_dirty(Path("/tmp")) is True

def test_is_dirty_false(mock_subprocess):
    mock_subprocess.return_value.stdout = ""
    assert is_dirty(Path("/tmp")) is False

def test_create_worktree_existing_branch(mock_subprocess):
    # Mock branch exists check
    mock_subprocess.return_value.stdout = "commit-hash"
    create_worktree(Path("/repo"), "branch", Path("/worktree"))
    # Should call worktree add without -b
    args = mock_subprocess.call_args_list[1][0][0]
    assert "worktree" in args
    assert "add" in args
    assert "-b" not in args

def test_remove_worktree(mock_subprocess):
    with patch("pathlib.Path.exists", return_value=True):
        remove_worktree(Path("/worktree"))
        args = mock_subprocess.call_args[0][0]
        assert args == ["git", "worktree", "remove", "."]
