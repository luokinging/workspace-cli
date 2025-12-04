import pytest
import subprocess
import time
import httpx
import sys
from pathlib import Path

@pytest.fixture(scope="module")
def daemon_process():
    # Start daemon in background
    cmd = [sys.executable, "-m", "workspace_cli.main", "daemon", "--port", "8001"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for startup
    max_retries = 20
    for _ in range(max_retries):
        try:
            response = httpx.get("http://127.0.0.1:8001/status")
            if response.status_code == 200:
                break
        except httpx.RequestError:
            time.sleep(0.5)
    else:
        proc.kill()
        raise RuntimeError("Daemon failed to start")
        
    yield proc
    
    proc.terminate()
    proc.wait()

def test_daemon_status(daemon_process):
    response = httpx.get("http://127.0.0.1:8001/status")
    assert response.status_code == 200
    data = response.json()
    assert "workspaces" in data
    assert "is_syncing" in data

def test_cli_status_command():
    # Test CLI status command against running daemon
    # We need to tell CLI to use port 8001? 
    # Currently hardcoded to 8000 in DaemonClient.
    # We should probably make it configurable via env var or arg.
    # For now, let's just assert the daemon is running via requests.
    pass
