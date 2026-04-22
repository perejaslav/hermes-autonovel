#!/usr/bin/env python3
"""
One-shot characters.md generator for foundation phase.
Reads seed.txt + voice.md + world.md + CRAFT.md, calls writer model.
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


def build_prompt(seed: str, world: str, voice: str, craft: str) -> str:
    return f"""Create a character registry for this novel.

LANGUAGE CONTRACT:
{language_instruction()}

SEED:
{seed}

WORLD BIBLE:
{world}

VOICE GUARDRAILS:
{voice or "(voice.md is empty)"}

CRAFT REFERENCE EXCERPT:
{craft[:5000] if craft else "(CRAFT.md not found)"}

Write `characters.md` in Markdown. Include:
- Protagonist, antagonistic forces, allies, foils, mentors, secondary cast
- For each major character: wound, want, need, lie, fear, secret, leverage, agency
- Relationships and pressure points between characters
- Speech patterns: syntax, vocabulary, metaphor domain, what they avoid saying
- Plot function and scenes they are required for

Make every major character specific enough to draft dialogue without tags.
Return only the Markdown document."""


def main() -> None:
    try:
        seed = read_required_file(BASE_DIR / "seed.txt", "character generation")
        world = read_required_file(BASE_DIR / "world.md", "character generation", min_chars=100)
        voice = read_optional_file(BASE_DIR / "voice.md")
        craft = read_optional_file(BASE_DIR / "CRAFT.md")
        result = call_writer(build_prompt(seed, world, voice, craft))
        write_generated_file(BASE_DIR / "characters.md", result, "character registry")
        print("Saved characters.md")
    except MissingInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
