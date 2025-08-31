# Changelog

All notable changes to **NAS File Organizer** will be documented here.

## [0.4.1] - 2025-08-31
### Added
- **Review UI** to confirm/correct ML predictions from `ml_samples`, including:
- Per-row Approve/Save actions
- **Bulk assign** selected files to a label (optional “move files”)
- **Create New Label** (POST `/review/labels/new`) — makes archive folder and returns to Review
- Automatic logging of ML predictions to `ml_samples` during planning (so review has data).

### Changed
- Review page styled with Tailwind; added header Back button.
- Safer form structure (no nested forms) + “Select all” with selected count.

### Fixed
- Routing mismatch causing 404 on label creation: hot-patched **POST `/review/labels/new`** in `web.py` to ensure the endpoint is registered even if router code isn’t reloaded inside the container.
- Ensured `_Review` and subfolders appear via recursive listing for dashboard widgets (where used).

### Notes
- Next: trainer to **prefer human gold** from `ml_labels` over folder-derived labels during retraining; add evaluation metrics after training.

## [0.4.0] - 2025-08-30
### Added
- Initial ML integration on top of rules engine (Phase 4 start).
- Training script updated to work recursively on `/data/archive/**` (subfolders included).
- Model artifacts now saved under `/data/ml/model.pkl` (persisted via Docker volume).
- Environment variables support HYBRID mode (`ML_MODE`, `ML_THRESHOLD`).

### Changed
- `services.py` extended with `ml_predict()` + `decide()` for hybrid classification:
- Rules remain the primary safety net.
- ML is consulted when rules don’t match or when scores are ambiguous.
- Low-confidence results are routed to `_Review`.

### Notes
- Current demo model trained on ~14 samples (CVs vs Invoices).
- Accuracy metrics not meaningful yet due to limited dataset, but the end-to-end loop is live.
- Next: expand dataset, integrate feedback from `/review` into retraining.

## [0.3.0] - 2025-08-29
### Added
- **Web UI** (FastAPI + Jinja2) → run with `nas-web` at [http://localhost:8000](http://localhost:8000).
- **Docker support** with volume mounts for Inbox/Archive/cache.
- **Cross-device safe moves**: fallback to copy+delete when `os.rename` fails (EXDEV).
- **Persistent cache.db**: mounted into `/data/cache.db` for stable SQLite across runs.


## [0.2.0] - 2025-08-25
### Added
- **SQLite text cache**: extracted/OCR’d text is cached in `cache.db` for faster re-runs.
- **Improved logging**: `logs/organizer.log` now records `MOVED`, `REVIEW`, `SKIP`, and `ERROR` with timestamps.
- **Review folder**: ambiguous matches are moved to `_Review/YYYY-MM-DD` for later inspection.

## [0.1.0] - 2025-08-25
### Added
- Initial MVP:
- Rule-based file classification via `rules.yaml`.
- OCR support using Tesseract.
- CLI command `nas-organize`.
- Basic watcher mode (`nas-watch`).
