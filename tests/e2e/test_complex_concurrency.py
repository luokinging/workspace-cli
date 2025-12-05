import pytest
import asyncio
import shutil
import subprocess
import time
import os
import signal
from pathlib import Path
import json

# Constants
WORK_ROOT = Path("/tmp/test-e2e-concurrency")
REMOTE_ROOT = WORK_ROOT / "remotes"
BASE_WORKSPACE = WORK_ROOT / "base-workspace"
LOG_DIR = WORK_ROOT / "logs"
DAEMON_PORT = 8002  # Different port

@pytest.fixture(scope="module")
def setup_environment():
    """Setup git remotes, base workspace, and logs."""
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True)
    REMOTE_ROOT.mkdir()
    LOG_DIR.mkdir()

    # 1. Create Remote Main Repo
    main_remote = REMOTE_ROOT / "main"
    main_remote.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=main_remote, check=True)

    main_tmp = WORK_ROOT / "main_tmp"
    main_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=main_tmp, check=True)
    (main_tmp / "README.md").write_text("Initial Content")
    subprocess.run(["git", "add", "."], cwd=main_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=main_tmp, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(main_remote)], cwd=main_tmp, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=main_tmp, check=True)

    # 2. Clone Base Workspace
    subprocess.run(["git", "clone", str(main_remote), str(BASE_WORKSPACE)], cwd=WORK_ROOT, check=True)
    
    # Create workspace.json in BASE_WORKSPACE with log_path
    config_data = {
        "base_path": str(BASE_WORKSPACE),
        "workspaces": {},
        "preview": ["echo 'Preview Running'"],
        "preview_hook": {
            "before_clear": ["echo 'Before Clear'"], 
            "after_preview": ["echo 'After Preview'"]
        },
        "log_path": str(LOG_DIR)
    }
    (BASE_WORKSPACE / "workspace.json").write_text(json.dumps(config_data))
    
    yield
    
    # Cleanup
    # shutil.rmtree(WORK_ROOT)

@pytest.fixture(scope="module")
def daemon_process(setup_environment):
    """Start and stop the daemon."""
    # Start Daemon
    cmd = ["python", "-m", "workspace_cli.main", "daemon", "--port", str(DAEMON_PORT), "--debug"]
    
    # Ensure PYTHONPATH includes project root
    env = os.environ.copy()
    project_root = str(Path.cwd().resolve())
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    # We run from BASE_WORKSPACE
    process = subprocess.Popen(cmd, cwd=BASE_WORKSPACE, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for startup
    time.sleep(3)
    
    yield process
    
    # Stop Daemon
    process.terminate()
    process.wait()

def run_cli(args, cwd=BASE_WORKSPACE):
    """Run CLI command."""
    env = os.environ.copy()
    env["WORKSPACE_DAEMON_PORT"] = str(DAEMON_PORT)
    project_root = str(Path.cwd().resolve())
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    return subprocess.run(
        ["python", "-m", "workspace_cli.main"] + args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True
    )

def start_preview_process(workspace, cwd=BASE_WORKSPACE):
    """Start preview command in background."""
    env = os.environ.copy()
    env["WORKSPACE_DAEMON_PORT"] = str(DAEMON_PORT)
    project_root = str(Path.cwd().resolve())
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")
    
    return subprocess.Popen(
        ["python", "-m", "workspace_cli.main", "preview", "--workspace", workspace],
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def test_concurrency_and_logging(daemon_process):
    # 1. Create Workspaces A and B
    res = run_cli(["create", "A", "B"])
    assert res.returncode == 0
    
    # 2. Start Preview A
    print("Starting Preview A...")
    proc_a = start_preview_process("A")
    
    # Wait a bit for it to start
    time.sleep(3)
    assert proc_a.poll() is None, "Preview A should be running"
    
    # 3. Start Preview B
    print("Starting Preview B...")
    proc_b = start_preview_process("B")
    
    # Wait a bit for switch
    time.sleep(5)
    
    # 4. Verify A exited
    assert proc_a.poll() is not None, "Preview A should have exited"
    
    # 5. Verify B is running
    assert proc_b.poll() is None, "Preview B should be running"
    
    # 6. Verify Logs
    log_files = list(LOG_DIR.glob("workspace-cli*"))
    assert len(log_files) > 0, "Log file should exist"
    
    log_content = log_files[0].read_text()
    assert "Logging configured to" in log_content or "Debug mode enabled" in log_content
    assert "create_workspace called" in log_content
    
    # Cleanup processes
    proc_b.terminate()
    proc_b.wait()
