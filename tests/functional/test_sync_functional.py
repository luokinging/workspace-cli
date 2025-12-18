import pytest
import time
import subprocess
from pathlib import Path
import shutil
import json

def test_create_workspace(base_workspace, run_cli, daemon):
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

def test_sync_command(base_workspace, run_cli, daemon):
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
        "workspaces": {"feature1": {"path": str(ws_path)}}
    }
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config, f)

    # 3. Run sync in feature workspace
    # We need to run from within the workspace
    result = run_cli(["sync"], cwd=ws_path)
    assert result.returncode == 0, f"Sync failed: {result.stdout}\n{result.stderr}"
    
    # 4. Verify feature workspace has update
    assert (ws_path / "backend" / "new_feature.txt").exists()
    
    # Verify Base Workspace did NOT update (since we didn't use --all)
    # Actually, Base Workspace might be updated if we are in it? No, we are in feature workspace.
    # But wait, sync logic for current workspace is "pull --rebase origin main".
    # Base workspace is a separate worktree/clone.
    # So Base Workspace should NOT be updated by "sync" in feature workspace.
    # Let's check Base Workspace backend submodule.
    # It should still point to old commit unless we updated it?
    # Wait, remote-main was updated. Base Workspace pulls from remote-main.
    # If we didn't sync Base, it shouldn't have the new commit.
    # But submodules?
    # Let's check if a file exists in Base Workspace that was added to main.
    # We didn't add a file to main, we updated submodule pointer.
    # So we check submodule pointer in Base Workspace.
    # It should be OLD.
    
    # How to check submodule pointer?
    # git -C base_workspace/backend rev-parse HEAD
    # But backend repo in base workspace is a clone.
    # If we didn't run "git pull" in base workspace, it shouldn't change.
    
    # Let's verify Base Workspace is untouched.
    # We can check if "git status" in base workspace shows "behind"?
    # Or just check if it has the new commit in main.
    
    res = subprocess.run(["git", "rev-parse", "HEAD"], cwd=base_workspace, capture_output=True, text=True)
    base_head = res.stdout.strip()
    
    res = subprocess.run(["git", "ls-remote", "origin", "main"], cwd=base_workspace, capture_output=True, text=True)
    remote_head = res.stdout.split()[0]
    
    # Base HEAD should NOT be Remote HEAD (because we didn't sync all)
    assert base_head != remote_head

def test_sync_all_command(base_workspace, run_cli, daemon):
    """Test the sync --all command."""
    # 1. Create feature workspace
    run_cli(["create", "feature2", "--base", str(base_workspace)])
    ws_path = base_workspace.parent / "base-ws-feature2"
    
    # 2. Simulate remote update (add file to main)
    test_dir = base_workspace.parent
    remote_main = test_dir / "remote-main"
    main_update = test_dir / "main-update-2"
    subprocess.run(["git", "clone", str(remote_main), str(main_update)], check=True)
    (main_update / "new_file.txt").write_text("new file")
    subprocess.run(["git", "add", "."], cwd=main_update, check=True)
    subprocess.run(["git", "commit", "-m", "add new file"], cwd=main_update, check=True)
    subprocess.run(["git", "push"], cwd=main_update, check=True)
    
    # Create config
    import json
    config = {
        "base_path": str(base_workspace),
        "workspaces": {"feature2": {"path": str(ws_path)}}
    }
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config, f)

    # 3. Run sync --all
    # Check base-ws branch before sync
    subprocess.run(["git", "branch", "-vv"], cwd=base_workspace)
    
    result = run_cli(["sync", "--all"], cwd=ws_path)
    assert result.returncode == 0
    
    # 4. Verify Base Workspace updated
    if not (base_workspace / "new_file.txt").exists():
        subprocess.run(["git", "status"], cwd=base_workspace)
        subprocess.run(["git", "log", "--oneline", "-n", "5"], cwd=base_workspace)
        subprocess.run(["git", "remote", "-v"], cwd=base_workspace)
    assert (base_workspace / "new_file.txt").exists()
    
    # 5. Verify Feature Workspace updated
    assert (ws_path / "new_file.txt").exists()



def test_preview_sync(base_workspace, run_cli, daemon):
    """Test preview sync."""
    # 1. Create workspace
    run_cli(["create", "feature1", "--base", str(base_workspace)])
    ws_path = base_workspace.parent / "base-ws-feature1"
    backend_path = ws_path / "backend"
    
    # Create preview branch in base workspace to help manager?
    subprocess.run(["git", "branch", "preview"], cwd=base_workspace, check=False)
    
    # 2. Start preview in background
    import sys
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    env["WORKSPACE_DAEMON_PORT"] = "9090"
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
        
        # Verify base workspace is on preview branch
        # We can check with git
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=base_workspace, capture_output=True, text=True)
        assert res.stdout.strip() == "preview"
        
    finally:
        proc.terminate()
        proc.wait()

def test_sync_updates_submodule_to_main(base_workspace, run_cli, daemon):
    """
    Test that 'workspace sync' updates submodules to origin/main 
    and keeps them on the main branch.
    """
    # 1. Create feature workspace
    res = run_cli(["create", "submod-test", "--base", str(base_workspace)])
    assert res.returncode == 0
    
    ws_path = base_workspace.parent / "base-ws-submod-test"
    backend_path = ws_path / "backend"
    
    # Check initial state of submodule
    # Usually it is detached HEAD at the commit stored in superproject
    res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=backend_path, capture_output=True, text=True)
    initial_branch = res.stdout.strip()
    # It is likely 'HEAD' (detached)
    
    # The user EXPECTS it to be checked out to main and merged?
    # Or maybe valid state is user manually checked out main, and sync should keep it up to date.
    
    # Let's switch submodule to main first, as a user might do to start dev
    subprocess.run(["git", "checkout", "main"], cwd=backend_path, check=True)
    
    # 2. Simulate remote update in SUBMODULE
    test_dir = base_workspace.parent
    remote_backend = test_dir / "remote-backend"
    
    # Clone remote backend to push a change
    backend_updater = test_dir / "backend-updater"
    subprocess.run(["git", "clone", str(remote_backend), str(backend_updater)], check=True)
    (backend_updater / "new_feature.txt").write_text("feature v1")
    subprocess.run(["git", "add", "."], cwd=backend_updater, check=True)
    subprocess.run(["git", "commit", "-m", "update submodule content"], cwd=backend_updater, check=True)
    subprocess.run(["git", "push"], cwd=backend_updater, check=True)
    
    # Note: We do NOT update the superproject to point to this new commit.
    # We want to see if 'workspace sync' pulls the submodule changes INDEPENDENTLY 
    # (or if that is the requirement).
    
    # 3. Run sync
    # Create config for sync
    config = {
        "base_path": str(base_workspace),
        "workspaces": {"submod-test": {"path": str(ws_path)}}
    }
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config, f)
        
    result = run_cli(["sync"], cwd=ws_path)
    assert result.returncode == 0
    
    # 4. Verify submodule is updated
    assert (backend_path / "new_feature.txt").exists(), "Submodule was not updated to latest origin/main"
    
    # Verify still on main
    res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=backend_path, capture_output=True, text=True)
    assert res.stdout.strip() == "main", "Submodule should be on main branch"
