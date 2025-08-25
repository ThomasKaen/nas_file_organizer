from __future__ import annotations
import re
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional
from rapidfuzz import fuzz
from ruyaml import YAML
from .models import Options, Rule, RuleMatch, RuleAction, Result
from .io_utils import list_files, read_text_any, next_available, render_template
import logging
from logging.handlers import RotatingFileHandler

yaml = YAML(typ="safe")

def _as_str(val, field: str, rule_name: str) -> str:
    if isinstance(val, list):
        if len(val) == 1 and isinstance(val[0], str):
            return val[0]
        raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string, not a list.')
    if isinstance(val, str):
        return val
    raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string.')

def _as_list_str(val, field: str, rule_name: str):
    if val is None:
        return None
    if isinstance(val, str):
        return [val]
    if isinstance(val, list) and all(isinstance(x, str) for x in val):
        return val
    raise ValueError(f'Rule "{rule_name}": field "{field}" must be a string or list of strings.')

def get_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("nas_organizer")
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

class OrganizerService:
    def load_options(self, rules_file: Path) -> Options:
        cfg = yaml.load(rules_file.read_text(encoding="utf-8"))

        rules: list[Rule] = []
        for r in cfg.get("rules", []):
            name = r["name"]
            m = r.get("match", {})
            a = r.get("action", {})

            any_keywords = _as_list_str(m.get("any_keywords"), "match.any_keywords", name)
            filetypes    = _as_list_str(m.get("filetypes"),    "match.filetypes",    name)
            regex        = m.get("regex")
            min_fuzzy    = m.get("min_fuzzy")

            move_to = _as_str(a.get("move_to"), "action.move_to", name)
            rename  = _as_str(a.get("rename", "{original}"), "action.rename", name)

            rules.append(Rule(
                name=name,
                match=RuleMatch(
                    any_keywords=any_keywords,
                    regex=regex,
                    filetypes=filetypes,
                    min_fuzzy=min_fuzzy,
                ),
                action=RuleAction(
                    move_to=move_to,
                    rename=rename,
                )
            ))

        defaults = cfg.get("defaults", {})
        return Options(
            inbox=Path(cfg["inbox"]),
            archive_root=Path(cfg["archive_root"]),
            rules=rules,
            ocr_languages=defaults.get("ocr_languages", "eng"),
            dry_run=bool(defaults.get("dry_run", True)),
            skip_large_mb=int(defaults.get("skip_large_mb", 50)),
        )

    def classify(self, path: Path, text: str, rules: list[Rule]) -> tuple[Optional[Rule], Optional[str]]:
        ext = path.suffix.lower().lstrip(".")
        text_low = text.lower()
        for rule in rules:
            m = rule.match
            if m.filetypes and ext not in m.filetypes:
                continue
            first_keyword = None
            if m.any_keywords:
                for kw in m.any_keywords:
                    if kw.lower() in text_low:
                        first_keyword = kw
                        break
                if not first_keyword and m.min_fuzzy:
                    best = max((fuzz.partial_ratio(kw.lower(), text_low) for kw in m.any_keywords), default=0)
                    if best >= m.min_fuzzy:
                        first_keyword = m.any_keywords[0]
                    else:
                        continue
                elif not first_keyword and not m.min_fuzzy:
                    continue
            if m.regex and not re.search(m.regex, text, flags=re.IGNORECASE):
                continue
            return rule, first_keyword
        return None, None

    def plan(self, opts: Options) -> Iterable[Result]:
        for p in list_files(opts.inbox):
            text = read_text_any(p, opts.ocr_languages, opts.skip_large_mb)
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
        log = get_logger(Path("logs/organizer.log"))
        for r in self.plan(opts):
            if not r.dst or r.reason == "no_match":
                if r.reason == "no_match":
                    log.info("SKIP src=%s reason=no_match", r.src)
                yield r
                continue
            try:
                if not opts.dry_run:
                    r.src.replace(r.dst)
                log.info("MOVED src=%s dst=%s rule=%s", r.src, r.dst, r.rule)
                yield r
            except Exception as e:
                log.error("ERROR src=%s reason=%s", r.src, str(e))
                yield Result(src=r.src, dst=r.dst, rule=r.rule, ok=False, reason=str(e), text_excerpt=r.text_excerpt)