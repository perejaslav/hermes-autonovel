#!/usr/bin/env python3
"""
One-shot world.md generator for foundation phase.
Reads seed.txt + voice.md, calls the writer model, outputs world.md content.
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


def build_prompt(seed: str, voice: str, craft: str) -> str:
    return f"""Create a reusable world bible for a fantasy novel from this seed.

LANGUAGE CONTRACT:
{language_instruction()}

SEED:
{seed}

VOICE GUARDRAILS:
{voice or "(voice.md is empty; define usable prose constraints in the world bible where relevant)"}

CRAFT REFERENCE EXCERPT:
{craft[:5000] if craft else "(CRAFT.md not found)"}

Write `world.md` in Markdown. Include concrete, draft-ready sections:
- Core premise and world differentiator
- Magic/speculative system with limits, costs, failure cases, and social consequences
- Geography, economy, class pressure, culture, law, factions, history
- Locations with sensory signatures and plot use
- Open questions the author must answer before drafting

Be specific enough that another script can draft scenes without inventing missing rules.
Return only the Markdown document."""


def main() -> None:
    try:
        seed = read_required_file(BASE_DIR / "seed.txt", "world generation")
        voice = read_optional_file(BASE_DIR / "voice.md")
        craft = read_optional_file(BASE_DIR / "CRAFT.md")
        result = call_writer(build_prompt(seed, voice, craft))
        write_generated_file(BASE_DIR / "world.md", result, "world bible")
        print("Saved world.md")
    except MissingInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
