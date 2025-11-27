import pytest
import shutil
import subprocess
import json
from pathlib import Path

@pytest.fixture
def test_dir(tmp_path):
    """Create a temporary directory for tests."""
    d = tmp_path / "workspace_test"
    d.mkdir()
    return d

@pytest.fixture
def base_workspace(test_dir):
    """Setup a base workspace with a repo."""
    base_ws = test_dir / "base-ws"
    base_ws.mkdir()
    
    # Setup a repo
    repo_path = base_ws / "repo1"
    repo_path.mkdir()
    subprocess.run(["git", "init"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=repo_path, check=True)
    
    # Create config
    config = {
        "base_path": str(base_ws),
        "repos": [
            {"name": "repo1", "path": "repo1"}
        ]
    }
    with open(test_dir / "workspace.json", "w") as f:
        json.dump(config, f)
        
    return base_ws

@pytest.fixture
def run_cli(base_workspace):
    """Helper to run CLI commands."""
    def _run(args):
        import sys
        import os
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        cmd = [sys.executable, "-m", "workspace_cli.main"] + args
        result = subprocess.run(
            cmd, 
            cwd=base_workspace, 
            env=env,
            capture_output=True, 
            text=True
        )
        return result
    return _run
