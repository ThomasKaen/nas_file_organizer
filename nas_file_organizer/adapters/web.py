from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3

from ..core.services import OrganizerService
from ..core.models import Result, Options

APP_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = APP_ROOT / "rules.yaml"
LOG_PATH = APP_ROOT / "logs" / "organizer.log"
REVIEW_DIR = "_Review"

app = FastAPI(title="NAS File Organizer")
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

# optional static folder (logo, etc.)
static_dir = APP_ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

svc = OrganizerService()

DB_PATH = Path(__file__).resolve().parents[1] / "cache.db"

def _load_opts() -> Options:
    return svc.load_options(RULES_PATH)

def _tail(path: Path, lines: int = 200) -> str:
    if not path.exists():
        return ""
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        data = f.readlines()
    return "".join(data[-lines:])

def _review_files(opts: Options) -> list[Path]:
    base = opts.archive_root / REVIEW_DIR
    if not base.exists():
        return []
    return sorted([p for p in base.rglob("*") if p.is_file()])

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    opts = _load_opts()
    planned: List[Result] = list(svc.plan(opts))
    to_move = [r for r in planned if r.dst and r.reason != "no_match"]
    no_match = [r for r in planned if r.reason == "no_match"]
    review_candidates = [r for r in planned if r.reason == "review"]
    logs_tail = _tail(LOG_PATH, 150)
    reviews = _review_files(opts)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "inbox": str(opts.inbox),
        "archive": str(opts.archive_root),
        "dry_run": opts.dry_run,
        "count_plan": len(planned),
        "count_move": len(to_move),
        "count_nomatch": len(no_match),
        "count_review": len(review_candidates) or len(reviews),
        "log_tail": logs_tail,
        "reviews": [str(p.relative_to(opts.archive_root)) for p in reviews][:50],
    })

@app.post("/run")
def run(background_tasks: BackgroundTasks, mode: str = Form("plan")):
    opts = _load_opts()
    if mode == "execute":
        # run execute in background to keep UI responsive
        def _do():
            for _ in svc.execute(opts):
                pass
        background_tasks.add_task(_do)
        return RedirectResponse(url="/", status_code=303)
    else:
        # plan only just refreshes dashboard
        return RedirectResponse(url="/", status_code=303)

@app.get("/api/plan")
def api_plan():
    opts = _load_opts()
    out = []
    for r in svc.plan(opts):
        out.append({
            "src": str(r.src),
            "dst": (str(r.dst) if r.dst else None),
            "rule": r.rule,
            "reason": r.reason,
            "ok": r.ok,
        })
    return JSONResponse(out)

@app.get("/logs")
def logs():
    return PlainTextResponse(_tail(LOG_PATH, 300))

@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    rows = []
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT ts, src, dst, rule, ok, reason FROM logs ORDER BY ts DESC LIMIT 100;")
        rows = cur.fetchall()
        conn.close()
    return templates.TemplateResponse("history.html", {"request": request, "rows": rows})

def main():
    import uvicorn, os
    # host/port configurable via env later if needed
    #uvicorn.run("nas_file_organizer.adapters.web:app", host="127.0.0.1", port=8000, reload=False)
    host = os.environ.get("HOST", "0.0.0.0")  # 👈 allow Docker access
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("nas_file_organizer.adapters.web:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
