#!/usr/bin/env python3
"""Create a new book run from chat intake and launch foundation."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from foundation_wizard import apply_foundation_answers, default_config


BASE_DIR = Path(__file__).resolve().parent
ARCHIVE_TARGETS = [
    "seed.txt",
    "book_config.json",
    "state.json",
    "world.md",
    "characters.md",
    "outline.md",
    "canon.md",
    "voice.md",
    "manuscript.md",
    "results.tsv",
    "landing",
    "chapters",
    "briefs",
    "edit_logs",
    "eval_logs",
    "typeset/novel.tex",
    "typeset/novel.pdf",
    "typeset/the_speaking_tide.epub",
    "typeset/epub_metadata.yaml",
    "typeset/epub_style.css",
    "typeset/epub_front_matter.md",
    "typeset/epub_colophon.md",
    "typeset/epub_back_cover.md",
    "typeset/epub_out",
    "typeset/epub_build",
    "typeset/EPUB",
    "typeset/META-INF",
]
REQUIRED_FIELDS = [
    "premise_hint",
    "genre",
    "audience",
    "tone",
    "selected_seed",
    "world_direction",
    "character_direction",
    "outline_direction",
]


def default_state() -> dict:
    return {
        "phase": "foundation",
        "current_focus": "planning",
        "iteration": 0,
        "foundation_score": 0.0,
        "lore_score": 0.0,
        "chapters_drafted": 0,
        "chapters_total": 0,
        "novel_score": 0.0,
        "revision_cycle": 0,
        "debts": [],
    }


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_intake(source: str | None) -> dict:
    if source in (None, ""):
        if sys.stdin.isatty():
            raise ValueError("missing intake JSON; pass --intake path or pipe JSON to stdin")
        raw = sys.stdin.read()
    elif source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text(encoding="utf-8")

    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("intake JSON must be an object")
    return data


def validate_intake(intake: dict) -> dict:
    missing = [field for field in REQUIRED_FIELDS if not str(intake.get(field, "")).strip()]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing required intake fields: {joined}")
    return {field: str(intake[field]).strip() for field in REQUIRED_FIELDS}


def build_seed_text(intake: dict) -> str:
    return (
        "Семя романа\n\n"
        f"Идея: {intake['premise_hint']}\n"
        f"Жанр: {intake['genre']}\n"
        f"Аудитория: {intake['audience']}\n"
        f"Тон: {intake['tone']}\n\n"
        f"Выбранный seed: {intake['selected_seed']}\n\n"
        f"Мир: {intake['world_direction']}\n"
        f"Герои: {intake['character_direction']}\n"
        f"Сюжет: {intake['outline_direction']}\n\n"
        "Писать книгу на русском языке, без англоязычной обвязки в тексте романа.\n"
    )


def archive_existing_artifacts(project_root: Path, archive_existing: bool = True) -> tuple[Path | None, list[str]]:
    if not archive_existing:
        return None, []

    existing = [name for name in ARCHIVE_TARGETS if (project_root / name).exists()]
    if not existing:
        return None, []

    archive_dir = project_root / "archive" / datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived: list[str] = []
    for name in existing:
        source = project_root / name
        destination = archive_dir / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        archived.append(name)

    save_json(
        archive_dir / "archive_manifest.json",
        {
            "archived_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(project_root),
            "archived_items": archived,
        },
    )
    return archive_dir, archived


def launch_foundation(project_root: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, "run_pipeline.py", "--phase", "foundation"],
        cwd=str(project_root),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"foundation phase failed with exit code {result.returncode}")

    required_outputs = [
        project_root / "world.md",
        project_root / "characters.md",
        project_root / "outline.md",
        project_root / "canon.md",
    ]
    missing = [path.name for path in required_outputs if not path.exists() or path.stat().st_size == 0]
    if missing:
        raise RuntimeError(f"foundation did not create expected outputs: {', '.join(missing)}")

    return result


def start_new_book(
    intake: dict,
    project_root: Path = BASE_DIR,
    archive_existing: bool = True,
    run_foundation: bool = True,
) -> dict:
    project_root = Path(project_root)
    normalized = validate_intake(intake)

    archive_dir, archived_items = archive_existing_artifacts(project_root, archive_existing=archive_existing)

    seed_path = project_root / "seed.txt"
    config_path = project_root / "book_config.json"
    state_path = project_root / "state.json"

    seed_path.write_text(build_seed_text(normalized), encoding="utf-8")
    apply_foundation_answers(normalized, base_config=default_config(), path=config_path)
    save_json(state_path, default_state())

    foundation_result = None
    if run_foundation:
        foundation_result = launch_foundation(project_root)

    return {
        "project_root": project_root,
        "archive_dir": archive_dir,
        "archived_items": archived_items,
        "seed_path": seed_path,
        "config_path": config_path,
        "state_path": state_path,
        "foundation_result": foundation_result,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start a new autonovel book from chat intake")
    parser.add_argument(
        "--intake",
        default=None,
        help="Path to intake JSON, or '-' to read JSON from stdin",
    )
    parser.add_argument(
        "--archive-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Archive existing generated artifacts before creating the new book",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    intake = read_intake(args.intake)
    result = start_new_book(intake, archive_existing=args.archive_existing)

    if result["archive_dir"] is not None:
        print(f"Archived previous artifacts in {result['archive_dir']}")
    else:
        print("No previous generated artifacts found to archive")
    print(f"Seed written to {result['seed_path']}")
    print(f"Config written to {result['config_path']}")
    print("Foundation completed. Review outputs and wait for explicit approval before drafting.")


if __name__ == "__main__":
    main()
