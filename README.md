🗂️ NAS File Organizer

Smart document organizer for NAS or local file systems.
Automatically sorts PDFs, images, text, and Office files into the right folders using OCR (Tesseract) and rule-based classification.

✨ Features
✅ Phase 1 — MVP

Rule-based classification via rules.yaml.

Extract text from PDFs, images, DOCX, XLSX, TXT.

OCR support with Tesseract.

CLI command: nas-organize.

Watch mode: nas-watch.

🚀 Phase 2 — Advanced (in progress)

Scoring engine with title/body weighting.

Review folder for ambiguous matches.

SQLite cache → skips repeated OCR/extraction for unchanged files.

Structured logging → logs/organizer.log with MOVED, REVIEW, SKIP, ERROR.

Docker support → ready to run on Synology/QNAP or locally.

### ✅ Phase 3 — Web + Docker Stability
- **Web UI** (FastAPI + Jinja2) at [http://localhost:8000](http://localhost:8000)  
  → monitor inbox/archive, review logs, run executes from browser.
- **Cross-device safe moves** → copy+delete fallback for Docker volume mounts.
- **Persistent cache.db** mounted into `/data/cache.db` (avoids DB lock errors).
- **Cleaner Docker Compose** setup → maps Inbox/Archive from host.
- First end-to-end Docker test successful (Aug 2025).

➡️ Next: enhance Web dashboard (live inbox view, rule editor).
📦 Installation

Clone and install in editable mode:

git clone https://github.com/ThomasKaen/nas_file_organizer.git
cd nas_file_organizer
pip install -e .


Requires:

Python 3.13+

Tesseract OCR installed (tesseract --version to check)

⚙️ Usage
Batch mode
nas-organize -c rules.yaml --execute

Watch mode
nas-watch

Debugging (see scores)
nas-organize -c rules.yaml --trace

🌐 Web UI

Run:

nas-web


Open http://localhost:8000
.
You can trigger runs, view history, and inspect logs.

🐳 Docker

Build and run:

docker build -t nas-organizer .
docker run --rm ^
  -v ${PWD}/rules.yaml:/app/rules.yaml ^
  -v "C:\Users\User\Documents\Inbox":/data/inbox ^
  -v "C:\Users\User\Documents\Archive":/data/archive ^
  -v ${PWD}/logs:/app/logs ^
  nas-organizer


For NAS deployment, map shared folders into /data/inbox and /data/archive.

## Milestone: First Successful Run 🎉

On **2025-08-25**, the first test invoices were sorted automatically into archive folders.  

Milestone: Docker + Web UI Integration 🚀

On 2025-08-29, first end-to-end run completed fully in Docker with Web UI enabled.

**Demo run:**
![CLI execution](docs/cli_mvp_test.png)

As shown above:
- Detected 2 invoices in the inbox
- Classified with the `invoices` rule
- Moved into archive structure `Archive/Invoices/YYYY/MM/`
- Renamed using the template `{date}_{first_keyword}_{original}`
- 
📜 License

This project is licensed under the Prosperity License.

✅ Free for personal, educational, and non-commercial use.

❌ Commercial use requires a license.

See LICENSE.md
 for details.

📝 Project Status

Current phase: 2 (Advanced features done, preparing Web UI)

📝 Project Status

Current phase: 3 (Web + Docker stability)

Next step: Build extended Web dashboard (view inbox files, tweak rules).

Long-term: Multi-client profiles, DB-backed rule sets, smarter NLP classification.

⚡ Tags: python · tesseract · ocr · nas · file-automation · sqlite · docker · automation · productivity