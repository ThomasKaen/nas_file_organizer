# nas_file_organizer/web/metrics.py
from __future__ import annotations
import os, json, sqlite3

def _cache_db() -> str:
    # Use the same env var as the app
    return os.environ.get("CACHE_DB", "/data/cache.db")

def _q(db, sql, args=()):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, args)
        row = cur.fetchone()
        return dict(row) if row else {}
    finally:
        con.close()

def per_class_counts():
    """
    Counts of labeled samples per class from gold labels.
    """
    db = _cache_db()
    try:
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT label, COUNT(*) AS n FROM ml_labels GROUP BY label ORDER BY n DESC"
        ).fetchall()
        con.close()
        return [(r["label"], r["n"]) for r in rows]
    except Exception:
        return []

def latest_metrics():
    db = _cache_db()
    # Use rowid as recency; generate ISO timestamp from SQLite 'now'
    m = _q(db, """
        SELECT
          version,
          path,
          accuracy,
          macro_f1,
          notes,
          strftime('%Y-%m-%dT%H:%M:%SZ', 'now') AS updated_at
        FROM ml_models
        ORDER BY rowid DESC
        LIMIT 1
    """)
    if not m:
        return {}

    # optional per-class counts (safe even if table is empty)
    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    try:
        rows = con.execute("""
            SELECT label, COUNT(*) AS n
            FROM ml_labels
            GROUP BY label
            ORDER BY n DESC
        """).fetchall()
        m["per_class_counts"] = [(r["label"], r["n"]) for r in rows]
    finally:
        con.close()
    return m


