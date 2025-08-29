# app/db/migrate.py
import os, sqlite3, pathlib, logging

log = logging.getLogger("migrate")

DB_PATH  = os.environ.get("CACHE_DB", "/data/cache.db")
CANDIDATES = [
    os.environ.get("SCHEMA_PATH"),
    "/app/schemas/base_and_phase4.sql",
    "/app/schemas/phase4.sql",
]

FALLBACK_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS text_cache (
  file_hash   TEXT PRIMARY KEY,
  path        TEXT NOT NULL,
  text        TEXT,
  size        INTEGER,
  mtime       REAL,
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_text_cache_path ON text_cache(path);

CREATE TABLE IF NOT EXISTS ml_labels (
  file_hash   TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  source      TEXT NOT NULL DEFAULT 'human',
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ml_samples (
  file_hash       TEXT PRIMARY KEY,
  path            TEXT,
  text            TEXT,
  predicted_label TEXT,
  confidence      REAL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ml_samples_pred ON ml_samples(predicted_label);

CREATE TABLE IF NOT EXISTS ml_corrections (
  id              INTEGER PRIMARY KEY,
  file_hash       TEXT NOT NULL,
  predicted_label TEXT,
  corrected_label TEXT NOT NULL,
  created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ml_corrections_filehash ON ml_corrections(file_hash);

CREATE TABLE IF NOT EXISTS ml_models (
  id         INTEGER PRIMARY KEY,
  version    TEXT NOT NULL,
  path       TEXT NOT NULL,
  trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  accuracy   REAL,
  macro_f1   REAL,
  notes      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ml_models_version ON ml_models(version);

CREATE TABLE IF NOT EXISTS ml_metrics (
  id            INTEGER PRIMARY KEY,
  model_version TEXT,
  metric        TEXT,
  value         REAL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def run():
    sql = None
    for p in [c for c in CANDIDATES if c]:
        path = pathlib.Path(p)
        if path.exists():
            sql = path.read_text(encoding="utf-8")
            log.info(f"Running migration from {path}")
            break
    if sql is None:
        log.warning("Schema file not found; using embedded fallback SQL.")
        sql = FALLBACK_SQL

    con = sqlite3.connect(DB_PATH)
    con.executescript(sql)
    con.commit()
    con.close()
