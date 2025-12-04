
import socket
import threading
import time
import pytest
from pathlib import Path
from workspace_cli.core.runner import PreviewRunner
from workspace_cli.models import WorkspaceConfig, PreviewHooks

def test_runner_concurrency_interruption(tmp_path):
    """
    Test that a second client can connect and interrupt the first client.
    """
    # Setup Config
    base_path = tmp_path / "base"
    base_path.mkdir()
    
    config = WorkspaceConfig(
        base_path=base_path,
        workspaces={},
        preview=["sleep 2"], # Simulate long running process
        preview_hook=PreviewHooks()
    )
    
    # Start Runner
    runner = PreviewRunner(config)
    runner_thread = threading.Thread(target=runner.start, daemon=True)
    runner_thread.start()
    
    time.sleep(1) # Wait for startup
    
    port_file = base_path / ".run_preview.port"
    assert port_file.exists()
    port = int(port_file.read_text().strip())
    
    # Client A Connects
    s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s1.connect(('127.0.0.1', port))
    s1.sendall(b"PREVIEW client-a")
    resp1 = s1.recv(1024)
    assert resp1 == b"ACCEPTED"
    print("Client A connected")
    
    time.sleep(0.5)
    
    # Client B Connects
    print("Client B connecting...")
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s2.connect(('127.0.0.1', port))
    s2.sendall(b"PREVIEW client-b")
    resp2 = s2.recv(1024)
    assert resp2 == b"ACCEPTED"
    print("Client B connected")
    
    # Verify Client A is disconnected
    # s1.recv should return empty bytes (closed) or error
    try:
        s1.settimeout(1.0)
        data = s1.recv(1024)
        assert data == b"" # Closed
        print("Client A disconnected as expected")
    except socket.timeout:
        pytest.fail("Client A was not disconnected")
    except OSError:
        print("Client A disconnected (OSError)")

    runner.stop()
    runner_thread.join()
