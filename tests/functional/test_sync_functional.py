import pytest
import time
import subprocess
from pathlib import Path
import shutil

def test_create_workspace(base_workspace, run_cli):
    """Test creating a new workspace."""
    # 1. Create workspace
    result = run_cli(["create", "feature1", "--base", str(base_workspace)])
    assert result.returncode == 0, f"Create failed: {result.stdout}\n{result.stderr}"
    
    ws_path = base_workspace.parent / "base-ws-feature1"
    assert ws_path.exists()
    assert (ws_path / ".git").is_file() # It's a worktree, so .git is a file
    
    # Check submodule
    backend_path = ws_path / "backend"
    assert backend_path.exists()
    assert (backend_path / "backend.txt").exists()

def test_sync_command(base_workspace, run_cli):
    """Test the sync command."""
    # 1. Create feature workspace
    run_cli(["create", "feature1", "--base", str(base_workspace)])
    ws_path = base_workspace.parent / "base-ws-feature1"
    
    # 2. Simulate remote update
    # We need to update remote-main and remote-backend
    test_dir = base_workspace.parent
    remote_backend = test_dir / "remote-backend"
    
    # Clone backend to push update
    backend_update = test_dir / "backend-update"
    subprocess.run(["git", "clone", str(remote_backend), str(backend_update)], check=True)
    (backend_update / "new_feature.txt").write_text("feature v1")
    subprocess.run(["git", "add", "."], cwd=backend_update, check=True)
    subprocess.run(["git", "commit", "-m", "add feature"], cwd=backend_update, check=True)
    subprocess.run(["git", "push"], cwd=backend_update, check=True)
    
    # Update remote-main to point to new backend
    # Clone remote-main
    main_update = test_dir / "main-update"
    subprocess.run(["git", "clone", str(test_dir / "remote-main"), str(main_update)], check=True)
    # Update submodule
    subprocess.run(["git", "submodule", "update", "--init", "--remote"], cwd=main_update, check=True)
    subprocess.run(["git", "add", "backend"], cwd=main_update, check=True)
    subprocess.run(["git", "commit", "-m", "update backend pointer"], cwd=main_update, check=True)
    subprocess.run(["git", "push"], cwd=main_update, check=True)
    
    # Create workspace.json in feature workspace (or base)
    # The sync command needs config.
    import json
    config = {
        "base_path": str(base_workspace),
        "repos": [] # Auto-discovery should work if we don't provide repos? 
                    # Actually sync_workspaces uses config.repos.
                    # If we leave it empty, it won't sync submodules unless we populate it.
                    # But wait, sync_workspaces logic:
                    # 1. Update Base (pull main, submodule update)
                    # 2. Update Siblings (merge main, submodule update)
                    # It doesn't explicitly iterate config.repos for git operations on siblings, 
                    # except maybe for logging or specific repo logic?
                    # Let's check sync.py.
                    # sync_workspaces iterates parent_dir.iterdir().
                    # It calls submodule_update(path).
                    # It doesn't use config.repos for the main sync logic.
                    # So empty repos list is fine.
    }
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config, f)

    # 3. Run sync in feature workspace
    # We need to run from within the workspace
    result = run_cli(["sync"], cwd=ws_path)
    assert result.returncode == 0, f"Sync failed: {result.stdout}\n{result.stderr}"
    
    # 4. Verify feature workspace has update
    assert (ws_path / "backend" / "new_feature.txt").exists()

def test_preview_sync(base_workspace, run_cli):
    """Test preview sync."""
    # 1. Create workspace
    run_cli(["create", "feature1", "--base", str(base_workspace)])
    ws_path = base_workspace.parent / "base-ws-feature1"
    backend_path = ws_path / "backend"
    
    # 2. Start preview in background
    import sys
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    cmd = [sys.executable, "-m", "workspace_cli.main", "preview", "--workspace", "feature1"]
    
    proc = subprocess.Popen(
        cmd,
        cwd=base_workspace, # Run from base workspace (or anywhere)
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for watcher to start
        time.sleep(3)
        
        # 3. Create a file in feature workspace (Uncommitted)
        new_file = backend_path / "preview_test.txt"
        new_file.write_text("hello preview")
        
        # Wait for sync
        time.sleep(3)
        
        # 4. Verify file exists in base workspace (preview target)
        target_file = base_workspace / "backend" / "preview_test.txt"
        assert target_file.exists()
        assert target_file.read_text() == "hello preview"
        
        # Verify base workspace backend is on preview branch
        # We can check with git
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=base_workspace/"backend", capture_output=True, text=True)
        assert res.stdout.strip() == "preview"
        
    finally:
        proc.terminate()
        proc.wait()
