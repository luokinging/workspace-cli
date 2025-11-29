import pytest
import shutil
import json
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.core.sync import sync_workspaces

def test_sync_expand(base_workspace, run_cli):
    """Test workspace_expand_folder logic."""
    # 1. Setup Base Workspace with expand folder and config
    expand_folder = base_workspace / "expand"
    expand_folder.mkdir()
    (expand_folder / "config.json").write_text('{"foo": "bar"}')
    (expand_folder / "subdir").mkdir()
    (expand_folder / "subdir" / "script.py").write_text('print("hello")')
    
    # Update config in base workspace (if it exists, or create it)
    # The CLI loads config from CWD or arguments.
    # We need to make sure `sync` command loads a config that has `workspace_expand_folder`.
    # `sync` command calls `load_config()`.
    # `load_config` looks for `workspace.json` in CWD or parents.
    
    # Create workspace.json in base_workspace
    config_data = {
        "base_path": str(base_workspace),
        "repos": [], # We can leave this empty or populate if needed for sync
        "workspace_expand_folder": "expand"
    }
    # We need repos for sync to work without error?
    # sync_workspaces iterates repos to update them.
    # If repos is empty, it just updates base and siblings (merge main).
    # That's fine for this test.
    
    with open(base_workspace / "workspace.json", "w") as f:
        json.dump(config_data, f)
        
    # Commit changes to base workspace so they are in main
    import subprocess
    subprocess.run(["git", "add", "."], cwd=base_workspace, check=True)
    subprocess.run(["git", "commit", "-m", "add expand folder"], cwd=base_workspace, check=True)
    
    # 2. Create Sibling Workspace
    # We can use CLI create, but we need to make sure it uses the config we just made?
    # CLI create with --base uses the base path.
    # If we run create from base_workspace, it might pick up config?
    # Let's run create command.
    run_cli(["create", "feature1", "--base", str(base_workspace)])
    
    ws_path = base_workspace.parent / "base-ws-feature1"
    
    # 3. Create conflicting files in Sibling to test overwrite
    (ws_path / "config.json").write_text('{"old": "value"}')
    (ws_path / "subdir").mkdir(exist_ok=True)
    (ws_path / "subdir" / "old.txt").write_text("old")
    
    # 4. Run sync
    # We need to run sync from within the workspace (or base).
    # And we need to ensure it picks up the config with `workspace_expand_folder`.
    # If we run from ws_path, `load_config` should find `workspace.json` in base_path?
    # `load_config` logic:
    # It looks for `workspace.json` in current dir.
    # If not found, it checks if we are in a workspace structure and looks in base path?
    # Let's check `config.py` logic.
    # If `config.py` doesn't support looking in base path, we might need to copy config or symlink it?
    # Or `create` command should have created a config in the new workspace?
    # `create` command: `save_config(config, save_path)` where save_path is CWD/workspace.json.
    # If we ran create from base_workspace, it saved config there.
    # But new workspace doesn't have it.
    
    # Let's manually put config in new workspace for now, or rely on `load_config` finding it if it searches up?
    # Usually `workspace.json` is at the root of the project (parent of base_ws)?
    # No, `base_path` points to Base Workspace.
    # Config is usually IN the Base Workspace or the Root?
    # `doc.md` says `workspace.json` is in the root of the workspace folder?
    # "Configuration: workspace.json ... may still hold preferences".
    
    # Let's assume we copy the config to the new workspace or it's shared.
    # For this test, let's write config to ws_path.
    with open(ws_path / "workspace.json", "w") as f:
        json.dump(config_data, f)
        
    # Run sync
    result = run_cli(["sync"], cwd=ws_path)
    assert result.returncode == 0, f"Sync failed: {result.stdout}\n{result.stderr}"
    
    # 5. Verify Expansion
    assert (ws_path / "config.json").read_text() == '{"foo": "bar"}'
    assert (ws_path / "subdir" / "script.py").exists()
    # old.txt should be gone if we delete existing target_path (which is subdir)
    # The logic: `if target_path.exists(): shutil.rmtree(target_path)`
    # target_path is `subdir`. So `subdir` is removed and recreated.
    # So `old.txt` should be gone.
    assert not (ws_path / "subdir" / "old.txt").exists()
