import pytest
from pathlib import Path
from workspace_cli.config import find_config_root

def test_find_config_in_worktree(tmp_path):
    # Setup:
    # /root/base (contains workspace.json and .git dir)
    # /root/feature (sibling, contains .git file pointing to base)
    
    root = tmp_path / "root"
    root.mkdir()
    
    base = root / "base"
    base.mkdir()
    (base / "workspace.json").write_text("{}")
    
    # Simulate git repo in base
    git_dir = base / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("")
    
    # Simulate feature worktree
    feature = root / "feature"
    feature.mkdir()
    
    # .git file in feature pointing to base
    # Format: gitdir: /path/to/base/.git/worktrees/feature
    # We need to make sure the path is correct for the logic we will implement
    # Usually it points to .../.git/worktrees/...
    # But for finding the base, we just need to resolve it.
    
    worktree_git_dir = git_dir / "worktrees" / "feature"
    worktree_git_dir.mkdir(parents=True)
    
    (feature / ".git").write_text(f"gitdir: {worktree_git_dir.resolve()}\n")
    
    # Test finding config from feature
    # Currently this should fail (return None or find nothing)
    # After fix, it should return base/workspace.json
    
    config_path = find_config_root(feature)
    
    # Assert
    assert config_path is not None
    assert config_path.resolve() == (base / "workspace.json").resolve()
