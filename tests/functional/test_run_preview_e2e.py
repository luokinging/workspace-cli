import pytest
import subprocess
import time
import os
import signal
import socket
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, PreviewHooks
from workspace_cli.config import save_config

def test_run_preview_e2e(tmp_path):
    # 1. Setup Environment
    base_ws = tmp_path / "base-ws"
    base_ws.mkdir()
    feature_ws = tmp_path / "feature-ws"
    feature_ws.mkdir()
    
    # Create remote repo
    remote_ws = tmp_path / "remote-ws"
    remote_ws.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_ws, check=True)
    
    # Clone base_ws from remote
    subprocess.run(["git", "clone", str(remote_ws), "base-ws"], cwd=tmp_path, check=True)
    
    # Configure base_ws
    subprocess.run(["git", "config", "user.email", "you@example.com"], cwd=base_ws, check=True)
    subprocess.run(["git", "config", "user.name", "Your Name"], cwd=base_ws, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=base_ws, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=base_ws, check=True)
    
    # Create feature_ws as worktree
    # feature_ws path was defined above but mkdir called. We should remove it first or let worktree create it.
    feature_ws.rmdir()
    subprocess.run(["git", "worktree", "add", "-b", "feature-a/stand", str(feature_ws)], cwd=base_ws, check=True)
    
    # Create config
    config = WorkspaceConfig(
        base_path=base_ws,
        workspaces={
            "feature-a": {"path": str(feature_ws)}
        },
        preview=["python3 -u -c \"import time; print('[Server] Running'); time.sleep(5)\""],
        preview_hook=PreviewHooks(
            before_clear=["python3 -u -c \"print('[Hook] Before Clear')\""],
            after_preview=["python3 -u -c \"print('[Hook] After Preview')\""]
        )
    )
    save_config(config, base_ws / "workspace.json")
    # Also save to feature_ws so it can be found
    save_config(config, feature_ws / "workspace.json")
    
    # 2. Start Run-Preview in background
    # We use subprocess to run the actual CLI command
    # Ensure workspace-cli is installed or run via python -m
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()
    
    cmd = ["python3", "-m", "workspace_cli.main", "run-preview"]
    
    # Create a log file to capture output
    log_file = tmp_path / "run_preview.log"
    
    with open(log_file, "w") as f:
        process = subprocess.Popen(
            cmd,
            cwd=base_ws,
            stdout=f,
            stderr=subprocess.STDOUT,
            env=env,
            preexec_fn=os.setsid
        )
        
    try:
        # Wait for runner to start (check port file)
        port_file = base_ws / ".run_preview.port"
        for _ in range(50):
            if port_file.exists():
                break
            time.sleep(0.1)
        assert port_file.exists(), "Runner failed to start (port file missing)"
        
        # 3. Trigger Preview from Feature Workspace
        # We can mock the CLI call or just use the socket directly to verify IPC
        # But let's try to run the actual CLI command to verify full integration
        
        # We need to mock 'init_preview' or ensure it doesn't fail.
        # Since we have a dummy git repo, 'rebuild_preview' might fail if it tries to do real git ops 
        # like 'fetch origin'.
        # For this test, we might want to mock the git operations or just verify IPC.
        # But `run-preview` calls `rebuild_preview` inside the runner process.
        # If `rebuild_preview` fails, the runner logs it.
        
        # Let's run `workspace preview` and see if it connects.
        # We can mock `init_preview` in the CLI process if we want, but we are running a subprocess.
        
        # To make this robust without full git setup, we might rely on the fact that 
        # `run-preview` logs output.
        
        trigger_cmd = ["python3", "-m", "workspace_cli.main", "preview", "--workspace", "feature-a", "--once"]
        subprocess.run(trigger_cmd, cwd=feature_ws, env=env, check=False) # check=False because sync might fail
        
        # 4. Verify Output
        time.sleep(2) # Wait for processing
        
        log_content = log_file.read_text()
        print("Log Content:\n", log_content)
        
        if "[Hook] Before Clear" not in log_content:
             print("DEBUG: Missing hook output. Full log above.")
        
        assert "Preview Runner Started" in log_content
        assert "Received trigger for workspace: feature-a" in log_content
        assert "[Hook] Before Clear" in log_content
        assert "[Server] Running" in log_content
        assert "[Hook] After Preview" in log_content
        
    finally:
        # 5. Stop
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()
