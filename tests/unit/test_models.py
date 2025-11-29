import pytest
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, WorkspaceEntry

def test_workspace_entry():
    entry = WorkspaceEntry(path="/path/to/ws")
    assert entry.path == "/path/to/ws"

def test_workspace_config():
    entry = WorkspaceEntry(path="/path/to/ws")
    config = WorkspaceConfig(
        base_path=Path("/base"),
        workspaces={"test": entry}
    )
    assert config.base_path == Path("/base")
    assert len(config.workspaces) == 1
    assert config.workspaces["test"].path == "/path/to/ws"

