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
    # We need to create a config for status to work?
    # Status loads config to find base path.
    # If we don't have workspace.json, status might fail or we need to pass base?
    # Status command doesn't take --base.
    # So we need workspace.json.
    # Let's create one.
    import json
    config = {
        "base_path": str(base_workspace),
        "repos": []
    }
    with open(base_workspace / "workspace.json", "w") as f:
        json.dump(config, f)
        
    # We need to run status from a place where it can find config.
    # If we run from base_workspace, it finds it.
    result = run_cli(["status"], cwd=base_workspace)
    assert result.returncode == 0
    assert "test1" in result.stdout
    
    # 3. Delete
    result = run_cli(["delete", "test1"])
    assert result.returncode == 0
    
    # Verify dir gone
    assert not ws_path.exists()

def test_create_duplicate_fails(base_workspace, run_cli):
    run_cli(["create", "test1", "--base", str(base_workspace)])
    result = run_cli(["create", "test1", "--base", str(base_workspace)])
    assert result.returncode != 0
    assert "already exists" in result.stderr
