import os
import shutil
import subprocess
import time
import sys
from pathlib import Path

# Configuration
TEST_ROOT = Path("e2e_manual_test_env").resolve()
PYTHON_CMD = sys.executable
CLI_CMD = [PYTHON_CMD, "-m", "workspace_cli.main"]

def run_cmd(cmd, cwd=None, check=True):
    """Run a command and print it."""
    cwd_str = f" in {cwd}" if cwd else ""
    print(f"\n[USER] $ {' '.join(cmd)}{cwd_str}")
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    if result.stdout:
        print(f"[STDOUT]\n{result.stdout.strip()}")
    if result.stderr:
        print(f"[STDERR]\n{result.stderr.strip()}")
    
    if check and result.returncode != 0:
        print(f"!!! COMMAND FAILED with code {result.returncode} !!!")
        sys.exit(1)
    return result

def setup_env():
    print("=== Case 1: Environment Setup ===")
    if TEST_ROOT.exists():
        shutil.rmtree(TEST_ROOT)
    TEST_ROOT.mkdir()
    
    # Git config for test
    git_config = ["-c", "user.email=test@example.com", "-c", "user.name=Test User", "-c", "protocol.file.allow=always"]
    
    # 1. Create Remote Submodules
    remote_backend = TEST_ROOT / "remote-backend"
    remote_backend.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_backend, check=True)
    
    backend_tmp = TEST_ROOT / "backend-tmp"
    backend_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=backend_tmp, check=True)
    subprocess.run(["git"] + git_config + ["commit", "--allow-empty", "-m", "init"], cwd=backend_tmp, check=True)
    (backend_tmp / "backend.txt").write_text("backend v1")
    subprocess.run(["git", "add", "."], cwd=backend_tmp, check=True)
    subprocess.run(["git"] + git_config + ["commit", "-m", "add backend.txt"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=backend_tmp, check=True)
    subprocess.run(["git", "push", str(remote_backend), "main"], cwd=backend_tmp, check=True)
    
    # 2. Create Remote Main Repo
    remote_main = TEST_ROOT / "remote-main"
    remote_main.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_main, check=True)
    
    main_tmp = TEST_ROOT / "main-tmp"
    main_tmp.mkdir()
    subprocess.run(["git", "init"], cwd=main_tmp, check=True)
    subprocess.run(["git"] + git_config + ["commit", "--allow-empty", "-m", "init"], cwd=main_tmp, check=True)
    
    # Add submodule
    subprocess.run(["git", "config", "--global", "protocol.file.allow", "always"], cwd=main_tmp, check=True)
    subprocess.run(["git", "submodule", "add", str(remote_backend), "backend"], cwd=main_tmp, check=True)
    subprocess.run(["git"] + git_config + ["commit", "-m", "add submodule"], cwd=main_tmp, check=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=main_tmp, check=True)
    subprocess.run(["git", "push", str(remote_main), "main"], cwd=main_tmp, check=True)
    
    # 3. Clone Base Workspace
    base_ws = TEST_ROOT / "base-ws"
    print(f"\n[USER] Cloning Base Workspace to {base_ws}")
    subprocess.run(["git", "clone", "--recursive", str(remote_main), str(base_ws)], check=True)
    
    # Config user in base_ws
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=base_ws, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=base_ws, check=True)
    
    return base_ws

def test_create(base_ws):
    print("\n=== Case 2: Create Workspace ===")
    run_cmd(CLI_CMD + ["create", "feature-a", "--base", str(base_ws)])
    
    ws_path = base_ws.parent / "base-ws-feature-a"
    if ws_path.exists() and (ws_path / "backend" / "backend.txt").exists():
        print(">>> VERIFICATION PASSED: Workspace created and populated.")
    else:
        print(">>> VERIFICATION FAILED: Workspace missing or empty.")
        sys.exit(1)
    return ws_path

def test_sync(base_ws, ws_path):
    print("\n=== Case 3: Sync Workspace ===")
    
    # Simulate remote update
    print("[SYSTEM] Simulating remote update...")
    remote_backend = TEST_ROOT / "remote-backend"
    backend_update = TEST_ROOT / "backend-update"
    subprocess.run(["git", "clone", str(remote_backend), str(backend_update)], check=True, capture_output=True)
    (backend_update / "new_feature.txt").write_text("feature v1")
    subprocess.run(["git", "add", "."], cwd=backend_update, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add feature"], cwd=backend_update, check=True, capture_output=True)
    subprocess.run(["git", "push"], cwd=backend_update, check=True, capture_output=True)
    
    main_update = TEST_ROOT / "main-update"
    subprocess.run(["git", "clone", str(TEST_ROOT / "remote-main"), str(main_update)], check=True, capture_output=True)
    subprocess.run(["git", "submodule", "update", "--init", "--remote"], cwd=main_update, check=True, capture_output=True)
    subprocess.run(["git", "add", "backend"], cwd=main_update, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "update backend pointer"], cwd=main_update, check=True, capture_output=True)
    subprocess.run(["git", "push"], cwd=main_update, check=True, capture_output=True)
    
    # Create workspace.json for sync
    import json
    config = {
        "base_path": str(base_ws), 
        "repos": [
            {"name": "backend", "path": "backend"}
        ]
    }
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config, f)

    # Run sync (Current Only)
    print("[USER] Running 'workspace sync' (Current Only)...")
    run_cmd(CLI_CMD + ["sync"], cwd=ws_path)
    
    if (ws_path / "backend" / "new_feature.txt").exists():
        print(">>> VERIFICATION PASSED: Sync updated current workspace.")
    else:
        print(">>> VERIFICATION FAILED: Sync did not update current workspace.")
        sys.exit(1)
        
    # Verify Base Workspace NOT updated
    if (base_ws / "backend" / "new_feature.txt").exists():
        print(">>> VERIFICATION FAILED: Base workspace updated but should not be (without --all).")
        # Note: This might fail if Base was somehow updated by something else, but it shouldn't be.
        # However, Base Workspace pulls from remote-main. 
        # remote-main was updated.
        # But we didn't run pull in Base.
        sys.exit(1)
    else:
        print(">>> VERIFICATION PASSED: Base workspace not updated (as expected).")

    # Run sync --all
    print("[USER] Running 'workspace sync --all'...")
    run_cmd(CLI_CMD + ["sync", "--all"], cwd=ws_path)
    
    if (base_ws / "backend" / "new_feature.txt").exists():
        print(">>> VERIFICATION PASSED: Sync --all updated Base workspace.")
    else:
        print(">>> VERIFICATION FAILED: Sync --all did not update Base workspace.")
        sys.exit(1)

def test_preview(base_ws, ws_path):
    print("\n=== Case 4: Preview Workspace ===")
    
    # Start preview in background
    print("[USER] Starting preview (background)...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    proc = subprocess.Popen(
        CLI_CMD + ["preview", "--workspace", "feature-a"],
        cwd=base_ws,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        time.sleep(3) # Wait for startup
        
        # VERIFY ROOT BRANCH SWITCH
        res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=base_ws, capture_output=True, text=True)
        current_branch = res.stdout.strip()
        print(f"[VERIFY] Base Workspace Branch: {current_branch}")
        if current_branch == "feature-a/preview":
            print(">>> VERIFICATION PASSED: Base Workspace switched to feature-a/preview.")
        else:
            print(f">>> VERIFICATION FAILED: Expected feature-a/preview, got {current_branch}")
            # Don't exit yet, check file sync too
        
        print("[USER] Making uncommitted change in feature-a...")
        (ws_path / "backend" / "preview_test.txt").write_text("hello preview")
        
        time.sleep(3) # Wait for sync
        
        target_file = base_ws / "backend" / "preview_test.txt"
        if target_file.exists() and target_file.read_text() == "hello preview":
            print(">>> VERIFICATION PASSED: Preview synced file.")
        else:
            print(">>> VERIFICATION FAILED: Preview file not found in target.")
            # print stdout/stderr
            out, err = proc.communicate(timeout=1)
            print(f"Preview Output:\n{out}\n{err}")
            sys.exit(1)
            
    finally:
        proc.terminate()
        proc.wait()

def test_delete(base_ws):
    print("\n=== Case 6: Delete Workspace ===")
    run_cmd(CLI_CMD + ["delete", "feature-a"])
    
    ws_path = base_ws.parent / "base-ws-feature-a"
    if not ws_path.exists():
        print(">>> VERIFICATION PASSED: Workspace deleted.")
    else:
        print(">>> VERIFICATION FAILED: Workspace still exists.")
        sys.exit(1)

def main():
    try:
        base_ws = setup_env()
        ws_path = test_create(base_ws)
        test_sync(base_ws, ws_path)
        test_preview(base_ws, ws_path)
        test_delete(base_ws)
        print("\n=== ALL MANUAL SCENARIOS PASSED ===")
    except Exception as e:
        print(f"\n!!! UNEXPECTED ERROR: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        if TEST_ROOT.exists():
            shutil.rmtree(TEST_ROOT)

if __name__ == "__main__":
    main()
