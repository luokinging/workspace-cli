import pytest
import shutil
import subprocess
import json
from pathlib import Path

@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary directory for tests."""
    d = tmp_path / "workspace_test"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir()
    return d

@pytest.fixture
def git_author_config():
    return [
        "-c", "user.email=test@example.com",
        "-c", "user.name=Test User",
        "-c", "protocol.file.allow=always"
    ]

@pytest.fixture
def base_workspace(test_dir, git_author_config):
    """
    Setup a base workspace with submodules.
    Structure:
    - remote-backend (bare)
    - remote-frontend (bare)
    - remote-main (bare, with submodules)
    - base-ws (cloned from remote-main)
    """
    # 1. Create Remote Submodules
    remote_backend = test_dir / "remote-backend"
    remote_backend.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_backend, check=True)
    
    # Initialize backend content
    backend_tmp = test_dir / "backend-tmp"
    backend_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=backend_tmp, check=True)
    subprocess.run(["git"] + git_author_config + ["commit", "--allow-empty", "-m", "init"], cwd=backend_tmp, check=True)
    (backend_tmp / "backend.txt").write_text("backend v1")
    subprocess.run(["git", "add", "."], cwd=backend_tmp, check=True)
    subprocess.run(["git"] + git_author_config + ["commit", "-m", "add backend.txt"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "push", str(remote_backend), "main"], cwd=backend_tmp, check=True)
    
    # 2. Create Remote Main Repo
    remote_main = test_dir / "remote-main"
    remote_main.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_main, check=True)
    
    # Initialize main content and add submodules
    main_tmp = test_dir / "main-tmp"
    main_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=main_tmp, check=True)
    subprocess.run(["git"] + git_author_config + ["commit", "--allow-empty", "-m", "init"], cwd=main_tmp, check=True)
    
    # Add submodule
    # We need to pass config to submodule add command too, but it runs clone internally.
    # The -c option applies to the immediate command.
    # For submodule add, we might need to set it globally or in the repo config first.
    subprocess.run(["git", "config", "--global", "protocol.file.allow", "always"], cwd=main_tmp, check=True)
    subprocess.run(["git", "submodule", "add", str(remote_backend), "backend"], cwd=main_tmp, check=True)
    subprocess.run(["git"] + git_author_config + ["commit", "-m", "add submodule"], cwd=main_tmp, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=main_tmp, check=True)
    subprocess.run(["git", "push", str(remote_main), "main"], cwd=main_tmp, check=True)
    
    # 3. Clone Base Workspace
    base_ws = test_dir / "base-ws"
    subprocess.run(["git", "clone", "--recursive", str(remote_main), str(base_ws)], check=True)
    
    # Configure base_ws user
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=base_ws, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=base_ws, check=True)
    
    # Create workspace.json (REQUIRED for daemon to start)
    config = {
        "base_path": str(base_ws.resolve()),
        "workspaces": {},
        "preview": [],
        "preview_hook": {"before_clear": [], "after_preview": []}
    }
    with open(base_ws / "workspace.json", "w") as f:
        json.dump(config, f)
    
    return base_ws

@pytest.fixture
def run_cli(base_workspace):
    """Helper to run CLI commands."""
    def _run(args, cwd=None):
        import sys
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        if cwd is None:
            cwd = base_workspace
        
        # Set daemon port if provided (default 9090 for tests)
        if "WORKSPACE_DAEMON_PORT" not in env:
            env["WORKSPACE_DAEMON_PORT"] = "9090"
            
        cmd = [sys.executable, "-m", "workspace_cli.main"] + args
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            env=env,
            capture_output=True, 
            text=True
        )
        return result
    return _run

@pytest.fixture
def daemon(base_workspace):
    """Start the daemon for tests."""
    import sys
    import os
    import time
    import requests
    
    # Start daemon
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    # Use a random port or default 9000?
    # Tests use default 9000.
    # We should probably use a different port to avoid conflict with real daemon.
    # But client defaults to 9000.
    # Let's use 9000 for now, assuming no other daemon is running.
    # Or we can configure client to use a different port.
    # But run_cli uses default.
    # We can set WORKSPACE_DAEMON_PORT env var.
    
    port = 9090
    env["WORKSPACE_DAEMON_PORT"] = str(port)
    
    cmd = [sys.executable, "-m", "workspace_cli.main", "daemon", "--port", str(port)]
    
    proc = subprocess.Popen(
        cmd,
        cwd=base_workspace, # Daemon runs in base workspace
        env=env,
        stdout=None, # Inherit
        stderr=None, # Inherit
        text=True
    )
    
    # Wait for startup
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            requests.get(f"http://localhost:{port}/status")
            break
        except requests.ConnectionError:
            time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError(f"Daemon failed to start (check logs)")
        
    yield f"http://localhost:{port}"
    
    # Stop daemon
    proc.terminate()
    proc.wait()
