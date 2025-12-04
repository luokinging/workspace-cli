from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import shutil
import logging

logger = logging.getLogger(__name__)

class SyncHandler(FileSystemEventHandler):
    def __init__(self, source: Path, target: Path, ignore_patterns: list = None):
        self.source = source
        self.target = target
        self.ignore_patterns = ignore_patterns or []

    def _sync(self, src_path: str):
        # Basic sync logic: copy file from source to target
        # TODO: Handle ignores and deletions properly
        rel_path = Path(src_path).relative_to(self.source)
        target_path = self.target / rel_path
        
        if Path(src_path).is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, target_path)
            logger.info(f"Synced {rel_path}")

    def on_modified(self, event):
        if not event.is_directory:
            self._sync(event.src_path)

    def on_created(self, event):
        self._sync(event.src_path)

    # TODO: Handle deletions and moves

class Watcher:
    def __init__(self, source: Path, target: Path):
        self.source = source
        self.target = target
        self.observer = Observer()
        self.handler = SyncHandler(source, target)

    def start(self):
        self.observer.schedule(self.handler, str(self.source), recursive=True)
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()
