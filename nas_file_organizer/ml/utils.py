import os
import re
import sqlite3
from typing import Iterable, List, Tuple, Optional


ARCHIVE_ROOT_DEFAULT = os.environ.get("ARCHIVE_ROOT", "/data/archive")


def connect_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def infer_label_from_path(path: str, archive_root: str = ARCHIVE_ROOT_DEFAULT) -> Optional[str]:
    try:
        rel = os.path.relpath(path, archive_root)
    except ValueError:
        return None
    parts = [p for p in rel.split(os.sep) if p and p != "."]
    if not parts:
        return None
# Label = first folder under archive root, e.g., Invoices/2025/...
    return parts[0].strip()


_CLEAN_RE = re.compile(r"\s+")


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\x00", " ")
    s = _CLEAN_RE.sub(" ", s)
    return s.strip()


def fetch_archive_samples(conn: sqlite3.Connection, archive_root: str) -> List[Tuple[str, str, str]]:
    """Return (file_hash, path, text) for items in archive."""
    cur = conn.cursor()
    rows = cur.execute("SELECT file_hash, path, text FROM text_cache WHERE path LIKE ?", (f"{archive_root}%",)).fetchall()
    out = []
    for r in rows:
        out.append((r["file_hash"], r["path"], normalize_text(r["text"])) )
    return out


def collect_training_set(conn: sqlite3.Connection, archive_root: str) -> Tuple[List[str], List[str], List[str]]:
    """Return (texts, labels, file_hashes) inferred from archive folder names.
    This treats past *rule-based* decisions as initial gold labels.
    """
    triples = fetch_archive_samples(conn, archive_root)
    texts, labels, hashes = [], [], []
    for fh, path, text in triples:
        label = infer_label_from_path(path, archive_root)
        if not label:
            continue
    # Skip empty text but allow filename tokens as weak fallback
    if not text:
        base = os.path.basename(path)
        text = os.path.splitext(base)[0].replace("_", " ").replace("-", " ")
        texts.append(text)
        labels.append(label)
        hashes.append(fh)
    return texts, labels, hashes


def upsert_model_registry(conn: sqlite3.Connection, version: str, path: str, accuracy: float, macro_f1: float, notes: str = ""):
    cur = conn.cursor()
    cur.execute(
    """
    INSERT INTO ml_models(version, path, accuracy, macro_f1, notes)
    VALUES(?,?,?,?,?)
    """,
(version, path, accuracy, macro_f1, notes)
)
    conn.commit()