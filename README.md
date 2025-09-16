🚀 Smart NAS File Organizer

Self-learning file management for NAS and home servers

🌍 Problem

Messy “Inbox” folders eat up hours. Invoices, contracts, and photos pile up. Rules break on edge cases, and nothing learns from your corrections.

💡 Solution

A self-learning NAS file organizer:

One-line deploy: docker compose up → runs anywhere.

Hybrid rules + ML: rules guarantee safety, ML handles edge cases.

Web dashboard: confirm/correct predictions in seconds.

Continuous learning: retrains weekly from your corrections.

OCR-ready: English by default (Tesseract installed).

📊 Impact

80–90% auto-classification after the first meaningful training set.

Human corrections become training data → accuracy climbs over time.

Plug-and-play for freelancers, SMBs, or personal NAS users.

🛠 Tech Stack

FastAPI (backend & web dashboard) · Jinja2 (templates) · Docker (deployment) SQLite (cache + learning store) · scikit-learn (ML classifier) · Python 3.13

⚡ Quickstart

Clone & run

git clone https://github.com/yourusername/nas-file-organizer.git
cd nas-file-organizer
docker compose up -d --build

Open dashboard

Visit http://localhost:8000

Drop files into /data/inbox

Classified files move to /data/archive

Train the model (CLI)

# inside the running container
docker compose exec nas-organizer nas-train
# flags (optional):
# nas-train --db /data/cache.db --out /data/model.pkl --version tfidf-logreg-v1

Review & correct

Visit /review → approve/correct predictions.

Click Retrain to learn from corrections. A toast confirms success.

Scheduling (optional)

Open /settings/schedule to set a weekly auto-retrain.

📈 Metrics Viewer

After retrain, the Review page shows:

Model version and samples seen

Accuracy and Macro‑F1

Per‑class counts (grows as you correct more files)

If no metrics exist yet, the card shows an empty state until the first retrain finishes.

🗂 Architecture

           ┌──────────┐
           │  Inbox   │
           └────┬─────┘
                │
        ┌───────▼────────┐
        │  Rules Engine  │
        └───────┬────────┘
                │
        ┌───────▼────────┐
        │ Hybrid ML/Rules│
        └───────┬────────┘
                │
        ┌───────▼──────────┐
        │   Archive Store  │
        └───────┬──────────┘
                │
        ┌───────▼──────────┐
        │ Review Dashboard │
        └──────────────────┘

🧭 Roadmap

Phase 2–4 (done): cache + web UI + Docker + hybrid ML + scheduler

Phase 5 (done): metrics viewer + /api/metrics/latest + nas-train + retrain toast

Post‑1.0: label normalization, richer per‑class metrics, optional invoice entity extraction

🛠 Developer Notes

The Docker image includes curl, wget, and sqlite3 to simplify on‑container debugging.

Ensure both trainer and web share the same data volume: ./data:/data.

Key env vars: CACHE_DB (default /data/cache.db), MODEL_OUT (default /data/model.pkl).

📜 License

This project is licensed under the Prosperity License.

✅ Free for personal, educational, and non‑commercial use.

❌ Commercial use requires a license.

See LICENSE.md for details.

📚 Documentation Map

README.md — product overview and Quickstart

CHANGELOG.md — technical history

JOURNAL.md — dev log & reflections

case_study.md — portfolio narrative and impact

📦 Latest Update (2025-09-16)

Phase 5 complete → metrics viewer, /api/metrics/latest, nas-train CLI, retrain toast

Path/env alignment and route cleanup

Ready for v1.0.0 tag