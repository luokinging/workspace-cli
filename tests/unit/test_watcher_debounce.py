import pytest
import time
from unittest.mock import MagicMock, patch
from pathlib import Path
from workspace_cli.core.sync import Watcher

def test_debounced_watcher():
    # Setup
    source_root = Path("/tmp/source")
    target_root = Path("/tmp/target")
    repo_path = Path("repo")
    
    watcher = Watcher(source_root, target_root, repo_path)
    
    # Mock _sync_file to avoid actual file ops
    watcher._sync_file = MagicMock()
    
    # Mock _is_ignored
    watcher._is_ignored = MagicMock(return_value=False)
    
    # Simulate events
    event1 = MagicMock()
    event1.is_directory = False
    event1.src_path = "/tmp/source/repo/file1.txt"
    
    event2 = MagicMock()
    event2.is_directory = False
    event2.src_path = "/tmp/source/repo/file2.txt"
    
    # 1. Trigger event 1
    watcher.on_modified(event1)
    
    # Verify not synced immediately
    watcher._sync_file.assert_not_called()
    
    # 2. Trigger event 2 (within debounce interval)
    time.sleep(0.1)
    watcher.on_modified(event2)
    
    # Verify still not synced
    watcher._sync_file.assert_not_called()
    
    # 3. Wait for debounce interval (1.0s + buffer)
    time.sleep(1.2)
    
    # Verify synced
    assert watcher._sync_file.call_count == 2
    # Order is not guaranteed due to set, but both should be called
    calls = [call.args[0] for call in watcher._sync_file.call_args_list]
    assert "/tmp/source/repo/file1.txt" in calls
    assert "/tmp/source/repo/file2.txt" in calls
    
    # Verify event_type="BATCH"
    watcher._sync_file.assert_any_call("/tmp/source/repo/file1.txt", event_type="BATCH")

def test_debounced_watcher_reset_timer():
    # Setup
    source_root = Path("/tmp/source")
    target_root = Path("/tmp/target")
    repo_path = Path("repo")
    
    watcher = Watcher(source_root, target_root, repo_path)
    watcher._sync_file = MagicMock()
    watcher._is_ignored = MagicMock(return_value=False)
    
    event = MagicMock()
    event.is_directory = False
    event.src_path = "/tmp/source/repo/file1.txt"
    
    # 1. Trigger event
    watcher.on_modified(event)
    
    # 2. Wait 0.6s (less than 1s)
    time.sleep(0.6)
    watcher._sync_file.assert_not_called()
    
    # 3. Trigger event again (should reset timer)
    watcher.on_modified(event)
    
    # 4. Wait 0.6s (total 1.2s from start, but only 0.6s from last event)
    time.sleep(0.6)
    watcher._sync_file.assert_not_called()
    
    # 5. Wait another 0.6s (total 1.2s from last event)
    time.sleep(0.6)
    watcher._sync_file.assert_called_once()
