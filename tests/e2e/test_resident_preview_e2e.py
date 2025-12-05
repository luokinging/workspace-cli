import pytest
import subprocess
import time
import shutil
import signal
import os
from pathlib import Path
from workspace_cli.client.api import DaemonClient

# Constants
WORK_ROOT = Path("/tmp/test-resident-preview-root")
BASE_WORKSPACE = WORK_ROOT / "base-workspace"
DAEMON_PORT = 8002

@pytest.fixture(scope="module")
def setup_environment():
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True)
    
    # Create Base Workspace
    BASE_WORKSPACE.mkdir()
    subprocess.run(["git", "init"], cwd=BASE_WORKSPACE, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "Initial commit"], cwd=BASE_WORKSPACE, check=True)
    
    # Create Remote
    REMOTE_DIR = WORK_ROOT / "remote"
    REMOTE_DIR.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=REMOTE_DIR, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(REMOTE_DIR)], cwd=BASE_WORKSPACE, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=BASE_WORKSPACE, check=True)
    
    # Create workspace.json
    import json
    config_data = {
        "base_path": str(BASE_WORKSPACE),
        "workspaces": {},
        "preview": ["echo 'Preview Running'"],
        "preview_hook": {"before_clear": [], "after_preview": []}
    }
    (BASE_WORKSPACE / "workspace.json").write_text(json.dumps(config_data))
    
    yield
    
    # shutil.rmtree(WORK_ROOT)

@pytest.fixture(scope="module")
def daemon_process(setup_environment):
    cmd = ["python", "-m", "workspace_cli.main", "daemon", "--port", str(DAEMON_PORT)]
    process = subprocess.Popen(cmd, cwd=BASE_WORKSPACE)
    time.sleep(2)
    yield process
    process.terminate()
    process.wait()

def test_resident_preview_auto_exit(daemon_process):
    # 1. Create Workspaces A and B
    client = DaemonClient(port=DAEMON_PORT)
    client.create_workspaces(["A", "B"], base_path=str(BASE_WORKSPACE))
    
    # 2. Start Preview A (Resident)
    # Use custom port for CLI via env var
    env = os.environ.copy()
    env["WORKSPACE_DAEMON_PORT"] = str(DAEMON_PORT)
    
    cmd_a = ["python", "-m", "workspace_cli.main", "preview", "--workspace", "A"]
    process_a = subprocess.Popen(
        cmd_a, 
        cwd=BASE_WORKSPACE, 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for A to start streaming
    # We can read stdout non-blocking or just wait a bit
    time.sleep(2)
    assert process_a.poll() is None, "Process A should be running"
    
    # 3. Start Preview B (should preempt A)
    cmd_b = ["python", "-m", "workspace_cli.main", "preview", "--workspace", "B"]
    process_b = subprocess.Popen(
        cmd_b, 
        cwd=BASE_WORKSPACE, 
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for B to start and A to exit
    time.sleep(3)
    
    # Verify A exited
    assert process_a.poll() is not None, "Process A should have exited"
    
    # Verify B is running
    assert process_b.poll() is None, "Process B should be running"
    
    # Cleanup B
    process_b.terminate()
    process_b.wait()
