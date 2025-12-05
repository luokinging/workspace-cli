import pytest
import os
import logging
from unittest.mock import patch
from workspace_cli.server.app import lifespan
from fastapi import FastAPI

@pytest.mark.asyncio
async def test_debug_mode_logging(capsys):
    # Mock env var
    with patch.dict(os.environ, {"WORKSPACE_DEBUG": "1"}):
        # Mock logging config
        with patch("logging.basicConfig") as mock_basic_config, \
             patch("logging.getLogger") as mock_get_logger:
            
            app = FastAPI()
            async with lifespan(app):
                pass
            
            # Verify logging config was called
            mock_basic_config.assert_called_with(level=logging.DEBUG)
            mock_get_logger.assert_any_call("workspace_cli")
            mock_get_logger.return_value.setLevel.assert_called_with(logging.DEBUG)
            
            # Verify print output
            captured = capsys.readouterr()
            assert "DEBUG: Logging configured to DEBUG level" in captured.out
