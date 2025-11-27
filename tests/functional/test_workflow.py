import pytest
from pathlib import Path

def test_create_and_delete_workspace(base_workspace, run_cli):
    # 1. Create
    result = run_cli(["create", "test1"])
    assert result.returncode == 0, f"Create failed: {result.stderr}"
    
    # Verify dir exists
    ws_path = base_workspace.parent / "base-ws-test1"
    assert ws_path.exists()
    
    # Verify worktree
    wt_path = ws_path / "repo1"
    assert wt_path.exists()
    assert (wt_path / ".git").exists()
    
    # 2. Status
    result = run_cli(["status"])
    assert result.returncode == 0
    assert "test1" in result.stdout
    
    # 3. Delete
    result = run_cli(["delete", "test1"])
    assert result.returncode == 0
    
    # Verify dir gone
    assert not ws_path.exists()

def test_create_duplicate_fails(base_workspace, run_cli):
    run_cli(["create", "test1"])
    result = run_cli(["create", "test1"])
    assert result.returncode != 0
    assert "already exists" in result.stderr
