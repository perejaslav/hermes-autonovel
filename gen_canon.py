#!/usr/bin/env python3
"""
Generate canon.md by extracting all hard facts from world.md + characters.md.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from autonovel_utils import BASE_DIR, MissingInputError, language_instruction, read_optional_file, read_required_file, write_generated_file

load_dotenv(BASE_DIR / ".env")

WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", "auto")

def call_writer(prompt, max_tokens=16000):
    from _api_adapter import call_writer as _orig
    return _orig(prompt, max_tokens=max_tokens)


def build_prompt(world: str, characters: str, outline: str, existing_canon: str) -> str:
    return f"""Build a canon database from the planning documents.

LANGUAGE CONTRACT:
{language_instruction()}

WORLD BIBLE:
{world}

CHARACTER REGISTRY:
{characters}

OUTLINE:
{outline}

EXISTING CANON:
{existing_canon or "(none)"}

Write `canon.md` in Markdown as a hard-facts database. Include:
- People: names, ages if known, roles, relationships, physical facts
- Places: location facts, rules, social/economic facts
- Magic/speculative rules: costs, limits, failure cases
- Timeline facts and historical events
- Open contradictions or missing facts that should block drafting

Use concise entries with source hints. Return only the Markdown document."""


def main() -> None:
    try:
        world = read_required_file(BASE_DIR / "world.md", "canon generation", min_chars=100)
        characters = read_required_file(BASE_DIR / "characters.md", "canon generation", min_chars=100)
        outline = read_required_file(BASE_DIR / "outline.md", "canon generation", min_chars=100)
        existing_canon = read_optional_file(BASE_DIR / "canon.md")
        result = call_writer(build_prompt(world, characters, outline, existing_canon))
        write_generated_file(BASE_DIR / "canon.md", result, "canon")
        print("Saved canon.md")
    except MissingInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
