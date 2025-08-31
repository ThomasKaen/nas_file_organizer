from __future__ import annotations
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, Request, BackgroundTasks, Form, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os
from contextlib import asynccontextmanager

from ..core.services import OrganizerService
from ..core.models import Result, Options
from ..db.migrate import run as run_migrations
from nas_file_organizer.web.review_router import router as review_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    run_migrations()  # idempotent: CREATE IF NOT EXISTS
    yield
    # Shutdown (nothing needed)

APP_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = APP_ROOT / "rules.yaml"
LOG_PATH = APP_ROOT / "logs" / "organizer.log"
REVIEW_DIR = "_Review"
CACHE_DB = os.environ.get("CACHE_DB", "/data/cache.db")
ARCHIVE_ROOT = os.environ.get("ARCHIVE_ROOT", "/data/archive")

router = APIRouter()
app = FastAPI(title="NAS File Organizer", lifespan=lifespan)
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

# optional static folder (logo, etc.)
static_dir = APP_ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

svc = OrganizerService()

DB_PATH = Path(__file__).resolve().parents[1] / "cache.db"

app.include_router(review_router)

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

def _read_log_rows(limit: int = 300):
    """Return parsed rows from organizer.log (timestamp, level, message)."""
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()[-limit:]
    rows = []
    for ln in lines:
        ln = ln.strip()
        # Expected format from logging.basicConfig: "YYYY-MM-DD HH:MM:SS,ms LEVEL message"
        # We'll split on first two spaces to get ts, level, rest
        if not ln:
            continue
        try:
            # naive parse: split timestamp + level + message
            # e.g. "2025-08-25 21:33:03,123 INFO MOVED  src=... dst=..."
            ts_str, rest = ln.split(" ", 1)
            # join back time part if it contains comma
            # safer: take first 23 chars for ts "YYYY-MM-DD HH:MM:SS,ms"
            ts_str = ln[:23]
            lv_and_msg = ln[24:].strip()
            level, msg = lv_and_msg.split(" ", 1)
            rows.append((ts_str, level, msg))
        except Exception:
            rows.append(("", "", ln))
    return rows

def _count_files(path: Path) -> int:
    try:
        return sum(1 for p in path.rglob("*") if p.is_file())
    except Exception:
        return 0

def db():
    con = sqlite3.connect(CACHE_DB)
    con.row_factory = sqlite3.Row
    return con

def _create_label(name: str = Form(...)):
    name = name.strip().replace(" ", "_")
    (Path(ARCHIVE_ROOT) / name).mkdir(parents=True, exist_ok=True)
    return RedirectResponse(url="/review", status_code=303)

app.add_api_route(
    "/review/labels/new",
    _create_label,
    methods=["POST"],
    name="create_label",
)

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
        "inbox_count": _count_files(opts.inbox),
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
    rows = _read_log_rows(500)
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "rows": rows}
    )

def main():
    import uvicorn, os
    # host/port configurable via env later if needed
    #uvicorn.run("nas_file_organizer.adapters.web:app", host="127.0.0.1", port=8000, reload=False)
    host = os.environ.get("HOST", "0.0.0.0")  # 👈 allow Docker access
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("nas_file_organizer.adapters.web:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
