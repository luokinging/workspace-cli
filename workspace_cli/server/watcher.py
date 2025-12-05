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
        
        if not Path(src_path).exists():
            logger.debug(f"Skipping sync for missing file: {src_path}")
            return

        if Path(src_path).is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_path, target_path)
            logger.info(f"Synced {rel_path}")

    def on_modified(self, event):
        logger.debug(f"Watcher on_modified: {event.src_path}")
        if not event.is_directory:
            self._sync(event.src_path)

    def on_created(self, event):
        logger.debug(f"Watcher on_created: {event.src_path}")
        self._sync(event.src_path)

    def on_moved(self, event):
        logger.debug(f"Watcher on_moved: {event.src_path} -> {event.dest_path}")
        if not event.is_directory:
            # If moved within source, sync the new file
            if str(event.dest_path).startswith(str(self.source)):
                self._sync(event.dest_path)
            # Also delete the old one? 
            # If it was a rename, we should delete the old target.
            # But atomic saves usually overwrite the target, so maybe just sync is enough?
            # If it's a rename of A -> B, we want B in target and A gone.
            
            # Handle deletion of source
            if str(event.src_path).startswith(str(self.source)):
                self._delete(event.src_path)

    def on_deleted(self, event):
        logger.debug(f"Watcher on_deleted: {event.src_path}")
        self._delete(event.src_path)

    def _delete(self, src_path: str):
        try:
            rel_path = Path(src_path).relative_to(self.source)
            target_path = self.target / rel_path
            if target_path.exists():
                if target_path.is_dir():
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
                logger.info(f"Deleted {rel_path}")
        except Exception as e:
            logger.error(f"Error deleting {src_path}: {e}")

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
