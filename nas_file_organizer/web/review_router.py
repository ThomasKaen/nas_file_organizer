# nas_file_organizer/web/review_router.py
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os, sqlite3, shutil, pathlib
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

CACHE_DB     = os.environ.get("CACHE_DB", "/data/cache.db")
ARCHIVE_ROOT = os.environ.get("ARCHIVE_ROOT", "/data/archive")

def db():
    con = sqlite3.connect(CACHE_DB)
    con.row_factory = sqlite3.Row
    return con

def top_level_labels():
    root = pathlib.Path(ARCHIVE_ROOT)
    if not root.exists(): return []
    return sorted([p.name for p in root.iterdir() if p.is_dir() and not p.name.startswith("_")])

@router.get("/review")
def review_page(request: Request, page: int = 1, per: int = 20, only_pending: int = 1):
    offset = (page-1) * per
    with db() as con:
        # show predicted items; when only_pending=1, hide ones already gold-labeled
        rows = con.execute(f"""
            SELECT s.file_hash, s.path, s.text, s.predicted_label, s.confidence,
                   (SELECT lbl.label FROM ml_labels AS lbl WHERE lbl.file_hash = s.file_hash) AS gold_label
            FROM ml_samples AS s
            ORDER BY s.created_at DESC
            LIMIT ? OFFSET ?
        """, (per, offset)).fetchall()

    if only_pending:
        rows = [r for r in rows if (r["gold_label"] is None)]

    return templates.TemplateResponse("review.html", {
        "request": request,
        "rows": rows,
        "labels": top_level_labels(),
        "page": page, "per": per, "only_pending": only_pending,
        "archive_root": ARCHIVE_ROOT
    })

@router.post("/review/confirm")
def review_confirm(
    file_hash: str = Form(...),
    predicted_label: str = Form(None),
    corrected_label: str = Form(...),
    move_file: int = Form(1)
):
    corrected_label = (corrected_label or "").strip()
    if not corrected_label:
        return RedirectResponse(url="/review", status_code=303)

    with db() as con:
        # fetch current path + text
        row = con.execute("SELECT path, text FROM ml_samples WHERE file_hash = ?", (file_hash,)).fetchone()
        if not row:
            return RedirectResponse(url="/review", status_code=303)

        cur_path = row["path"]
        # 1) upsert gold label
        con.execute("""
            INSERT INTO ml_labels(file_hash, label, source, created_at)
            VALUES(?,?, 'human', CURRENT_TIMESTAMP)
            ON CONFLICT(file_hash) DO UPDATE SET label=excluded.label
        """, (file_hash, corrected_label))

        # 2) record correction if different from prediction
        if predicted_label and predicted_label != corrected_label:
            con.execute("""
                INSERT INTO ml_corrections(file_hash, predicted_label, corrected_label, created_at)
                VALUES(?,?,?,CURRENT_TIMESTAMP)
            """, (file_hash, predicted_label, corrected_label))

        con.commit()

    # 3) optional: move file from _Review (or wrong folder) to corrected folder
    try:
        if move_file:
            src = pathlib.Path(cur_path)
            # if it's not already under the correct label, move it
            rel = pathlib.Path(os.path.relpath(cur_path, ARCHIVE_ROOT))
            top = rel.parts[0] if len(rel.parts) else None
            if top != corrected_label:
                dst_dir = pathlib.Path(ARCHIVE_ROOT) / corrected_label
                dst_dir.mkdir(parents=True, exist_ok=True)
                dst = dst_dir / src.name
                shutil.move(str(src), str(dst))
                # reflect the move in DB tables
                with db() as con:
                    con.execute("UPDATE text_cache SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), file_hash))
                    con.execute("UPDATE ml_samples SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), file_hash))
                    con.commit()
    except Exception:
        # keep UX smooth even if move fails (e.g., cross-device issues)
        pass

    return RedirectResponse(url="/review", status_code=303)
