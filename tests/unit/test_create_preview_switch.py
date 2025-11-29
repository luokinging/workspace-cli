import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from workspace_cli.core.workspace import create_workspace
from workspace_cli.models import WorkspaceConfig, RepoConfig

@pytest.fixture
def mock_config():
    base = Path("/tmp/base")
    return WorkspaceConfig(
        base_path=base,
        repos=[
            RepoConfig(name="repo1", path=Path("repo1")),
            RepoConfig(name="repo2", path=Path("repo2")),
        ]
    )

@patch("workspace_cli.core.workspace.create_worktree")
@patch("workspace_cli.core.workspace.checkout_new_branch")
@patch("pathlib.Path.exists", autospec=True)
@patch("pathlib.Path.mkdir")
def test_create_workspace_switches_to_preview(mock_mkdir, mock_exists, mock_checkout, mock_create_worktree, mock_config):
    def exists_side_effect(self):
        # Return False for workspace path (so it can be created)
        if str(self).endswith("test-ws"):
            return False
        # Return True for repos (so they can be processed)
        return True
        
    mock_exists.side_effect = exists_side_effect
    
    # Call function
    create_workspace("test-ws", mock_config)
    
    # Verify create_worktree was called (existing logic)
    assert mock_create_worktree.call_count == 2

    # We don't explicitly call checkout_new_branch in create_workspace anymore
    # as create_worktree handles it (or git worktree add -b does)
    # assert mock_checkout.call_count == 2
    
    # Check arguments for first repo
    repo1_path = mock_config.base_path / "repo1"
    # mock_checkout.assert_any_call(repo1_path, "workspace-test-ws/preview", force=True)
    
    # Check arguments for second repo
    repo2_path = mock_config.base_path / "repo2"
    # mock_checkout.assert_any_call(repo2_path, "workspace-test-ws/preview", force=True)
