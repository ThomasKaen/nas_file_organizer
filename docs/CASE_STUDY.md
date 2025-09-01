📖 Case Study — Smart NAS File Organizer
🎯 Context

This project started as a small freelance-style automation: “move files into folders.”
Through iteration it became a deployable NAS app with self-learning feedback loops — closer to a SaaS product prototype than a one-off script.

🛠 Technical Journey
Phase 2 — From Prototype to Reliable Tool

Added SQLite cache for OCR/extracted text → avoids reprocessing unchanged files.

Implemented structured logging (logs/organizer.log) for traceability.

Introduced a Review folder for ambiguous cases.

Reflection: First real use of SQLite made me appreciate databases as external memory, not just “in-script hacks.”

Phase 3 — Deployable App

Built Web UI with FastAPI + Jinja2.

Achieved Docker stability (volume mounts for Inbox, Archive, cache.db).

Solved cross-device move issue with copy+delete fallback (EXDEV).

End-to-end pipeline worked in Docker + Web UI.

Reflection: Debugging in Docker surfaced edge cases I’d never seen locally. Copy/paste wasn’t “cheating” — AI help compressed weeks into hours, but integration still required persistence.

Phase 4 — Smarter & Self-Learning (completed)

Integrated ML classifier (scikit-learn) alongside rules.

Implemented closed feedback loop: review page corrections feed into training data.

Retrain button wired to trainer; model (`model.pkl`) saved and loaded in HYBRID mode.

Added background scheduler:
- Retrains on startup if model is stale (>7 days).
- Weekly retrain job (user can set day/hour via `/settings/schedule`).

Review confirm now moves files out of `_Review` into labeled folders and syncs DB paths.

Reflection: The hybrid design matters — rules remain as safety net, ML handles messy real-world edge cases. Automation only counts if it frees the user from babysitting — the auto-scheduler closed that gap.

💡 Lessons Learned

Persistence beats magic: AI accelerates, but real-world bugs still need hours of grind.

Rules + ML > either alone: Rules give safety and explainability; ML brings adaptability.

Docker debugging is a teacher: real-world behavior surfaces only in realistic environments.

Automation means full loop: review → retrain → schedule. Without self-retraining, “AI” is still just a static script.

🌍 Impact & Portfolio Value

Demonstrates end-to-end ability: from script → app → product mindset.

Shows skills in Python, FastAPI, Docker, SQLite, ML integration.

Highlights ability to integrate scheduling, persistence, and UI controls.

Case study material for freelance clients, technical interviews, and portfolio presentations.

🧭 Next Steps (Phase 5)

Add polish: metrics panel after retrain (accuracy, per-class counts).

Entity extraction for invoices (dates, totals, companies).

Sub-categories and multilingual OCR.

Optional: high-confidence “ruleless mode” for performance.

✍️ Personal Reflection

This project wasn’t just about tech. It was also about proving I can take something from idea → messy prototype → polished deliverable and not stop halfway.
Whether for freelance work or WFH opportunities, it’s become a way to show reliability, persistence, and the ability to think in systems, not just code.
