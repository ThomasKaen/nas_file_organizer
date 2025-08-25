# Changelog

All notable changes to **NAS File Organizer** will be documented here.

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
