# Development Journal — NAS File Organizer

## 2025-08-25
- Personal note: 12-hour dev sprint, MVP → cache+logs, completed on 25/08/2025 @ 22:17

- Implemented **SQLite cache** for text extraction.
  - Motivation: avoid repeated OCR (slow).
  - Chose SQLite because it’s lightweight, file-based, and requires no server.
  - Future: could also store **rulesets** per client in DB for multi-profile support.

- Updated **logging** system.
  - Added categories: `MOVED`, `REVIEW`, `SKIP`, `ERROR`.
  - Review moves are treated like normal moves but flagged for user inspection.
  - Logs go to `logs/organizer.log`.

- Reflections:
  - Considering moving **rules** into the DB later for multi-client setups.
  - Docker integration tested locally — containerized version is on the roadmap.
  - Real-time watcher still experimental, but works for demos.

## 2025-08-25
- MVP finished: OCR with Tesseract, rules.yaml parsing, classification + execution.
- First working run with invoices recognized.
- Next steps identified: caching, logging, review handling, Docker.