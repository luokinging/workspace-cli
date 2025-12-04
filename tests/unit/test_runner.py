import pytest
from unittest.mock import MagicMock, patch, call, ANY
from pathlib import Path
from workspace_cli.core.runner import PreviewRunner
from workspace_cli.models import WorkspaceConfig, PreviewHooks

@pytest.fixture
def mock_config(tmp_path):
    config = WorkspaceConfig(
        base_path=tmp_path,
        preview=["run_server"],
        preview_hook=PreviewHooks(
            before_clear=["hook_before"],
            after_preview=["hook_after"]
        )
    )
    return config

@patch("workspace_cli.core.runner.socket")
@patch("workspace_cli.core.runner.threading")
def test_runner_init(mock_threading, mock_socket, mock_config):
    runner = PreviewRunner(mock_config)
    assert runner.config == mock_config
    assert runner.port_file == mock_config.base_path / ".run_preview.port"

@patch("workspace_cli.core.runner.socket")
def test_setup_socket(mock_socket, mock_config):
    runner = PreviewRunner(mock_config)
    mock_sock_instance = MagicMock()
    mock_socket.socket.return_value = mock_sock_instance
    mock_sock_instance.getsockname.return_value = ("127.0.0.1", 12345)
    
    runner._setup_socket()
    
    mock_sock_instance.bind.assert_called_with(('127.0.0.1', 0))
    mock_sock_instance.listen.assert_called_with(1)
    assert runner.port_file.read_text() == "12345"

@patch("workspace_cli.core.runner.subprocess.Popen")
def test_run_command(mock_popen, mock_config):
    runner = PreviewRunner(mock_config)
    mock_process = MagicMock()
    mock_process.stdout = ["output line"]
    mock_process.poll.return_value = 0
    mock_popen.return_value = mock_process
    
    runner._run_command("echo test", "Test", "white")
    
    mock_popen.assert_called_with(
        "echo test",
        shell=True,
        cwd=mock_config.base_path,
        stdout=-1,
        stderr=-2,
        text=True,
        bufsize=1,
        preexec_fn=ANY
    )

@patch("workspace_cli.core.runner.sync_core.rebuild_preview")
@patch("workspace_cli.core.runner.PreviewRunner._run_command")
@patch("workspace_cli.core.runner.PreviewRunner._stop_processes")
def test_restart_lifecycle(mock_stop, mock_run, mock_rebuild, mock_config):
    runner = PreviewRunner(mock_config)
    
    # Mock execute_parallel to just call run_command sequentially for simplicity in test
    # Or we can rely on the real _execute_parallel which spawns threads.
    # Let's mock _execute_parallel to avoid threading issues in unit test
    with patch.object(runner, '_execute_parallel') as mock_parallel:
        runner._restart_lifecycle("feature-a")
        
        mock_stop.assert_called()
        assert runner.current_workspace == "feature-a"
        
        # Verify hooks called
        mock_parallel.assert_any_call(["hook_before"], "BeforeClear", ANY)
        
        # Verify sync called
        mock_rebuild.assert_called_with("feature-a", mock_config)
        
        # Verify preview commands started (these are started in threads in the real code)
        # In _restart_lifecycle, we manually spawn threads for preview/after_preview
        # We can't easily assert on threads starting without mocking threading.Thread
        
@patch("workspace_cli.core.runner.threading.Thread")
@patch("workspace_cli.core.runner.sync_core.rebuild_preview")
@patch("workspace_cli.core.runner.PreviewRunner._stop_processes")
@patch("workspace_cli.core.runner.PreviewRunner._execute_parallel")
def test_restart_lifecycle_threads(mock_parallel, mock_stop, mock_rebuild, mock_thread, mock_config):
    runner = PreviewRunner(mock_config)
    runner._restart_lifecycle("feature-a")
    
    # Check that threads were started for preview and after_preview
    # preview=["run_server"], after_preview=["hook_after"]
    assert mock_thread.call_count >= 2 
