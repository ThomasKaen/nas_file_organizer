-- ML-compatible tables; idempotent (CREATE IF NOT EXISTS).


CREATE TABLE IF NOT EXISTS ml_labels (
id INTEGER PRIMARY KEY,
file_hash TEXT NOT NULL,
label TEXT NOT NULL,
source TEXT NOT NULL DEFAULT 'human', -- 'human' or 'derived'
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ml_labels_filehash ON ml_labels(file_hash);


CREATE TABLE IF NOT EXISTS ml_samples (
id INTEGER PRIMARY KEY,
file_hash TEXT NOT NULL,
path TEXT,
text TEXT,
predicted_label TEXT,
confidence REAL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ml_samples_pred ON ml_samples(predicted_label);


CREATE TABLE IF NOT EXISTS ml_corrections (
id INTEGER PRIMARY KEY,
file_hash TEXT NOT NULL,
predicted_label TEXT,
corrected_label TEXT NOT NULL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS ml_models (
id INTEGER PRIMARY KEY,
version TEXT NOT NULL,
path TEXT NOT NULL,
trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
accuracy REAL,
macro_f1 REAL,
notes TEXT
);


-- Optional metrics table for runs
CREATE TABLE IF NOT EXISTS ml_metrics (
id INTEGER PRIMARY KEY,
model_version TEXT,
metric TEXT,
value REAL,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);