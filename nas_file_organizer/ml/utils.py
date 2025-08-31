# nas_file_organizer/ml/utils.py
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
    """
    Infer a label from an archive path like /data/archive/<Label>/... .
    Returns None if it can't find a segment under archive_root.
    """
    path = os.path.normpath(path)
    archive_root = os.path.normpath(archive_root)
    if not path.startswith(archive_root):
        return None
    rel = os.path.relpath(path, archive_root)
    first = rel.split(os.sep, 1)[0]
    return first if first and first not in (".", "..") else None

def normalize_text(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^\w]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def collect_training_set(conn: sqlite3.Connection) -> Tuple[List[str], List[str], List[str]]:
    """
    Build (texts, labels, file_hashes) by joining ml_samples (predictions/text)
    with ml_labels (human-confirmed label). Falls back to inferring label from path
    if a human label is missing but path is in the archive.
    """
    rows = conn.execute("""
        SELECT s.file_hash, s.path, s.text,
               L.label AS human_label
        FROM ml_samples AS s
        LEFT JOIN ml_labels AS L ON L.file_hash = s.file_hash
        WHERE (s.text IS NOT NULL AND s.text <> '')
           OR (s.path IS NOT NULL AND s.path <> '')
        ORDER BY s.updated_at DESC, s.created_at DESC
    """).fetchall()

    texts: List[str] = []
    labels: List[str] = []
    hashes: List[str] = []

    for r in rows:
        fh  = r["file_hash"]
        txt = r["text"] or ""
        pth = r["path"] or ""

        # If we don't have text (should be rare), use filename + parent folder as a weak text signal
        if not txt:
            base = os.path.basename(pth)
            parent = os.path.basename(os.path.dirname(pth))
            txt = f"{base} {parent}"
        txt = normalize_text(txt)

        label = r["human_label"] or infer_label_from_path(pth, ARCHIVE_ROOT_DEFAULT)
        if not label:
            # Skip items the user hasn’t labeled yet and we can’t infer.
            continue

        texts.append(txt)
        labels.append(label)
        hashes.append(fh)

    return texts, labels, hashes

def upsert_model_registry(conn: sqlite3.Connection, version: str, path: str,
                          accuracy: float, macro_f1: float, notes: str = "") -> None:
    conn.execute("""
        INSERT INTO ml_models(version, path, accuracy, macro_f1, notes)
        VALUES(?,?,?,?,?)
        ON CONFLICT(version) DO UPDATE SET
          path=excluded.path, accuracy=excluded.accuracy,
          macro_f1=excluded.macro_f1, notes=excluded.notes
    """, (version, path, accuracy, macro_f1, notes))
    conn.commit()
