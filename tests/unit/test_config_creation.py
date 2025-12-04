import pytest
from pathlib import Path
from typer.testing import CliRunner
from workspace_cli.main import app
from workspace_cli.config import load_config

runner = CliRunner()

import os
from unittest.mock import patch

@patch("workspace_cli.core.workspace.create_workspace")
def test_create_config_in_parent(mock_create, tmp_path):
    # Setup: Create base workspace directory
    base_ws = tmp_path / "base-ws"
    base_ws.mkdir()
    
    # Run create command from inside base_ws
    cwd = os.getcwd()
    os.chdir(base_ws)
    try:
        result = runner.invoke(app, ["create", "feature-a", "--base", "."])
    finally:
        os.chdir(cwd)
    
    if result.exit_code != 0:
        print(f"Output: {result.stdout}")
        print(f"Exception: {result.exception}")
    
    assert result.exit_code == 0
    
    # Check where config was created
    # Should be in parent (tmp_path), NOT in base_ws
    assert (tmp_path / "workspace.json").exists()
    assert not (base_ws / "workspace.json").exists()
    
    # Verify content
    config = load_config(tmp_path / "workspace.json")
    assert config.base_path.resolve() == base_ws.resolve()

@patch("workspace_cli.core.workspace.create_workspace")
def test_create_config_in_cwd_if_not_base(mock_create, tmp_path):
    # Setup: Create root directory
    root = tmp_path / "root"
    root.mkdir()
    base_ws = root / "base-ws"
    base_ws.mkdir()
    
    # Run create command from root
    cwd = os.getcwd()
    os.chdir(root)
    try:
        result = runner.invoke(app, ["create", "feature-a", "--base", "./base-ws"])
    finally:
        os.chdir(cwd)
    
    assert result.exit_code == 0
    
    # Check where config was created
    # Should be in root (CWD)
    assert (root / "workspace.json").exists()
    
    # Verify content
    config = load_config(root / "workspace.json")
    assert config.base_path.resolve() == base_ws.resolve()
