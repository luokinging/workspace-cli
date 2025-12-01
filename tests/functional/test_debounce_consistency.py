import pytest
import time
import shutil
import threading
from pathlib import Path
from workspace_cli.core.sync import Watcher

def test_debounce_consistency(tmp_path):
    # Setup directories
    source_root = tmp_path / "source"
    target_root = tmp_path / "target"
    repo_path = Path("repo")
    
    source_repo = source_root / repo_path
    target_repo = target_root / repo_path
    
    source_repo.mkdir(parents=True)
    target_repo.mkdir(parents=True)
    
    # Initialize Watcher
    watcher = Watcher(source_root, target_root, repo_path)
    # Reduce debounce interval for test speed
    watcher.debounce_interval = 0.5
    
    # Mock _is_ignored to always return False
    watcher._is_ignored = lambda p: False
    
    # Scenario 1: Rapid Create -> Modify -> Delete -> Create
    # Final state: File exists with "content 2"
    file1 = source_repo / "file1.txt"
    
    # 1. Create
    file1.write_text("content 1")
    event_create = type('Event', (), {'is_directory': False, 'src_path': str(file1)})()
    watcher.on_created(event_create)
    
    # 2. Modify (rapidly)
    file1.write_text("content 2")
    event_modify = type('Event', (), {'is_directory': False, 'src_path': str(file1)})()
    watcher.on_modified(event_modify)
    
    # Wait for debounce
    time.sleep(1.0)
    
    # Verify target
    target_file1 = target_repo / "file1.txt"
    assert target_file1.exists()
    assert target_file1.read_text() == "content 2"
    
    # Scenario 2: Rapid Create -> Delete
    # Final state: File does not exist
    file2 = source_repo / "file2.txt"
    file2.write_text("temp")
    event_create2 = type('Event', (), {'is_directory': False, 'src_path': str(file2)})()
    watcher.on_created(event_create2)
    
    file2.unlink()
    event_delete2 = type('Event', (), {'is_directory': False, 'src_path': str(file2)})()
    watcher.on_deleted(event_delete2)
    
    # Wait for debounce
    time.sleep(1.0)
    
    # Verify target
    target_file2 = target_repo / "file2.txt"
    assert not target_file2.exists()
    
    # Scenario 3: Move (Rename)
    # Final state: Old file gone, new file exists
    file3 = source_repo / "file3.txt"
    file3.write_text("content 3")
    # Initial sync (manual for setup)
    shutil.copy2(file3, target_repo / "file3.txt")
    
    file3_new = source_repo / "file3_new.txt"
    shutil.move(file3, file3_new)
    
    event_move = type('Event', (), {
        'is_directory': False, 
        'src_path': str(file3),
        'dest_path': str(file3_new)
    })()
    watcher.on_moved(event_move)
    
    # Wait for debounce
    time.sleep(1.0)
    
    # Verify target
    assert not (target_repo / "file3.txt").exists()
    assert (target_repo / "file3_new.txt").exists()
    assert (target_repo / "file3_new.txt").read_text() == "content 3"

if __name__ == "__main__":
    pytest.main([__file__])
