import pytest
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, WorkspaceEntry

def test_workspace_entry():
    entry = WorkspaceEntry(path="/path/to/ws")
    assert entry.path == "/path/to/ws"

def test_workspace_config_defaults():
    config = WorkspaceConfig(base_path=Path("/tmp"))
    assert config.workspaces == {}
    assert config.preview == []
    assert config.preview_hook.before_clear == []
    assert config.preview_hook.after_preview == []

def test_workspace_config_with_preview():
    config = WorkspaceConfig(
        base_path=Path("/tmp"),
        preview=["npm run dev"],
        preview_hook={
            "before_clear": ["echo clear"],
            "after_preview": ["echo done"]
        }
    )
    assert config.preview == ["npm run dev"]
    assert config.preview_hook.before_clear == ["echo clear"]
    assert config.preview_hook.after_preview == ["echo done"]

def test_workspace_config():
    entry = WorkspaceEntry(path="/path/to/ws")
    config = WorkspaceConfig(
        base_path=Path("/base"),
        workspaces={"test": entry}
    )
    assert config.base_path == Path("/base")
    assert len(config.workspaces) == 1

