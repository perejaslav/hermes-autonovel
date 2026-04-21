#!/usr/bin/env python3
"""Batch draft chapters with quick local checks and optional spot evaluations."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from autonovel_utils import BASE_DIR, discover_chapters

CHAPTERS_DIR = BASE_DIR / "chapters"
STATE_FILE = BASE_DIR / "state.json"


def run(args: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(BASE_DIR),
    )


def word_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def pattern_check(path: Path) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8")
    did_not = len(re.findall(r"\bHe (?:did|had) not\b", text))
    thought = len(re.findall(r"\bHe thought (?:about|of)\b", text))
    return word_count(path), did_not, thought


def slop_check(chapter_num: int) -> dict:
    code = (
        "from evaluate import slop_score, load_file; "
        "import json; "
        f"r=slop_score(load_file('chapters/ch_{chapter_num:02d}.md')); "
        "print(json.dumps(r))"
    )
    result = run([sys.executable, "-c", code])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "slop check failed")
    return json.loads(result.stdout.strip())


def spot_eval(chapter_num: int) -> tuple[float | None, float | None]:
    result = run([sys.executable, "evaluate.py", f"--chapter={chapter_num}"], timeout=300)
    m_overall = re.search(r"overall_score: ([\d.]+)", result.stdout)
    m_raw = re.search(r"raw_judge_score: ([\d.]+)", result.stdout)
    if m_overall:
        raw = float(m_raw.group(1)) if m_raw else None
        return float(m_overall.group(1)), raw
    return None, None


def update_state(chapter_num: int) -> None:
    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    state["current_focus"] = f"ch_{chapter_num:02d}"
    state["chapters_drafted"] = chapter_num
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch draft chapters")
    parser.add_argument("start", type=int, nargs="?", default=1)
    parser.add_argument("end", type=int, nargs="?")
    parser.add_argument(
        "--spot-eval",
        type=int,
        nargs="*",
        default=[],
        help="Chapter numbers to evaluate after drafting",
    )
    args = parser.parse_args()

    existing = discover_chapters(BASE_DIR)
    inferred_end = max((num for num, _ in existing), default=args.start)
    end = args.end or inferred_end
    chapters = list(range(args.start, end + 1))

    results = []
    for chapter_num in chapters:
        print(f"\n{'=' * 50}\nDRAFTING CH {chapter_num}\n{'=' * 50}")
        draft = run([sys.executable, "draft_chapter.py", str(chapter_num)], timeout=900)
        if draft.returncode != 0:
            print(f"  DRAFT FAILED: {(draft.stderr or draft.stdout)[:300]}")
            results.append((chapter_num, 0, 0, None))
            continue

        chapter_path = CHAPTERS_DIR / f"ch_{chapter_num:02d}.md"
        words, did_not, thought = pattern_check(chapter_path)
        slop = slop_check(chapter_num)

        score = None
        if chapter_num in args.spot_eval:
            score, raw = spot_eval(chapter_num)
            print(f"  Score: {score} (raw {raw})")

        print(f"  Words: {words}")
        print(f"  Slop penalty: {slop['slop_penalty']}")
        print(f"  Patterns: did_not={did_not} thought={thought}")
        update_state(chapter_num)
        results.append((chapter_num, words, slop["slop_penalty"], score))

    total_words = sum(words for _, words, _, _ in results)
    print(f"\nBATCH DRAFTING COMPLETE: {total_words} new words")


if __name__ == "__main__":
    main()
