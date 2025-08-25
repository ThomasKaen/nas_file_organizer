from __future__ import annotations
import time
from pathlib import Path
from typing import Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..core.services import OrganizerService

SETTLE_SECONDS = 2.0   # wait this long after last change
STABILITY_CHECKS = 2   # require this many stable size checks (1 sec apart)

def is_file_ready(p: Path) -> bool:
    """Return True if file exists and size stops changing for STABILITY_CHECKS checks."""
    if not p.exists() or p.is_dir():
        return False
    last = -1
    for _ in range(STABILITY_CHECKS):
        try:
            sz = p.stat().st_size
        except Exception:
            return False
        if sz == last:
            continue
        last = sz
        time.sleep(1.0)
    return True

class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.last_seen: Dict[Path, float] = {}
        self.svc = OrganizerService()

    def on_created(self, event: FileSystemEvent):
        self._mark(event)

    def on_modified(self, event: FileSystemEvent):
        self._mark(event)

    def _mark(self, event: FileSystemEvent):
        if event.is_directory:
            return
        p = Path(event.src_path)
        self.last_seen[p] = time.time()

    def flush_ready(self):
        """
        Run when some files have settled. This reloads rules and executes the normal pipeline.
        We don't individually move only changed files—running execute() is simpler and robust.
        """
        if not self.last_seen:
            return

        now = time.time()
        # Pick files that have been quiet long enough AND are stable on disk
        ready = [p for p, t in list(self.last_seen.items())
                 if (now - t) >= SETTLE_SECONDS and is_file_ready(p)]

        if not ready:
            return

        # Remove them from the pending map first (avoid reprocessing loop)
        for p in ready:
            self.last_seen.pop(p, None)

        # Execute a batch pass (rules reloaded each time so edits are picked up)
        opts = self.svc.load_options(self.rules_path)
        # We execute with whatever dry_run is in rules.yaml
        for _ in self.svc.execute(opts):
            pass

def main():
    rules_path = Path("rules.yaml")
    svc = OrganizerService()
    opts = svc.load_options(rules_path)
    inbox = opts.inbox

    handler = DebouncedHandler(rules_path)
    observer = Observer()
    observer.schedule(handler, str(inbox), recursive=True)
    observer.start()
    print(f"[watch] Monitoring: {inbox} (debounce {SETTLE_SECONDS}s)")
    try:
        while True:
            handler.flush_ready()
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
