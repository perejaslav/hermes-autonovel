#!/usr/bin/env python3
"""Generate remaining chapters + foreshadowing ledger."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from autonovel_utils import BASE_DIR, MissingInputError, read_required_file, write_generated_file

load_dotenv(BASE_DIR / ".env")

WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", "auto")

def call_writer(prompt, max_tokens=16000):
    from _api_adapter import call_writer as _orig
    return _orig(prompt, max_tokens=max_tokens)


def build_prompt(outline: str, characters: str, world: str) -> str:
    return f"""Improve this outline by adding or repairing its foreshadowing ledger.

WORLD BIBLE:
{world}

CHARACTER REGISTRY:
{characters}

CURRENT OUTLINE:
{outline}

Return a complete replacement for `outline.md`, preserving all chapter entries and adding a final section:

## FORESHADOWING LEDGER

The ledger must track each thread, where it is planted, escalated, and harvested.
Every plant should have a planned payoff or an explicit reason it remains unresolved.
Return only the full Markdown document."""


def main() -> None:
    try:
        outline = read_required_file(BASE_DIR / "outline.md", "foreshadowing ledger generation", min_chars=100)
        characters = read_required_file(BASE_DIR / "characters.md", "foreshadowing ledger generation", min_chars=100)
        world = read_required_file(BASE_DIR / "world.md", "foreshadowing ledger generation", min_chars=100)
        result = call_writer(build_prompt(outline, characters, world))
        write_generated_file(BASE_DIR / "outline.md", result, "outline with foreshadowing")
        print("Saved outline.md")
    except MissingInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
