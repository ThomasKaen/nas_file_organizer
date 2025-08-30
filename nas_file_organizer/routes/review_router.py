from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
import sqlite3
import os, pathlib, shutil
from typing import List


router = APIRouter()
DB_PATH = os.environ.get("CACHE_DB", "/data/cache.db")


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

@router.get("/review")
async def review_page(request: Request):
    with conn() as c:
        rows = c.execute(
            """
            SELECT s.file_hash, s.path, s.predicted_label, s.confidence, t.text
            FROM ml_samples s
            LEFT JOIN text_cache t ON t.file_hash = s.file_hash
            WHERE NOT EXISTS (
            SELECT 1 FROM ml_corrections x WHERE x.file_hash = s.file_hash
            )
            ORDER BY s.created_at DESC LIMIT 200
            """
        ).fetchall()
    return request.app.templates.TemplateResponse("review.html", {"request": request, "items": rows})

@router.post("/review/submit")
async def submit_review(file_hash: str = Form(...), corrected_label: str = Form(...), predicted_label: str = Form("")):
    with conn() as c:
        c.execute(
            "INSERT INTO ml_corrections(file_hash, predicted_label, corrected_label) VALUES(?,?,?)",
            (file_hash, predicted_label, corrected_label)
        )
        c.execute(
            "INSERT OR REPLACE INTO ml_labels(file_hash, label, source) VALUES(?, ?, 'human')",
            (file_hash, corrected_label)
        )
        c.commit()
    return RedirectResponse(url="/review", status_code=HTTP_303_SEE_OTHER)

@router.post("/review/bulk")
def review_bulk_assign(
    file_hash: List[str] = Form([]),
    corrected_label: str = Form(...),
    move_file: int = Form(1),
):
    if not file_hash:
        return RedirectResponse("/review", status_code=303)

    ARCHIVE_ROOT = os.environ.get("ARCHIVE_ROOT", "/data/archive")

    def db():
        con = sqlite3.connect(os.environ.get("CACHE_DB", "/data/cache.db"))
        con.row_factory = sqlite3.Row
        return con

    with db() as con:
        # fetch paths for all selected
        qmarks = ",".join(["?"] * len(file_hash))
        rows = con.execute(
            f"SELECT file_hash, path FROM ml_samples WHERE file_hash IN ({qmarks})",
            file_hash,
        ).fetchall()

        # upsert gold labels and (if needed) corrections
        con.executemany(
            """INSERT INTO ml_labels(file_hash, label, source, created_at)
               VALUES(?, ?, 'human', CURRENT_TIMESTAMP)
               ON CONFLICT(file_hash) DO UPDATE SET label=excluded.label""",
            [(r["file_hash"], corrected_label) for r in rows],
        )

        # optional: record correction events when prediction differs
        preds = {
            r["file_hash"]: r["predicted_label"]
            for r in con.execute(
                f"SELECT file_hash, predicted_label FROM ml_samples WHERE file_hash IN ({qmarks})",
                file_hash,
            )
        }
        con.executemany(
            """INSERT INTO ml_corrections(file_hash, predicted_label, corrected_label, created_at)
               VALUES(?,?,?,CURRENT_TIMESTAMP)""",
            [
                (fh, preds.get(fh), corrected_label)
                for fh in file_hash
                if preds.get(fh) and preds.get(fh) != corrected_label
            ],
        )
        con.commit()

    # move files (best-effort)
    if move_file:
        dst_dir = pathlib.Path(ARCHIVE_ROOT) / corrected_label
        dst_dir.mkdir(parents=True, exist_ok=True)
        with db() as con:
            for r in rows:
                try:
                    src = pathlib.Path(r["path"])
                    if not src.exists():
                        continue
                    # skip if already under the chosen label
                    rel = pathlib.Path(os.path.relpath(str(src), ARCHIVE_ROOT))
                    top = rel.parts[0] if rel.parts else None
                    if top == corrected_label:
                        continue
                    dst = dst_dir / src.name
                    shutil.move(str(src), str(dst))
                    # reflect in DB
                    con.execute("UPDATE text_cache SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), r["file_hash"]))
                    con.execute("UPDATE ml_samples SET path=?, updated_at=CURRENT_TIMESTAMP WHERE file_hash=?",
                                (str(dst), r["file_hash"]))
                except Exception:
                    pass
            con.commit()

    return RedirectResponse("/review", status_code=303)