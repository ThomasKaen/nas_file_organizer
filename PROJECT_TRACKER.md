# NAS File Organizer — Project Tracker

**Updated:** 2025-08-31 (Europe/London)

Keep this short and moving: shift items between lists as work progresses. Use checkboxes for quick PRs.

---

## ✅ Done (Phase 2–4)
- SQLite text cache for OCR/extracted text (avoids reprocessing unchanged files)
- Structured logging to `logs/organizer.log` (MOVED, REVIEW, SKIP, ERROR + timestamps)
- **Review** folder for ambiguous cases
- Web UI (FastAPI + Jinja2) at `/` (default: `0.0.0.0:8000`)
- Dockerized app with volume mounts (Inbox, Archive, `cache.db`)
- Cross-device safe moves (copy+delete fallback on `EXDEV`)
- Persistent SQLite cache across Docker runs
- End-to-end flow verified via Web UI + Docker
- **Review UI**: Approve/Save per item, **Bulk assign**, and **Create new label** (POST `/review/labels/new`)
- ML predictions automatically logged into `ml_samples` and surfaced in Review

---

## ✅ Done (Phase 4)
- Trainer integrated with Review (`/review/retrain`) → saves model.pkl
- Confirm/Save moves files out of `_Review` into assigned label folder
- Robust trainer: handles single-class and few-sample datasets gracefully
- Auto-retrain scheduler: startup stale check + weekly APScheduler job
- Settings UI at `/settings/schedule` with day/hour dropdowns
- Review page button linking to schedule settings

✅ Done (Phase 5)

Metrics endpoint /api/metrics/latest and metrics card on /review

Path/env alignment for DB/model artifacts

nas-train CLI for manual/cron retraining

Retrain success toast on Review redirect

🔜 Post‑1.0 Backlog

Normalize label names (casing/plural) in data and UI

Add per‑class precision/recall/F1 table and confusion matrix (once dataset grows)

Optional: invoice entity extraction (date, total, VAT) using regex + heuristics

Optional: add updated_at column to ml_models and surface it directly

Optional: multi-language OCR settings (Tesseract packs)
---

## 🧭 Decision Log
- 2025-08-31 — Register create-label route in `web.py` to avoid container code-reload issues; keep UI path **/review/labels/new**.
- 2025-08-29 — Adopt **hybrid** approach: rules = safety net; ML handles messy edge cases.
- 2025-08-25 — Introduced SQLite cache, Review folder, and structured logging.
