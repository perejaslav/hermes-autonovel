#!/usr/bin/env python3
"""Non-mutating project audit for autonovel manuscripts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from autonovel_utils import BASE_DIR, discover_chapters


SUSPICIOUS_UNICODE_RE = re.compile(r"[\u3400-\u9fff]")


def _chapter_heading_style(text: str) -> str:
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    if re.match(r"^#\s+Chapter\s+\d+", first, re.IGNORECASE):
        return "hash_chapter_number"
    if re.match(r"^#\s+Chapter\s+\w+", first, re.IGNORECASE):
        return "hash_chapter_word"
    if first.startswith("#"):
        return "hash_other"
    return "prose_first"


def collect_audit(root: Path = BASE_DIR) -> dict:
    """Collect non-mutating audit findings for state and manuscript consistency."""
    root = Path(root)
    issues: list[str] = []
    details: dict[str, object] = {}

    chapters = discover_chapters(root)
    chapter_count = len(chapters)
    details["chapter_count"] = chapter_count

    state_path = root / "state.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        details["state"] = {
            "chapters_drafted": state.get("chapters_drafted"),
            "chapters_total": state.get("chapters_total"),
            "phase": state.get("phase"),
        }
        if state.get("chapters_total") != chapter_count:
            issues.append("state_chapter_total_mismatch")
    else:
        issues.append("missing_state_json")

    suspicious: list[dict[str, object]] = []
    heading_styles: dict[str, list[str]] = {}
    for chapter_num, path in chapters:
        text = path.read_text(encoding="utf-8")
        for match in SUSPICIOUS_UNICODE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            suspicious.append({
                "chapter": chapter_num,
                "file": str(path),
                "line": line,
                "text": match.group(0),
            })
        style = _chapter_heading_style(text)
        heading_styles.setdefault(style, []).append(path.name)

    if suspicious:
        issues.append("suspicious_unicode")
    if len(heading_styles) > 1:
        issues.append("inconsistent_chapter_headings")

    details["suspicious_unicode"] = suspicious
    details["chapter_heading_styles"] = heading_styles

    return {
        "issues": sorted(set(issues)),
        "details": details,
    }


def format_audit(report: dict) -> str:
    """Return an ASCII-safe JSON report for Windows console compatibility."""
    return json.dumps(report, indent=2, ensure_ascii=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit autonovel project state without changing files")
    parser.add_argument("--root", default=str(BASE_DIR), help="Project root to audit")
    args = parser.parse_args()
    print(format_audit(collect_audit(Path(args.root))))


if __name__ == "__main__":
    main()
