import os
import shutil
import pytest
from pathlib import Path
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.core.sync import sync_rules
from workspace_cli.utils.git import run_git_cmd

@pytest.fixture
def temp_workspace_env(tmp_path):
    """
    Creates a temporary environment with:
    - A base directory
    - A rules repo (git initialized)
    - Two workspaces: base-ws1, base-ws2
    """
    base_dir = tmp_path / "workspaces"
    base_dir.mkdir()
    
    # Create rules repo origin
    rules_origin = tmp_path / "rules_origin"
    rules_origin.mkdir()
    run_git_cmd(["init", "--bare"], rules_origin)
    
    # Create workspaces
    ws1 = base_dir / "base-ws1"
    ws1.mkdir()
    ws2 = base_dir / "base-ws2"
    ws2.mkdir()
    
    # Setup rules repo in ws1
    ws1_rules = ws1 / "rules"
    ws1_rules.mkdir()
    run_git_cmd(["init"], ws1_rules)
    run_git_cmd(["remote", "add", "origin", str(rules_origin)], ws1_rules)
    
    # Create expand folder and some content
    expand_folder = ws1_rules / "expand"
    expand_folder.mkdir()
    (expand_folder / "config.json").write_text('{"foo": "bar"}')
    (expand_folder / "subdir").mkdir()
    (expand_folder / "subdir" / "script.py").write_text('print("hello")')
    
    # Commit and push
    run_git_cmd(["add", "."], ws1_rules)
    run_git_cmd(["commit", "-m", "Initial commit"], ws1_rules)
    run_git_cmd(["branch", "-M", "main"], ws1_rules)
    run_git_cmd(["push", "-u", "origin", "main"], ws1_rules)
    
    # Setup rules repo in ws2 (clone)
    run_git_cmd(["clone", str(rules_origin), str(ws2 / "rules")], base_dir) # clone into ws2/rules
    # Wait, clone creates the dir.
    # run_git_cmd(["clone", str(rules_origin), "rules"], ws2) # This might be easier if cwd is ws2
    
    # Let's just manually setup ws2 rules for simplicity or use clone correctly
    if (ws2 / "rules").exists():
        shutil.rmtree(ws2 / "rules")
    run_git_cmd(["clone", str(rules_origin), str(ws2 / "rules")], base_dir)

    return base_dir, ws1, ws2

def test_sync_rules_expand(temp_workspace_env):
    base_dir, ws1, ws2 = temp_workspace_env
    
    # Create config
    config = WorkspaceConfig(
        base_path=ws1, # This is technically not the base path in the sense of the CLI, but used for resolving
        repos=[RepoConfig(name="rules", path=Path("rules"))],
        rules_repo_name="rules",
        workspace_expand_folder="expand"
    )
    
    # Create a pre-existing file in ws2 that should be overwritten
    (ws2 / "config.json").write_text('{"old": "value"}')
    
    # Create a pre-existing dir in ws2 that should be overwritten
    (ws2 / "subdir").mkdir()
    (ws2 / "subdir" / "old.txt").write_text("old")

    # Change CWD to ws1 to simulate running from there
    cwd = os.getcwd()
    os.chdir(ws1)
    try:
        # We need to mock the config.base_path to match the structure expected by sync_rules
        # sync_rules expects config.base_path.parent to contain the workspaces
        # And workspaces are named {base_name}-{name}
        # Here our base_dir is the parent.
        # And our workspaces are named base-ws1, base-ws2.
        # So base_name is 'base'.
        # We need config.base_path to be something that has .parent as base_dir.
        # Let's say config.base_path is ws1.
        # But ws1 name is 'base-ws1'.
        # So config.base_path.name is 'base-ws1'.
        # The code expects `base_name` to be `config.base_path.name`.
        # Wait, the code says:
        # base_name = config.base_path.name
        # ... parent.name.startswith(f"{base_name}-")
        # If base_name is 'base-ws1', it looks for 'base-ws1-...'
        # This implies the workspaces are named 'project-ws1', 'project-ws2' where 'project' is the base name?
        # No, the CLI usually creates workspaces like 'project', 'project-feature1'.
        # The 'base' workspace is 'project'.
        # So if we are in 'project', base_name is 'project'.
        # And 'project-feature1' starts with 'project-'.
        
        # So in our test setup:
        # We should name workspaces 'base' and 'base-ws2'.
        # Let's rename ws1 to 'base' and ws2 to 'base-ws2'.
        
        os.chdir(cwd) # Move back first
        
        new_ws1 = base_dir / "base"
        ws1.rename(new_ws1)
        ws1 = new_ws1
        
        # Update config
        config.base_path = ws1
        
        os.chdir(ws1)
        
        # Run sync
        sync_rules(config)
        
        # Verify ws1 (current)
        assert (ws1 / "config.json").exists()
        assert (ws1 / "config.json").read_text() == '{"foo": "bar"}'
        assert (ws1 / "subdir" / "script.py").exists()
        
        # Verify ws2 (sibling)
        assert (ws2 / "config.json").exists()
        assert (ws2 / "config.json").read_text() == '{"foo": "bar"}'
        assert (ws2 / "subdir" / "script.py").exists()
        assert not (ws2 / "subdir" / "old.txt").exists()
        
    finally:
        os.chdir(cwd)
