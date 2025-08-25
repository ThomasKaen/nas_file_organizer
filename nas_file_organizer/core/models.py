from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

@dataclass
class RuleAction:
    move_to: str
    rename: str

@dataclass
class RuleMatch:
    any_keywords: Sequence[str] | None = None
    regex: str | None = None
    filetypes: Sequence[str] | None = None
    min_fuzzy: int | None = None

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