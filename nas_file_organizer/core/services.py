from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional, Tuple
from rapidfuzz import fuzz
from ruyaml import YAML
from .models import Options, Rule, RuleMatch, RuleAction, Result
from .io_utils import list_files, read_text_any, next_available, render_template

yaml = YAML(typ="safe")

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
        )

    # --- scoring & classification

    def _score_rule(self, text: str, rule: Rule) -> Tuple[float, Optional[str]]:
        """Return (score, first_keyword_hit)."""
        m = rule.match

        # Split text into title (first 5 lines) and body (rest)
        lines = text.splitlines()
        title = "\n".join(lines[:5]) if lines else ""
        body = "\n".join(lines[5:]) if len(lines) > 5 else ""

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

    def classify(self, path: Path, text: str, rules: list[Rule]) -> tuple[Optional[Rule], Optional[str]]:
        ext = path.suffix.lower().lstrip(".")
        best: tuple[float, int, Optional[Rule], Optional[str]] = (-1.0, -10**9, None, None)  # (score, priority, rule, first_kw)

        for rule in rules:
            m = rule.match
            if m.filetypes and ext not in m.filetypes:
                continue
            score, first_kw = self._score_rule(text, rule)
            if score >= m.min_score:
                # pick best by (score, priority)
                if (score > best[0]) or (score == best[0] and m.priority > best[1]):
                    best = (score, m.priority, rule, first_kw)

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
                yield Result(src=p, dst=None, rule=None, ok=True, reason="no_match", text_excerpt=text[:200])
                continue
            ts = datetime.fromtimestamp(p.stat().st_mtime)
            dst_dir = Path(render_template(rule.action.move_to, original=p.name, date=ts, archive_root=opts.archive_root, first_keyword=first_kw))
            dst_dir.mkdir(parents=True, exist_ok=True)
            new_name = render_template(rule.action.rename, original=p.stem, date=ts, archive_root=opts.archive_root, first_keyword=first_kw) + p.suffix
            dst = next_available(dst_dir / new_name)
            yield Result(src=p, dst=dst, rule=rule.name, ok=True, text_excerpt=text[:200])

    def execute(self, opts: Options) -> Iterable[Result]:
        for r in self.plan(opts):
            if not r.dst or r.reason == "no_match":
                yield r
                continue
            try:
                if not opts.dry_run:
                    r.src.replace(r.dst)
                yield r
            except Exception as e:
                yield Result(src=r.src, dst=r.dst, rule=r.rule, ok=False, reason=str(e), text_excerpt=r.text_excerpt)
