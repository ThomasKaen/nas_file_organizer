# Changelog

All notable changes to **NAS File Organizer** will be documented here.

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
