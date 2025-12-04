import pytest
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, PreviewHook, WorkspaceEntry
from workspace_cli.core import sync as sync_core
from workspace_cli.config import save_config
import subprocess

def test_preview_hooks(tmp_path, mocker):
    """Test that preview hooks are executed correctly."""
    
    # Setup directories
    base_ws = tmp_path / "base-ws"
    base_ws.mkdir()
    
    feature_ws = tmp_path / "feature-a"
    feature_ws.mkdir()
    
    # Mock dependencies to avoid full git setup
    mocker.patch("workspace_cli.core.sync.rebuild_preview")
    mocker.patch("workspace_cli.core.sync._check_pid_file")
    mocker.patch("workspace_cli.core.sync._create_pid_file")
    mocker.patch("workspace_cli.core.sync._remove_pid_file")
    
    # Define hooks
    before_file = base_ws / "before.txt"
    ready_file = base_ws / "ready.txt"
    
    # Create config
    config = WorkspaceConfig(
        base_path=base_ws,
        workspaces={
            "feature-a": WorkspaceEntry(path=str(feature_ws))
        },
        preview_hook=PreviewHook(
            before_clear=f"touch {before_file}",
            ready_preview=f"touch {ready_file}"
        )
    )
    
    # Run preview
    sync_core.start_preview("feature-a", config, once=True)
    
    # Verify hooks executed
    assert before_file.exists(), "before_clear hook was not executed"
    assert ready_file.exists(), "ready_preview hook was not executed"

def test_preview_hook_failure(tmp_path, mocker):
    """Test that preview stops if a hook fails."""
    
    base_ws = tmp_path / "base-ws"
    base_ws.mkdir()
    
    mocker.patch("workspace_cli.core.sync.rebuild_preview")
    mocker.patch("workspace_cli.core.sync._check_pid_file")
    mocker.patch("workspace_cli.core.sync._create_pid_file")
    mocker.patch("workspace_cli.core.sync._remove_pid_file")
    
    # Config with failing hook
    config = WorkspaceConfig(
        base_path=base_ws,
        workspaces={},
        preview_hook=PreviewHook(
            before_clear="exit 1"
        )
    )
    
    # Spy on typer.secho
    mock_secho = mocker.patch("typer.secho")
    
    # Run preview
    sync_core.start_preview("feature-a", config, once=True)
    
    # Verify error logged
    calls = [args[0] for args, _ in mock_secho.call_args_list]
    assert any("Hook 'before_clear' failed" in str(c) for c in calls)
