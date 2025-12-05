import pytest
import time
from pathlib import Path
from workspace_cli.server.watcher import Watcher

import logging

def test_watcher_debug(tmp_path, caplog):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    
    caplog.set_level(logging.DEBUG)
    
    watcher = Watcher(source, target)
    watcher.start()
    
    try:
        # Create a file in source
        (source / "test.txt").write_text("hello")
        
        # Wait for watcher
        time.sleep(1)
        
        # Check target
        assert (target / "test.txt").exists()
        assert (target / "test.txt").read_text() == "hello"
        
        # Check logs
        assert "Watcher on_created" in caplog.text or "Watcher on_modified" in caplog.text
        caplog.clear()
        
        # Modify file
        (source / "test.txt").write_text("world")
        time.sleep(1)
        
        assert (target / "test.txt").read_text() == "world"
        
        assert "Watcher on_modified" in caplog.text
        caplog.clear()
        
        # Test Move (Rename)
        (source / "test.txt").rename(source / "moved.txt")
        time.sleep(1)
        
        assert not (target / "test.txt").exists()
        assert (target / "moved.txt").exists()
        assert (target / "moved.txt").read_text() == "world"
        
        assert "Watcher on_moved" in caplog.text
        caplog.clear()
        
        # Test Delete
        (source / "moved.txt").unlink()
        time.sleep(1)
        
        assert not (target / "moved.txt").exists()
        
        assert "Watcher on_deleted" in caplog.text
        
    finally:
        watcher.stop()
