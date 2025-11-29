import pytest
import time
import subprocess
from pathlib import Path
import threading

def test_preview_sync(base_workspace, run_cli):
    # 1. Create workspace
    run_cli(["create", "feature1"])
    ws_path = base_workspace.parent / "base-ws-feature1"
    repo_path = ws_path / "repo1"
    
    # 2. Start preview in background
    # We need to run this in a thread or subprocess that we can kill
    # But run_cli uses subprocess.run which blocks.
    # Let's use Popen directly for this test
    import sys
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    cmd = [sys.executable, "-m", "workspace_cli.main", "preview", "--workspace", "feature1"]
    
    proc = subprocess.Popen(
        cmd,
        cwd=base_workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Wait for watcher to start
        time.sleep(2)
        
        # 3. Create a file in feature workspace
        new_file = repo_path / "new_file.txt"
        new_file.write_text("hello")
        
        # Wait for sync
        time.sleep(2)
        
        # 4. Verify file exists in base workspace (preview target)
        # Note: The sync logic syncs to base_workspace/repo1
        # But wait, does it sync to a preview branch?
        # sync.py: 
        #   checkout_new_branch(target_repo_path, preview_branch, force=True)
        #   shutil.copy2(src_file, dst_file)
        
        # So the file should be in base_workspace/repo1
        # 4. Verify file exists in base workspace (preview target)
        target_file = base_workspace / "repo1" / "new_file.txt"
        assert target_file.exists()
        assert target_file.read_text() == "hello"
        
    finally:
        proc.terminate()
        proc.wait()

def test_sync_rules(base_workspace, run_cli):
    # Setup rules repo in config
    import json
    config_path = base_workspace.parent / "workspace.json"
    with open(config_path) as f:
        config = json.load(f)
    
    # Create rules repo
    rules_repo = base_workspace / "rules"
    rules_repo.mkdir()
    subprocess.run(["git", "init"], cwd=rules_repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=rules_repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=rules_repo, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=rules_repo, check=True)
    
    # Add remote (simulate origin)
    origin_rules = base_workspace.parent / "origin_rules"
    origin_rules.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=origin_rules, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(origin_rules)], cwd=rules_repo, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=rules_repo, check=True) # master or main? git init default depends on version
    
    # Update config
    config["repos"].append({"name": "rules", "path": "rules"})
    config["rules_repo"] = "rules"
    with open(config_path, "w") as f:
        json.dump(config, f)
        
    # Create feature workspace
    result = run_cli(["create", "feature1"])
    assert result.returncode == 0, f"Create failed: {result.stdout}\n{result.stderr}"
    
    ws_path = base_workspace.parent / "base-ws-feature1"
    rules_ws_path = ws_path / "rules"
    
    assert rules_ws_path.exists(), "Rules repo not created in feature workspace"
    
    # Modify rules in feature workspace
    (rules_ws_path / "rule.txt").write_text("new rule")
    
    # Run syncrule from feature workspace
    # We need to change cwd to feature workspace
    import sys
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    cmd = [sys.executable, "-m", "workspace_cli.main", "syncrule"]
    
    result = subprocess.run(
        cmd,
        cwd=ws_path, # Run from feature workspace
        env=env,
        capture_output=True,
        text=True
    )
    
    assert result.returncode == 0, f"Sync failed: {result.stdout}\n{result.stderr}"
    
    # Verify pushed to origin
    # Clone origin to check
    check_dir = base_workspace.parent / "check_rules"
    if check_dir.exists():
        import shutil
        shutil.rmtree(check_dir)
    subprocess.run(["git", "clone", str(origin_rules), str(check_dir)], check=True)
    
    assert (check_dir / "rule.txt").exists()
