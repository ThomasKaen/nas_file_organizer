from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

@dataclass
class RuleMatch:
    any_keywords: Sequence[str] | None = None
    regex: str | None = None
    filetypes: Sequence[str] | None = None
    fuzzy_min: int | None = None     # 0..100
    patterns: Sequence[str] | None = None
    min_score: int = 1
    title_weight: float = 2.0
    body_weight: float = 1.0
    priority: int = 0

@dataclass
class RuleAction:
    move_to: str
    rename: str = "{original}"

@dataclass
class Rule:
    name: str
    match: RuleMatch
    action: RuleAction

@dataclass
class Options:
    inbox: Path
    archive_root: Path
    rules: list[Rule]
    ocr_languages: str = "eng"
    ocr_on_empty_text: bool = True
    page_window_first: int = 2
    page_window_last: int = 1
    dry_run: bool = True
    skip_large_mb: int = 50

@dataclass
class Result:
    src: Path
    dst: Optional[Path]
    rule: Optional[str]
    ok: bool
    reason: Optional[str] = None
    text_excerpt: str = ""
