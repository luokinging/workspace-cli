import pytest
from pathlib import Path

def test_create_and_delete_workspace(base_workspace, run_cli):
    # 1. Create
    result = run_cli(["create", "test1", "--base", str(base_workspace)])
    assert result.returncode == 0, f"Create failed: {result.stderr}"
    
    # Verify dir exists
    ws_path = base_workspace.parent / "base-ws-test1"
    assert ws_path.exists()
    
    # Verify worktree (workspace repo)
    assert (ws_path / ".git").is_file()
    
    # Verify submodule
    submodule_path = ws_path / "backend"
    assert submodule_path.exists()
    assert (submodule_path / "backend.txt").exists()
    
    # 2. Status
    # create command should have created workspace.json in CWD (which is likely base_workspace or temp dir?)
    # run_cli default cwd?
    # If run_cli runs in a temp dir, create writes there.
    # We should run status in the same dir.
    # Let's assume run_cli uses a consistent cwd if not specified, or we need to know where it is.
    # In conftest (not seen), usually it's a temp dir.
    # If we pass cwd=base_workspace to status, we expect workspace.json to be there.
    # Did create write to base_workspace?
    # main.py: save_path = Path.cwd() / "workspace.json"
    # So it depends on where create was run.
    # In this test: run_cli(["create", ...]) -> uses default cwd.
    # We should run status in default cwd too.
    
    # Remove manual config creation that overwrites the one from create!
        
    # Run status in default cwd (where create ran)
    result = run_cli(["status"])
    assert result.returncode == 0
    assert "test1" in result.stdout
    
    # 3. Delete
    result = run_cli(["delete", "test1"])
    assert result.returncode == 0
    
    # Verify dir gone
    assert not ws_path.exists()

def test_create_multiple_workspaces(base_workspace, run_cli):
    """Test creating multiple workspaces at once."""
    result = run_cli(["create", "ws1", "ws2", "ws3", "--base", str(base_workspace)])
    assert result.returncode == 0, f"Create failed: {result.stderr}"
    
    for name in ["ws1", "ws2", "ws3"]:
        ws_path = base_workspace.parent / f"base-ws-{name}"
        assert ws_path.exists()
        assert (ws_path / ".git").is_file()

def test_create_duplicate_fails(base_workspace, run_cli):
    run_cli(["create", "test1", "--base", str(base_workspace)])
    result = run_cli(["create", "test1", "--base", str(base_workspace)])
    assert result.returncode != 0
    assert "already exists" in result.stderr
