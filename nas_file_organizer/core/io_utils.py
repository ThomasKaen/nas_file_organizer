from __future__ import annotations
import io
from pathlib import Path
from typing import Iterable, Iterator
from datetime import datetime
import chardet
import fitz
from PIL import Image
import pytesseract
from docx import Document
from openpyxl import load_workbook

def list_files(folder: Path) -> Iterable[Path]:
    for p in folder.rglob("*"):
        if p.is_file():
            yield p

def read_text_any(path: Path, ocr_lang: str="eng", skip_large_mb: int = 50) -> str:
    try:
        if path.stat().st_size > skip_large_mb * 1024 * 1024:
            return ""
    except Exception:
        pass
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _pdf_text(path, ocr_lang)
    if ext in {".txt", ".log", ".md"}:
        return _txt_text(path)
    if ext == ".docx":
        return _docx_text(path)
    if ext == ".xlsx":
        return _xlsx_text(path)
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"}:
        return _image_ocr(path, ocr_lang)
    return ""  # unknown types



def _pdf_text(path: Path, ocr_lang: str) -> str:
    try:
        doc = fitz.open(path)
        text_pages = []
        for page in doc:
            t = page.get_text("text") or ""
            if not t.strip():
                # OCR the page image if no text layer
                pix = page.get_pixmap(dpi=200)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                t = pytesseract.image_to_string(img, lang=ocr_lang)
            text_pages.append(t)
        return "\n".join(text_pages)
    except Exception:
        return ""

def _image_ocr(path: Path, ocr_lang: str) -> str:
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img, lang=ocr_lang)
    except Exception:
        return ""

def _txt_text(path: Path) -> str:
    raw = path.read_bytes()
    enc = chardet.detect(raw).get("encoding") or "utf-8"
    try:
        return raw.decode(enc, errors="ignore")
    except Exception:
        return ""

def _docx_text(path: Path) -> str:
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""

def _xlsx_text(path: Path) -> str:
    try:
        wb = load_workbook(path, data_only=True)
        out = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                out.append(" ".join("" if v is None else str(v) for v in row))
        return "\n".join(out)
    except Exception:
        return ""

def next_available(p: Path) -> Path:
    if not p.exists(): return p
    stem, suf = p.stem, p.suffix
    i = 2
    while True:
        cand = p.with_name(f"{stem}_{i}{suf}")
        if not cand.exists(): return cand
        i += 1

def render_template(tmpl: str, *, original: str, date: datetime, archive_root: Path, first_keyword: str | None = None) -> str:
    return (tmpl
            .replace("{original}", original)
            .replace("{year}", f"{date.year}")
            .replace("{month}", f"{date.month:02d}")
            .replace("{day}", f"{date.day:02d}")
            .replace("{date}", date.strftime("%Y-%m-%d"))
            .replace("{archive_root}", str(archive_root))
            .replace("{first_keyword}", first_keyword or ""))