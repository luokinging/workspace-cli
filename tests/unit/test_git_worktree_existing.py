import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from workspace_cli.utils.git import create_worktree, GitError

@patch("workspace_cli.utils.git.run_git_cmd")
def test_create_worktree_existing_branch(mock_run_git):
    repo_path = Path("/tmp/repo")
    branch = "existing-branch"
    path = Path("/tmp/worktree")
    
    # Simulate branch exists (rev-parse succeeds)
    # First call: rev-parse --verify -> success
    # Second call: worktree add -> success
    mock_run_git.side_effect = ["hash", ""]
    
    create_worktree(repo_path, branch, path)
    
    # Verify worktree add was called WITHOUT -b
    mock_run_git.assert_any_call(["worktree", "add", str(path), branch], repo_path)
    
    # Verify worktree add -b was NOT called
    try:
        mock_run_git.assert_any_call(["worktree", "add", "-b", branch, str(path)], repo_path)
        assert False, "Should not call worktree add -b"
    except AssertionError:
        pass

@patch("workspace_cli.utils.git.run_git_cmd")
def test_create_worktree_new_branch(mock_run_git):
    repo_path = Path("/tmp/repo")
    branch = "new-branch"
    path = Path("/tmp/worktree")
    
    # Simulate branch does not exist (rev-parse fails)
    def side_effect(cmd, cwd):
        if "rev-parse" in cmd:
            raise GitError("Branch not found")
        return ""
        
    mock_run_git.side_effect = side_effect
    
    create_worktree(repo_path, branch, path)
    
    # Verify worktree add -b WAS called
    mock_run_git.assert_any_call(["worktree", "add", "-b", branch, str(path)], repo_path)
