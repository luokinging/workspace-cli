import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from workspace_cli.main import app
from workspace_cli.models import WorkspaceConfig, RepoConfig
from workspace_cli.config import save_config, load_config

runner = CliRunner()

def test_save_config(tmp_path):
    config = WorkspaceConfig(
        base_path=Path("/tmp/base"),
        repos=[RepoConfig(name="repo1", path=Path("repo1"))],
        rules_repo_name="rules"
    )
    config_path = tmp_path / "workspace.json"
    save_config(config, config_path)
    
    assert config_path.exists()
    with open(config_path) as f:
        data = json.load(f)
        assert data["base_path"] == "/tmp/base"
        assert data["repos"][0]["name"] == "repo1"
        assert data["rules_repo"] == "rules"

@patch("workspace_cli.core.workspace.create_workspace")
def test_create_command_auto_config(mock_create_workspace, tmp_path):
    # Run in a temp dir where no config exists
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, [
            "create", "test-ws", 
            "--base", "/tmp/base", 
            "--repo", "repo1", 
            "--repo", "repo2"
        ])
        
        assert result.exit_code == 0
        assert "Created config at" in result.stdout
        
        # Verify config created
        config_path = Path.cwd() / "workspace.json"
        assert config_path.exists()
        
        # Verify create_workspace called
        mock_create_workspace.assert_called_once()
        args = mock_create_workspace.call_args
        assert args[0][0] == "test-ws"
        assert isinstance(args[0][1], WorkspaceConfig)
        assert args[0][1].base_path == Path("/tmp/base").resolve()

@patch("workspace_cli.core.workspace.create_workspace")
def test_create_command_existing_config(mock_create_workspace, tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        # Create existing config
        config_path = Path.cwd() / "workspace.json"
        with open(config_path, "w") as f:
            json.dump({
                "base_path": "/tmp/base",
                "repos": [{"name": "repo1", "path": "repo1"}]
            }, f)
            
        result = runner.invoke(app, ["create", "test-ws"])
        
        assert result.exit_code == 0
        # Should NOT say "Created config at"
        assert "Created config at" not in result.stdout
        
        mock_create_workspace.assert_called_once()

def test_create_command_missing_config_and_args(tmp_path):
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(app, ["create", "test-ws"])
        assert result.exit_code == 1
        # Typer/Click runner captures all output in stdout unless mix_stderr=False is used
        # But here we just check stdout which contains everything by default in simple invoke
        assert "Config not found" in result.stdout
