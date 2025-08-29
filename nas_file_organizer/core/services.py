from __future__ import annotations
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional, Tuple
from rapidfuzz import fuzz
from ruyaml import YAML
from .models import Options, Rule, RuleMatch, RuleAction, Result
from .io_utils import list_files, read_text_any, next_available, render_template
import errno, shutil

yaml = YAML(typ="safe")
_log = None

def get_log() -> logging.Logger:
    global _log
    if _log is None:
        log_path = Path("logs/organizer.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            filename=log_path,
            filemode="a",
            format="%(asctime)s %(levelname)s %(message)s",
            level=logging.INFO,
        )
        _log = logging.getLogger("nas_organizer")
    return _log

def _as_str(val, field: str, rule_name: str) -> str:
    if isinstance(val, list):
        if len(val) == 1 and isinstance(val[0], str):
            return val[0]
        raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string, not a list.')
    if isinstance(val, str):
        return val
    raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string.')

def _as_list_str(val, field: str, rule_name: str) -> list[str] | None:
    if val is None:
        return None
    if isinstance(val, str):
        return [val]
    if isinstance(val, list) and all(isinstance(x, str) for x in val):
        return val
    raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string or list of strings.')

class OrganizerService:
    def load_options(self, rules_file: Path) -> Options:
        cfg = yaml.load(rules_file.read_text(encoding="utf-8"))

        rules: list[Rule] = []
        for r in cfg.get("rules", []):
            name = r["name"]
            m = r.get("match", {})
            a = r.get("action", {})

            rules.append(Rule(
                name=name,
                match=RuleMatch(
                    any_keywords=_as_list_str(m.get("any_keywords"), "match.any_keywords", name),
                    regex=m.get("regex"),
                    filetypes=_as_list_str(m.get("filetypes"), "match.filetypes", name),
                    fuzzy_min=m.get("fuzzy_min"),
                    patterns=_as_list_str(m.get("patterns"), "match.patterns", name),
                    min_score=int(m.get("min_score", 1)),
                    title_weight=float(m.get("title_weight", 2.0)),
                    body_weight=float(m.get("body_weight", 1.0)),
                    priority=int(m.get("priority", 0)),
                ),
                action=RuleAction(
                    move_to=_as_str(a.get("move_to"), "action.move_to", name),
                    rename=_as_str(a.get("rename", "{original}"), "action.rename", name),
                )
            ))

        defaults = cfg.get("defaults", {})
        page_window = defaults.get("page_window", {}) or {}
        first = int(page_window.get("first", 2))
        last  = int(page_window.get("last", 1))

        return Options(
            inbox=Path(cfg["inbox"]),
            archive_root=Path(cfg["archive_root"]),
            rules=rules,
            ocr_languages=str(defaults.get("ocr_languages", "eng")),
            ocr_on_empty_text=bool(defaults.get("ocr_on_empty_text", True)),
            page_window_first=first,
            page_window_last=last,
            dry_run=bool(defaults.get("dry_run", True)),
            skip_large_mb=int(defaults.get("skip_large_mb", 50)),
            title_lines=int(defaults.get("title_lines", 5)),
        )

    # --- scoring & classification

    def _score_rule(self, text: str, rule: Rule, title_n: int) -> Tuple[float, Optional[str]]:
        """Return (score, first_keyword_hit)."""
        m = rule.match

        # Split text into title (first 5 lines) and body (rest)
        lines = text.splitlines()
        title = "\n".join(lines[:title_n])
        body = "\n".join(lines[title_n:])

        score = 0.0
        first_kw: Optional[str] = None

        # exact keyword hits
        if m.any_keywords:
            for kw in m.any_keywords:
                if kw.lower() in title.lower():
                    score += m.title_weight
                    if not first_kw: first_kw = kw
                elif kw.lower() in body.lower():
                    score += m.body_weight
                    if not first_kw: first_kw = kw

            # fuzzy hit (anywhere) to catch minor typos
            if m.fuzzy_min:
                best = max((fuzz.partial_ratio(kw.lower(), text.lower()) for kw in m.any_keywords), default  = 0)
                if best >= m.fuzzy_min and not first_kw:
                    first_kw = m.any_keywords[0]
                    # give it a lighter boost than exact-title
                    score += m.body_weight

        # regex patterns (structural cues), count as double body weight
        if m.patterns:
            for pat in m.patterns:
                try:
                    if re.search(pat, text):
                        score += 2.0  # structural hit
                except re.error:
                    # ignore bad regex; could log if you add logging here
                    pass

        # simple regex presence (legacy field)
        if m.regex:
            try:
                if re.search(m.regex, text, flags=re.IGNORECASE):
                    score += m.body_weight
            except re.error:
                pass

        return score, first_kw

    def classify(self, path: Path, text: str, rules: list[Rule], opts: Options | None = None) -> tuple[
        Optional[Rule], Optional[str]]:
        ext = path.suffix.lower().lstrip(".")
        best: tuple[float, int, Optional[Rule], Optional[str]] = (-1.0, -10 ** 9, None, None)
        second: tuple[float, int, Optional[Rule], Optional[str]] = (-1.0, -10 ** 9, None, None)

        for rule in rules:
            m = rule.match
            if m.filetypes and ext not in m.filetypes:
                continue
            title_n = opts.title_lines if opts else 5  # fallback default
            score, first_kw = self._score_rule(text, rule, title_n)
            if score >= m.min_score:
                tup = (score, m.priority, rule, first_kw)
                if (score > best[0]) or (score == best[0] and m.priority > best[1]):
                    second = best
                    best = tup
                elif (score > second[0]) or (score == second[0] and m.priority > second[1]):
                    second = tup

        # if no match
        if not best[2]:
            return None, None

        # conflict threshold: if scores are effectively equal (within 0.25), mark for review
        if second[2] is not None and abs(best[0] - second[0]) < 0.25:
            return None, None  # signal "no confident match" → plan() will route to Review

        return best[2], best[3]

    # --- planning & execution

    def plan(self, opts: Options) -> Iterable[Result]:
        for p in list_files(opts.inbox):
            text = read_text_any(
                p,
                ocr_lang=opts.ocr_languages,
                skip_large_mb=opts.skip_large_mb,
                page_window_first=opts.page_window_first,
                page_window_last=opts.page_window_last,
                ocr_on_empty_text=opts.ocr_on_empty_text,
            )
            rule, first_kw = self.classify(p, text, opts.rules)
            if not rule:
                # Send to Review folder instead of pure no_match
                ts = datetime.fromtimestamp(p.stat().st_mtime)
                review_dir = opts.archive_root / "_Review" / f"{ts.year}-{ts.month:02d}-{ts.day:02d}"
                review_dir.mkdir(parents=True, exist_ok=True)
                dst = next_available(review_dir / p.name)
                yield Result(src=p, dst=dst, rule=None, ok=True, reason="review", text_excerpt=text[:200])
                continue
            ts = datetime.fromtimestamp(p.stat().st_mtime)
            dst_dir = Path(render_template(rule.action.move_to, original=p.name, date=ts, archive_root=opts.archive_root, first_keyword=first_kw))
            dst_dir.mkdir(parents=True, exist_ok=True)
            new_name = render_template(rule.action.rename, original=p.stem, date=ts, archive_root=opts.archive_root, first_keyword=first_kw) + p.suffix
            dst = next_available(dst_dir / new_name)
            yield Result(src=p, dst=dst, rule=rule.name, ok=True, text_excerpt=text[:200])

    def execute(self, opts: Options) -> Iterable[Result]:
        log = get_log()
        for r in self.plan(opts):
            if not r.dst or r.reason == "no_match":
                log.info("SKIP   %s (%s)", r.src, r.reason or "no_match")
                yield r
                continue
            try:
                if not opts.dry_run:
                    r.dst.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        # Fast path: same-mount rename
                        r.src.replace(r.dst)
                    except OSError as e:
                        if (getattr(e, "errno", None) == errno.EXDEV) or "Invalid cross-device link" in str(e):
                            shutil.copy2(r.src, r.dst)
                            r.src.unlink()
                        else:
                            raise

                if r.reason == "review":
                    log.info("REVIEW %s -> %s", r.src, r.dst)
                else:
                    log.info("MOVED  %s -> %s", r.src, r.dst)

                yield r
            except Exception as e:
                log.error("ERROR  %s -> %s (%s)", r.src, r.dst, str(e))
                yield Result(
                    src=r.src,
                    dst=r.dst,
                    rule=r.rule,
                    ok=False,
                    reason=str(e),
                    text_excerpt=r.text_excerpt,
                )

#docker exec - it de2d4e577153 sh - lc "nas-organizer -c /app/rules.yaml --trace | sed -n '1,200p'"
