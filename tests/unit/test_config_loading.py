import pytest
import json
from pathlib import Path
from workspace_cli.config import load_config, save_config
from workspace_cli.models import WorkspaceConfig, PreviewHooks

def test_load_config_with_preview(tmp_path):
    config_path = tmp_path / "workspace.json"
    data = {
        "base_path": str(tmp_path),
        "workspaces": {},
        "preview": ["cmd1"],
        "preview_hook": {
            "before_clear": ["hook1"],
            "after_preview": ["hook2"]
        }
    }
    config_path.write_text(json.dumps(data))
    
    config = load_config(config_path)
    
    assert config.preview == ["cmd1"]
    assert config.preview_hook.before_clear == ["hook1"]
    assert config.preview_hook.after_preview == ["hook2"]

def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "workspace.json"
    config = WorkspaceConfig(
        base_path=tmp_path,
        preview=["cmd1"],
        preview_hook=PreviewHooks(
            before_clear=["hook1"],
            after_preview=["hook2"]
        )
    )
    save_config(config, config_path)
    
    loaded = load_config(config_path)
    assert loaded.preview == ["cmd1"]
    assert loaded.preview_hook.before_clear == ["hook1"]
    assert loaded.preview_hook.after_preview == ["hook2"]
