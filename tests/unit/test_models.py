import pytest
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, RepoConfig

def test_repo_config():
    repo = RepoConfig(name="test", path=Path("test"))
    assert repo.name == "test"
    assert repo.path == Path("test")

def test_workspace_config():
    repo = RepoConfig(name="test", path=Path("test"))
    config = WorkspaceConfig(
        base_path=Path("/base"),
        repos=[repo]
    )
    assert config.base_path == Path("/base")
    assert len(config.repos) == 1

