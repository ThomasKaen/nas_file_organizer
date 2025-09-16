# nas_file_organizer/web/review_router.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from nas_file_organizer.ml.train import train_and_save
import os, sqlite3, shutil, hashlib, datetime
from nas_file_organizer.web.metrics import latest_metrics, per_class_counts


APP_ROOT = Path(__file__).resolve().parents[2]
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))
_last_metrics = {}
router = APIRouter(prefix="/review", tags=["review"])

CACHE_DB     = os.environ.get("CACHE_DB", "/data/cache.db")
ARCHIVE_ROOT = os.environ.get("ARCHIVE_ROOT", "/data/archive")
MODEL_OUT = os.environ.get("MODEL_OUT", "/data/model.pkl")


def db():
    con = sqlite3.connect(CACHE_DB)
    con.row_factory = sqlite3.Row
    return con

def _labels():
    root = Path(ARCHIVE_ROOT)
    return sorted([p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")]) if root.exists() else []

def _unique_target(dst_dir: Path, filename: str) -> Path:
    """Avoid overwrite if a same-named file already exists in the target folder."""
    base = Path(filename).stem
    ext  = Path(filename).suffix
    dst  = dst_dir / filename
    i = 1
    while dst.exists():
        dst = dst_dir / f"{base}({i}){ext}"
        i += 1
    return dst

@router.get("", response_class=HTMLResponse, name="review_page")  # -> GET /review
def review_page(request: Request, only_pending: int = 1):
    sql = """
      SELECT s.file_hash, s.path, s.text, s.predicted_label, s.confidence,
             (SELECT label FROM ml_labels WHERE file_hash = s.file_hash) AS gold_label
      FROM ml_samples AS s
      ORDER BY s.created_at DESC LIMIT 100
    """
    with db() as con:
        rows = con.execute(sql).fetchall()
    if only_pending:
        rows = [r for r in rows if r["gold_label"] is None]
    return templates.TemplateResponse("review.html", {
        "request": request,
        "rows": rows,
        "labels": _labels(),
        "archive_root": ARCHIVE_ROOT,
        "metrics": latest_metrics(),
        "class_counts": per_class_counts(),
    })

@router.post("/submit", name="review_confirm")
def review_confirm(event_id: int = Form(...), label: str = Form(...), path: str = Form(...)):
    """
    - Mark event as reviewed with chosen label
    - MOVE the actual file from Review -> <label>
    - Update all DB tables that store the file path
    """
    src = Path(path)
    # If path is missing or stale, try to recover the current path from text_cache by hash
    if not src.exists():
        file_hash = hashlib.sha256(path.encode("utf-8")).hexdigest()
        with db() as con:
            row = con.execute("SELECT path FROM text_cache WHERE file_hash=?", (file_hash,)).fetchone()
            if row and row["path"]:
                src = Path(row["path"])

    # Prepare destination
    dst_dir = Path(ARCHIVE_ROOT) / label
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = _unique_target(dst_dir, src.name) if src.exists() else dst_dir / Path(path).name

    # Do the DB updates + move
    with db() as con:
        # mark reviewed + chosen label on the file_events row
        con.execute("UPDATE file_events SET final_label=?, reviewed=1 WHERE id=?", (label, event_id))

        # ensure ml_labels has a human label
        file_hash = hashlib.sha256(str(src).encode("utf-8")).hexdigest()
        con.execute("""
          INSERT INTO ml_labels(file_hash,label,source,created_at)
          VALUES(?,?,'human',?)
          ON CONFLICT(file_hash) DO UPDATE SET label=excluded.label
        """, (file_hash, label, datetime.datetime.utcnow().isoformat()))

        con.commit()

    # Try to move the file (best effort). shutil.move handles cross-device moves.
    if src.exists() and src.is_file():
        try:
            dst = _unique_target(dst_dir, src.name)  # recompute in case of race
            shutil.move(str(src), str(dst))
            new_path = str(dst)
        except Exception as e:
            # If move fails, keep the old path; you can log e if you want.
            new_path = str(src)
    else:
        # File not found on disk; keep the original path
        new_path = str(src)

    # Reflect the new path everywhere we cache it
    with db() as con:
        con.execute("UPDATE text_cache SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                    (new_path, file_hash))
        con.execute("UPDATE ml_samples SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                    (new_path, file_hash))
        con.execute("UPDATE file_events SET moved_to=? WHERE id=?", (new_path, event_id))
        con.commit()

    return RedirectResponse(url="/review", status_code=303)

@router.post("/bulk", name="review_bulk_assign")  # -> POST /review/bulk
def review_bulk_assign(
    file_hash: list[str] = Form([]),
    corrected_label: str = Form(...),
    move_file: int = Form(1),
):
    if not file_hash:
        return RedirectResponse("/review", status_code=303)

    import shutil
    from pathlib import Path as P
    with db() as con:
        qmarks = ",".join("?" * len(file_hash))
        rows = con.execute(f"SELECT file_hash, path, predicted_label FROM ml_samples WHERE file_hash IN ({qmarks})", file_hash).fetchall()
        con.executemany("""
          INSERT INTO ml_labels(file_hash,label,source,created_at)
          VALUES(?,?,'human',CURRENT_TIMESTAMP)
          ON CONFLICT(file_hash) DO UPDATE SET label=excluded.label
        """, [(r["file_hash"], corrected_label) for r in rows])
        con.executemany("""
          INSERT INTO ml_corrections(file_hash,predicted_label,corrected_label,created_at)
          VALUES(?,?,?,CURRENT_TIMESTAMP)
        """, [(r["file_hash"], r["predicted_label"], corrected_label)
              for r in rows if r["predicted_label"] and r["predicted_label"] != corrected_label])
        con.commit()

    if move_file:
        dst_dir = Path(ARCHIVE_ROOT) / corrected_label
        dst_dir.mkdir(parents=True, exist_ok=True)
        with db() as con:
            for r in rows:
                try:
                    src = P(r["path"])
                    if not src.exists():
                        continue
                    dst = dst_dir / src.name
                    shutil.move(str(src), str(dst))
                    con.execute("UPDATE text_cache SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), r["file_hash"]))
                    con.execute("UPDATE ml_samples SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), r["file_hash"]))
                except Exception:
                    pass
            con.commit()

    return RedirectResponse("/review", status_code=303)

@router.post("/labels/new", name="create_label")  # -> POST /review/labels/new
def create_label(name: str = Form(...)):
    name = name.strip().replace(" ", "_")
    (Path(ARCHIVE_ROOT) / name).mkdir(parents=True, exist_ok=True)
    # append_rule_stub(name)  # enable when you add the helper
    return RedirectResponse("/review", status_code=303)

@router.post("/review/retrain", name="retrain_model")
def review_retrain():
    from nas_file_organizer.ml.train import train_and_save
    train_and_save(CACHE_DB, MODEL_OUT, os.environ.get("MODEL_VERSION", "tfidf-logreg-v1"))
    return RedirectResponse(url="/review?retrained=1", status_code=303)