# NAS File Organizer

Content-aware file sorter with OCR for NAS (Synology/QNAP/Docker-friendly).

## Features (MVP)
- Configurable rules in `rules.yaml`
- Keyword + regex matching
- Dynamic rename templates (`{date}`, `{year}`, `{month}`, `{original}`, etc.)
- Safe renaming on conflicts
- Dry-run mode
- CLI (`nas-organize`) for batch execution
- Logs every action to `logs/organizer.log`

---

## Milestone: First Successful Run 🎉

On **2025-08-25**, the first test invoices were sorted automatically into archive folders.  

**Demo run:**
![CLI execution](docs/screenshot_demo.png)

As shown above:
- Detected 2 invoices in the inbox
- Classified with the `invoices` rule
- Moved into archive structure `Archive/Invoices/YYYY/MM/`
- Renamed using the template `{date}_{first_keyword}_{original}`

---

## Next Steps (Phase 2)
- OCR support (Tesseract)
- Rule scoring (fuzzy match, title weighting)
- Real-time watch mode
- Docker deployment
- Simple web UI for monitoring
