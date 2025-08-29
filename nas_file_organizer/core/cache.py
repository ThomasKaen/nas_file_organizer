from __future__ import annotations
import hashlib
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("/data/cache.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS file_cache (
  key TEXT PRIMARY KEY,
  text CLOB NOT NULL,
  mtime REAL NOT NULL,
  size INTEGER NOT NULL
);
"""

def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute(SCHEMA)
    return con

def make_key(path: Path) -> str:
    st = path.stat()
    h = hashlib.sha1()
    # path influences; size+mtime detect changes
    h.update(str(path.resolve()).encode("utf-8"))
    h.update(str(st.st_size).encode("utf-8"))
    h.update(str(st.st_mtime_ns).encode("utf-8"))
    return h.hexdigest()

def get_text(path: Path) -> Optional[str]:
    key = make_key(path)
    st = path.stat()
    with _connect() as con:
        row = con.execute(
            "SELECT text, mtime, size FROM file_cache WHERE key=?",
            (key,)
        ).fetchone()
        if not row:
            return None
        text, mtime, size = row
        # defensive sanity (should always match with our key scheme)
        if abs(mtime - st.st_mtime) > 1 or size != st.st_size:
            return None
        return text

def set_text(path: Path, text: str) -> None:
    key = make_key(path)
    st = path.stat()
    with _connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO file_cache(key, text, mtime, size) VALUES (?, ?, ?, ?)",
            (key, text, st.st_mtime, st.st_size),
        )
