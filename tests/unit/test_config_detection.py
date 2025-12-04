import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from workspace_cli.config import detect_current_workspace, WorkspaceConfig, WorkspaceEntry

@pytest.fixture
def mock_config():
    return WorkspaceConfig(
        base_path=Path("/tmp/base"),
        workspaces={
            "feature-a": WorkspaceEntry(path="../base-feature-a"),
            "feature-b": WorkspaceEntry(path="/tmp/base-feature-b")
        }
    )

@patch("workspace_cli.config.load_config")
@patch("pathlib.Path.cwd")
def test_detect_current_workspace_relative(mock_cwd, mock_load_config, mock_config):
    mock_load_config.return_value = mock_config
    
    # Simulate being inside feature-a
    mock_cwd.return_value = Path("/tmp/base-feature-a/subdir").resolve()
    
    # We need to mock resolve() behavior or ensure paths match
    # Since we can't easily mock resolve() on real Path objects mixed with mocks,
    # let's rely on the fact that the function calls resolve().
    # But here we are mocking cwd.
    
    # Let's mock the logic inside detect_current_workspace slightly differently or use real paths?
    # Using real paths in /tmp is safer.
    pass

def test_detect_real_paths(tmp_path):
    # Create a fake structure
    base = tmp_path / "base"
    base.mkdir()
    
    feature_a = tmp_path / "base-feature-a"
    feature_a.mkdir()
    
    feature_b = tmp_path / "base-feature-b"
    feature_b.mkdir()
    
    config = WorkspaceConfig(
        base_path=base,
        workspaces={
            "feature-a": WorkspaceEntry(path="../base-feature-a"),
            "feature-b": WorkspaceEntry(path=str(feature_b))
        }
    )
    
    with patch("workspace_cli.config.load_config", return_value=config):
        # Test feature-a (relative)
        with patch("pathlib.Path.cwd", return_value=feature_a / "subdir"):
            assert detect_current_workspace() == "feature-a"
            
        # Test feature-b (absolute)
        with patch("pathlib.Path.cwd", return_value=feature_b):
            assert detect_current_workspace() == "feature-b"
            
        # Test base
        with patch("pathlib.Path.cwd", return_value=base):
            assert detect_current_workspace() == "base"
            
        # Test unknown
        with patch("pathlib.Path.cwd", return_value=tmp_path / "unknown"):
            assert detect_current_workspace() is None
