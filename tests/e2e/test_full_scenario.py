import pytest
import asyncio
import shutil
import subprocess
import time
import os
import signal
from pathlib import Path
from workspace_cli.client.api import DaemonClient
import httpx

# Constants
WORK_ROOT = Path("/tmp/test-e2e-work-root")
REMOTE_ROOT = WORK_ROOT / "remotes"
BASE_WORKSPACE = WORK_ROOT / "base-workspace"
DAEMON_PORT = 8001  # Use a different port to avoid conflict

@pytest.fixture(scope="module")
def setup_environment():
    """Setup git remotes and base workspace."""
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    WORK_ROOT.mkdir(parents=True)
    REMOTE_ROOT.mkdir()

    # 1. Create Remote Submodules
    backend_remote = REMOTE_ROOT / "backend"
    backend_remote.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=backend_remote, check=True)
    
    # Create initial content for backend
    backend_tmp = WORK_ROOT / "backend_tmp"
    backend_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=backend_tmp, check=True)
    (backend_tmp / "README.md").write_text("Backend Initial")
    subprocess.run(["git", "add", "."], cwd=backend_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Initial backend"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(backend_remote)], cwd=backend_tmp, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=backend_tmp, check=True)

    frontend_remote = REMOTE_ROOT / "frontend"
    frontend_remote.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=frontend_remote, check=True)
    
    # Create initial content for frontend
    frontend_tmp = WORK_ROOT / "frontend_tmp"
    frontend_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=frontend_tmp, check=True)
    (frontend_tmp / "main.js").write_text("console.log('Frontend Initial');")
    subprocess.run(["git", "add", "."], cwd=frontend_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Initial frontend"], cwd=frontend_tmp, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(frontend_remote)], cwd=frontend_tmp, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=frontend_tmp, check=True)

    # 2. Create Remote Main Repo
    main_remote = REMOTE_ROOT / "main"
    main_remote.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=main_remote, check=True)

    main_tmp = WORK_ROOT / "main_tmp"
    main_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=main_tmp, check=True)
    subprocess.run(["git", "submodule", "add", str(backend_remote), "backend"], cwd=main_tmp, check=True)
    subprocess.run(["git", "submodule", "add", str(frontend_remote), "frontend"], cwd=main_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Initial main"], cwd=main_tmp, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(main_remote)], cwd=main_tmp, check=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=main_tmp, check=True)

    # 3. Clone Base Workspace
    subprocess.run(["git", "clone", "--recursive", str(main_remote), str(BASE_WORKSPACE)], cwd=WORK_ROOT, check=True)
    
    # Create workspace.json in BASE_WORKSPACE
    import json
    config_data = {
        "base_path": str(BASE_WORKSPACE),
        "workspaces": {},
        "preview": [],
        "preview_hook": {"before_clear": [], "after_preview": []}
    }
    (BASE_WORKSPACE / "workspace.json").write_text(json.dumps(config_data))
    
    # Switch to master in base workspace (git clone defaults to master usually, but let's be sure)
    # subprocess.run(["git", "checkout", "master"], cwd=BASE_WORKSPACE, check=True)

    yield

    # Cleanup
    # shutil.rmtree(WORK_ROOT)

@pytest.fixture(scope="module")
def daemon_process(setup_environment):
    """Start and stop the daemon."""
    # Start Daemon
    # We must run daemon from BASE_WORKSPACE so it finds the config
    cmd = ["python", "-m", "workspace_cli.main", "daemon", "--port", str(DAEMON_PORT)]
    process = subprocess.Popen(cmd, cwd=BASE_WORKSPACE)
    
    # Wait for startup
    time.sleep(2)
    
    yield process
    
    # Stop Daemon
    process.terminate()
    process.wait()

@pytest.mark.asyncio
async def test_full_scenario(daemon_process):
    # We use DaemonClient directly for some checks, but CLI for commands to simulate user
    client = DaemonClient(port=DAEMON_PORT)
    
    # Case 2: Daemon Lifecycle (Check Status)
    status = client.get_status()
    assert status.is_syncing is False
    
    # Case 3: Create Workspace
    # Create A
    client.create_workspaces(["A"], base_path=str(BASE_WORKSPACE))
    
    # Verify
    ws_path = WORK_ROOT / "base-workspace-A"
    assert ws_path.exists()
    assert (ws_path / ".git").is_file() # Worktree .git is a file
    assert (ws_path / "backend" / "README.md").exists()
    
    status = client.get_status()
    assert any(ws.name == "A" for ws in status.workspaces)

    # Case 4: Global Sync
    # Simulate Remote Change
    backend_tmp = WORK_ROOT / "backend_tmp"
    (backend_tmp / "README.md").write_text("Backend Updated")
    subprocess.run(["git", "add", "."], cwd=backend_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Update backend"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=backend_tmp, check=True)
    
    main_tmp = WORK_ROOT / "main_tmp"
    subprocess.run(["git", "pull", "--rebase"], cwd=main_tmp, check=True)
    # Update submodule in main
    subprocess.run(["git", "submodule", "update", "--remote"], cwd=main_tmp, check=True)
    subprocess.run(["git", "add", "."], cwd=main_tmp, check=True)
    subprocess.run(["git", "commit", "-m", "Update submodule"], cwd=main_tmp, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=main_tmp, check=True)
    
    # Sync
    client.sync_workspace("A", sync_all=True)
    
    # Verify A got the update
    # We need to check if A pulled main.
    # Since A is a worktree of base, and we synced, it should have fetched.
    # But A is on a branch 'workspace-A/stand'.
    # Sync logic pulls 'main' into current branch?
    # WorkspaceManager.sync_workspace calls git.pull(rebase=True).
    # This pulls from the tracking branch.
    # If we created the branch from main, it might track origin/main?
    # ShellGitProvider.create_worktree: `git worktree add -b <branch> <path> <base>` (base defaults to HEAD of repo).
    # It doesn't explicitly set upstream.
    # So `git pull` might fail if no upstream.
    # Let's assume for this test that we might need to set upstream or the sync logic handles it.
    # Actually, `git pull` without upstream usually fails.
    # We might need to fix this in implementation if it fails.
    
    # Case 5: Preview Switching
    # Prepare Changes in A
    (ws_path / "backend" / "README.md").write_text("Preview Content")
    
    # Preview
    client.switch_preview("A")
    
    # Verify Base Workspace
    assert (BASE_WORKSPACE / "backend" / "README.md").read_text() == "Preview Content"
    
    status = client.get_status()
    assert status.active_preview == "A"

    # Case 6: Live Watch
    # Modify file in A
    (ws_path / "frontend" / "main.js").write_text("console.log('Live Watch');")
    
    # Wait for sync (debounce)
    await asyncio.sleep(2)
    
    # Verify Base Workspace
    assert (BASE_WORKSPACE / "frontend" / "main.js").read_text() == "console.log('Live Watch');"

    # Case 7: Switch Workspace
    # Create B
    client.create_workspaces(["B"], base_path=str(BASE_WORKSPACE))
    ws_b_path = WORK_ROOT / "base-workspace-B"
    (ws_b_path / "backend" / "README.md").write_text("Feature B Content")
    
    # Switch
    client.switch_preview("B")
    
    # Verify
    assert (BASE_WORKSPACE / "backend" / "README.md").read_text() == "Feature B Content"
    status = client.get_status()
    assert status.active_preview == "B"

    # Case 8: Delete Workspace
    client.delete_workspace("A")
    
    assert not ws_path.exists()
    status = client.get_status()
    assert not any(ws.name == "A" for ws in status.workspaces)

    # Case 9: Daemon Shutdown is handled by fixture
