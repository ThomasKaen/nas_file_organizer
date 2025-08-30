# NAS File Organizer — Project Tracker

**Updated:** 2025-08-29 (Europe/London)

Keep this short and moving: shift items between lists as work progresses. Use checkboxes for quick PRs.

---

## ✅ Done (Phase 2–3)
- SQLite text cache for OCR/extracted text (avoids reprocessing unchanged files)
- Structured logging to `logs/organizer.log` (MOVED, REVIEW, SKIP, ERROR + timestamps)
- **Review** folder for ambiguous cases
- Web UI (FastAPI + Jinja2) at `/` (default: `0.0.0.0:8000`)
- Dockerized app with volume mounts (Inbox, Archive, `cache.db`)
- Cross-device safe moves (copy+delete fallback on `EXDEV`)
- Persistent SQLite cache across Docker runs
- End‑to‑end flow verified via Web UI + Docker

---

## 🚧 In Progress (Phase 4 scaffolding)
- ML layer design (scikit‑learn / spaCy) — features: text, structure, metadata
- Web UI **Review** tab spec + DB schema for corrections
- `nas-train` CLI spec (weekly/on‑demand retrain) → outputs `model.pkl` in `/data`
- Replay pipeline design — capture high‑confidence samples in SQLite for training

---

## 🔜 Next Up (Phase 4 milestones)
- [ ] Create DB tables: `samples`, `labels`, `metrics`, `corrections`
- ✅ Extract training set from archive cache (text + metadata)
- ✅ Baseline classifier: TF-IDF + Logistic Regression
- ✅ Integrate classifier into pipeline; fallback to rules when low confidence
- ✅ Add confidence threshold + modes: `RULES_ONLY`, `HYBRID`, `ML_ONLY`
- [ ] Web UI **Review** page to confirm/correct predictions; write gold labels
- [ ] `nas-train` implementation + weekly cron/example; persist `model.pkl`
- [ ] Evaluation: accuracy, precision/recall, confusion matrix in logs
- [ ] Stretch: multilingual OCR (eng + hun)
- [ ] Stretch: entity extraction (dates, totals, names)
- [ ] Stretch: sub-categories (e.g., invoices by company/client)
- [ ] Stretch: “Ruleless mode” when ML confidence is high

---

## 🧭 Decision Log
- 2025‑08‑29 — Adopt **hybrid** approach: rules = safety net; ML handles messy edge cases.
- 2025‑08‑25 — Introduced SQLite cache, Review folder, and structured logging.

---

## 🗂 Suggested location
Place this file at the repo root as `PROJECT_TRACKER.md` (or under `docs/`).
