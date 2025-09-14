# nas_file_organizer/adapters/web.py
from __future__ import annotations
from pathlib import Path
from typing import List
from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3, os, datetime, json

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager

from ..core.services import OrganizerService
from ..core.models import Result, Options
from ..db.migrate import run as run_migrations
from nas_file_organizer.web.review_router import router as review_router
from nas_file_organizer.ml.train import train_and_save

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    run_migrations()  # idempotent
    yield
    # Shutdown: nothing needed

# ===== Env / paths =====
APP_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = APP_ROOT / "rules.yaml"
LOG_PATH = APP_ROOT / "logs" / "organizer.log"
REVIEW_DIR = "_Review"
CACHE_DB = os.environ.get("CACHE_DB", "/data/cache.db")
ARCHIVE_ROOT = os.environ.get("ARCHIVE_ROOT", "/data/archive")
MODEL_OUT = os.environ.get("MODEL_OUT", "/data/model.pkl")
MODEL_VER = os.environ.get("MODEL_VERSION", "tfidf-logreg-v1")

app = FastAPI(title="NAS File Organizer", lifespan=lifespan)
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

# Static
static_dir = APP_ROOT / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Services
svc = OrganizerService()

# Include existing review router
app.include_router(review_router)

# ===== Scheduler (define ONCE, before installing jobs) =====
SCHED_TZ = os.environ.get("SCHED_TZ", "UTC")
scheduler = BackgroundScheduler(timezone=SCHED_TZ)
JOB_ID = "weekly_retrain"

# ===== Helpers =====
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
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()[-limit:]
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
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

# ---- Simple app settings (persist in CACHE_DB) ----
def _ensure_settings_table():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL
            )
        """)
        con.commit()

def _get_setting(key: str, default: str) -> str:
    _ensure_settings_table()
    with db() as con:
        row = con.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

def _set_setting(key: str, value: str):
    _ensure_settings_table()
    with db() as con:
        con.execute("""
            INSERT INTO app_settings(key, value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))
        con.commit()

DEFAULT_DAY = "mon"   # mon,tue,wed,thu,fri,sat,sun
DEFAULT_HOUR = "3"    # 0..23

def _get_schedule():
    day  = _get_setting("retrain_day", DEFAULT_DAY)
    hour = _get_setting("retrain_hour", DEFAULT_HOUR)
    return day, hour

def _set_schedule(day: str, hour: str):
    _set_setting("retrain_day", day)
    _set_setting("retrain_hour", hour)

def _needs_retrain(db_path: str, days: int = 7) -> bool:
    if not os.path.exists(db_path):
        return True
    try:
        con = sqlite3.connect(db_path)
        row = con.execute("SELECT MAX(created_at) FROM ml_models").fetchone()
        con.close()
        if not row or not row[0]:
            return True
        last = datetime.datetime.fromisoformat(row[0])
        return (datetime.datetime.utcnow() - last).days >= days
    except Exception:
        return True

def _do_retrain():
    try:
        res = train_and_save(CACHE_DB, MODEL_OUT, MODEL_VER)
        print(f"[AutoRetrain] Model retrained ({res['samples']} samples, acc={res['accuracy']:.3f})")
    except Exception as e:
        print("[AutoRetrain] Retrain failed:", e)

def _install_weekly_job():
    # Remove existing job (if any), then add a new one using current settings
    try:
        scheduler.remove_job(JOB_ID)
    except Exception:
        pass
    day, hour = _get_schedule()
    # sanitize inputs
    valid_days = {"mon","tue","wed","thu","fri","sat","sun"}
    if day not in valid_days:
        day = DEFAULT_DAY
    try:
        h = int(hour)
        if not (0 <= h <= 23):
            h = int(DEFAULT_HOUR)
    except Exception:
        h = int(DEFAULT_HOUR)
    trigger = CronTrigger(day_of_week=day, hour=h, minute=0)
    scheduler.add_job(_do_retrain, trigger=trigger, id=JOB_ID)
    print(f"[AutoRetrain] Scheduled weekly retrain: {day} {h:02d}:00 ({SCHED_TZ})")

# ===== Routes (all local ones via app.add_api_route) =====

# Create new top-level label folder
def _create_label(name: str = Form(...)):
    name = name.strip().replace(" ", "_")
    (Path(ARCHIVE_ROOT) / name).mkdir(parents=True, exist_ok=True)
    return RedirectResponse(url="/review", status_code=303)

app.add_api_route("/review/labels/new", _create_label, methods=["POST"], name="create_label")

# Manual retrain (button on review page)
def _retrain():
    train_and_save(CACHE_DB, MODEL_OUT, MODEL_VER)
    return RedirectResponse(url="/review", status_code=303)

app.add_api_route("/review/retrain", _retrain, methods=["POST"], name="retrain_model")
app.add_api_route("/review/retrain", _retrain, methods=["GET"],  name="retrain_model_get")

def _latest_metrics():
    """
    Read the most recent model registry entry.
    Tries `ml_models` (our usual) and falls back to `model_registry` if your utils use a different table.
    """
    tables_to_try = [
        ("ml_models", """
           SELECT version, path, accuracy, macro_f1, samples, classes, notes, created_at
             FROM ml_models
            ORDER BY COALESCE(datetime(created_at), datetime('now')) DESC, id DESC
            LIMIT 1
        """),
        ("model_registry", """
           SELECT version, path, accuracy, macro_f1, samples, classes, notes, created_at
             FROM model_registry
            ORDER BY COALESCE(datetime(created_at), datetime('now')) DESC, id DESC
            LIMIT 1
        """),
    ]
    con = sqlite3.connect(CACHE_DB)
    con.row_factory = sqlite3.Row
    for _, sql in tables_to_try:
        try:
            row = con.execute(sql).fetchone()
            if row:
                return {
                    "version": row["version"],
                    "path": row["path"],
                    "accuracy": row["accuracy"],
                    "macro_f1": row["macro_f1"],
                    "samples": row["samples"] if "samples" in row.keys() else None,
                    "classes": json.loads(row["classes"]) if (row.get("classes")) else [],
                    "notes": row["notes"] if "notes" in row.keys() else None,
                    "created_at": row["created_at"] if "created_at" in row.keys() else None,
                }
        except Exception:
            continue
    return None

def _per_class_counts():
    """
    Quick counts from gold labels for a tiny class summary.
    """
    try:
        con = sqlite3.connect(CACHE_DB)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT label, COUNT(*) AS n FROM ml_labels GROUP BY label ORDER BY n DESC").fetchall()
        return [(r["label"], r["n"]) for r in rows]
    except Exception:
        return []

# Home/dashboard
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

# Run plan/execute from UI
@app.post("/run")
def run(background_tasks: BackgroundTasks, mode: str = Form("plan")):
    opts = _load_opts()
    if mode == "execute":
        def _do():
            for _ in svc.execute(opts):
                pass
        background_tasks.add_task(_do)
        return RedirectResponse(url="/", status_code=303)
    else:
        return RedirectResponse(url="/", status_code=303)

# API: plan JSON
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

# Logs & History
@app.get("/logs")
def logs():
    return PlainTextResponse(_tail(LOG_PATH, 300))

@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    rows = _read_log_rows(500)
    return templates.TemplateResponse("history.html", {"request": request, "rows": rows})

# Settings: schedule (GET page + POST save)
def _schedule_page(request: Request):
    day, hour = _get_schedule()
    return templates.TemplateResponse("settings_schedule.html", {
        "request": request,
        "day": day,
        "hour": hour,
        "days": ["mon","tue","wed","thu","fri","sat","sun"],
        "hours": [str(i) for i in range(24)]
    })

def _schedule_save(day: str = Form(...), hour: str = Form(...)):
    _set_schedule(day.strip().lower(), hour.strip())
    _install_weekly_job()
    return RedirectResponse(url="/settings/schedule", status_code=303)

app.add_api_route("/settings/schedule", _schedule_page, methods=["GET"],  response_class=HTMLResponse, name="schedule_page")
app.add_api_route("/settings/schedule", _schedule_save, methods=["POST"], name="schedule_save")

@app.get("/api/metrics/latest")
def api_metrics_latest():
    m = _latest_metrics()
    return JSONResponse(m or {})

# ===== Startup actions =====
if _needs_retrain(CACHE_DB, 7):
    print("[AutoRetrain] Model is stale or missing → retraining now...")
    _do_retrain()

scheduler.start()
_install_weekly_job()

def main():
    import uvicorn
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("nas_file_organizer.adapters.web:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    main()
