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

Phase 4 — Smarter & Self-Learning (in progress)

Added ML classifier (scikit-learn) on top of rules.

Designed feedback loop: review page corrections become training data.

Background retrainer (nas-train) saves updated models (model.pkl).

Planned stretch goals: multilingual OCR, invoice entity extraction, sub-categories, high-confidence “ruleless mode.”

Reflection: The hybrid design matters — rules remain as safety net, ML handles messy real-world edge cases.

💡 Lessons Learned

Persistence beats magic: AI accelerates, but real-world bugs still need hours of grind.

Rules + ML > either alone: Rules give safety and explainability; ML brings adaptability.

Docker debugging is a teacher: real-world behavior surfaces only in realistic environments.

It’s a product, not a script: small freelance-style utilities can evolve into portfolio-level products.

🌍 Impact & Portfolio Value

Demonstrates end-to-end ability: from script → app → product mindset.

Shows skills in Python, FastAPI, Docker, SQLite, ML integration.

Case study material for freelance clients, technical interviews, and portfolio presentations.

🧭 Next Steps

Ship Phase 4 fully (hybrid ML in production, feedback loop live).

Add polish: dropdown labels in review page, entity extraction for invoices.

Capture metrics: auto-classification % and accuracy improvements after retrain.

Document real-world performance as a follow-up case study.

✍️ Personal Reflection

This project wasn’t just about tech. It was also about proving I can take something from idea → messy prototype → polished deliverable and not stop halfway.
Whether for freelance work or WFH opportunities, it’s become a way to show reliability, persistence, and the ability to think in systems, not just code.