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

## 🚧 In Progress (Phase 4)
- Trainer update to **prefer `ml_labels`** (human gold) when available
- `nas-train` CLI + weekly cron example (persist model to `/data/ml/model.pkl`)
- Evaluation on retrain: accuracy, precision/recall, confusion matrix in logs

---

## 🔜 Next Up (Phase 4 milestones)
- [ ] Create DB tables: `samples`, `labels`, `metrics`, `corrections` *(metrics pending; others exist)*
- ✅ Extract training set from archive cache (text + metadata)
- ✅ Baseline classifier: TF-IDF + Logistic Regression
- ✅ Integrate classifier into pipeline; fallback to rules when low confidence
- ✅ Add confidence threshold + modes: `RULES_ONLY`, `HYBRID`, `ML_ONLY`
- ✅ Web UI **Review** page to confirm/correct predictions; write gold labels
- [ ] `nas-train` implementation + weekly cron/example; persist `model.pkl`
- [ ] Evaluation: accuracy, precision/recall, confusion matrix in logs
- [ ] Stretch: multilingual OCR (eng + hun)
- [ ] Stretch: entity extraction (dates, totals, names)
- [ ] Stretch: sub-categories (e.g., invoices by company/client)
- [ ] Stretch: “Ruleless mode” when ML confidence is high

---

## 🧭 Decision Log
- 2025-08-31 — Register create-label route in `web.py` to avoid container code-reload issues; keep UI path **/review/labels/new**.
- 2025-08-29 — Adopt **hybrid** approach: rules = safety net; ML handles messy edge cases.
- 2025-08-25 — Introduced SQLite cache, Review folder, and structured logging.
