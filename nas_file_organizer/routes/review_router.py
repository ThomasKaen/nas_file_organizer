from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER
import sqlite3
import os


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
