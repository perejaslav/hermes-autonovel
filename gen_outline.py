#!/usr/bin/env python3
"""Generate outline.md from seed + world + characters + mystery + craft."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from autonovel_utils import BASE_DIR, MissingInputError, read_optional_file, read_required_file, write_generated_file

load_dotenv(BASE_DIR / ".env")

WRITER_MODEL = os.environ.get("AUTONOVEL_WRITER_MODEL", "auto")

def call_writer(prompt, max_tokens=16000):
    from _api_adapter import call_writer as _orig
    return _orig(prompt, max_tokens=max_tokens)


def build_prompt(seed: str, world: str, characters: str, mystery: str, craft: str) -> str:
    return f"""Create the main chapter outline for this novel.

SEED:
{seed}

WORLD BIBLE:
{world}

CHARACTER REGISTRY:
{characters}

AUTHOR-ONLY MYSTERY NOTES:
{mystery or "(MYSTERY.md is empty or missing; define the central secret if needed)"}

CRAFT REFERENCE EXCERPT:
{craft[:5000] if craft else "(CRAFT.md not found)"}

Write `outline.md` in Markdown. Use this exact chapter heading pattern so other tools can parse it:
`### Ch N: Title`

For each chapter include:
- POV, location, purpose in the act structure
- concrete scene beats in order
- try-fail cycle outcome
- emotional movement
- plants and payoffs needed later
- chapter-ending question

Aim for a complete novel-length outline, not a synopsis. Return only the Markdown document."""


def main() -> None:
    try:
        seed = read_required_file(BASE_DIR / "seed.txt", "outline generation")
        world = read_required_file(BASE_DIR / "world.md", "outline generation", min_chars=100)
        characters = read_required_file(BASE_DIR / "characters.md", "outline generation", min_chars=100)
        mystery = read_optional_file(BASE_DIR / "MYSTERY.md")
        craft = read_optional_file(BASE_DIR / "CRAFT.md")
        result = call_writer(build_prompt(seed, world, characters, mystery, craft))
        write_generated_file(BASE_DIR / "outline.md", result, "outline")
        print("Saved outline.md")
    except MissingInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
