import pytest
from pathlib import Path
from workspace_cli.server.git import MockGitProvider, ShellGitProvider, GitError

def test_mock_git_provider():
    provider = MockGitProvider()
    path = Path("/tmp/test")
    
    # Test create_worktree
    provider.create_worktree(Path("/repo"), "feature", path)
    assert str(path) in provider.worktrees
    assert provider.worktrees[str(path)] == "feature"
    assert ("create_worktree", Path("/repo"), "feature", path) in provider.calls
    
    # Test get_current_branch
    provider.responses["get_current_branch"] = "feature"
    assert provider.get_current_branch(path) == "feature"
    
    # Test remove_worktree
    provider.remove_worktree(path)
    assert str(path) not in provider.worktrees

def test_shell_git_provider_init():
    # Just test instantiation, actual calls require git repo
    provider = ShellGitProvider()
    assert provider is not None
def test_mock_git_provider_methods():
    provider = MockGitProvider()
    path = Path("/tmp")
    
    provider.push(path, "origin", "feature")
    assert ("push", path, "origin", "feature") in provider.calls
    
    provider.update_submodules(path)
    assert ("update_submodules", path) in provider.calls
    
    provider.set_upstream(path, "branch", "upstream")
    assert ("set_upstream", path, "branch", "upstream") in provider.calls
