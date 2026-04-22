#!/usr/bin/env python3
"""Interactive foundation setup for a new autonovel book."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _api_adapter import call_writer
from autonovel_utils import BASE_DIR, language_instruction


CONFIG_FILE = BASE_DIR / "book_config.json"


def default_config() -> dict:
    """Return default book configuration for Hermes-native runs."""
    return {
        "language": "ru",
        "language_name": "Russian",
        "interactive_foundation": True,
        "foundation": {
            "premise_hint": "",
            "audience": "adult literary fantasy readers",
            "tone": "specific, sensory, emotionally restrained",
            "genre": "fantasy",
            "selected_seed": "",
            "world_direction": "",
            "character_direction": "",
            "outline_direction": "",
        },
    }


def load_config(path: Path = CONFIG_FILE) -> dict:
    """Load config or return defaults when missing."""
    if not path.exists():
        return default_config()
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = default_config()
    merged.update({k: v for k, v in data.items() if k != "foundation"})
    merged["foundation"].update(data.get("foundation", {}))
    return merged


def save_config(config: dict, path: Path = CONFIG_FILE) -> None:
    """Persist book configuration."""
    path.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def apply_foundation_answers(
    answers: dict,
    base_config: dict | None = None,
    path: Path | None = None,
) -> dict:
    """Apply chat-collected foundation answers and optionally persist them."""
    config = base_config or default_config()
    foundation = config.setdefault("foundation", default_config()["foundation"].copy())
    allowed_fields = set(default_config()["foundation"].keys())

    for key, value in answers.items():
        if key in allowed_fields:
            foundation[key] = str(value).strip()

    config["language"] = config.get("language") or "ru"
    config["language_name"] = config.get("language_name") or "Russian"
    config["interactive_foundation"] = False

    if path is not None:
        save_config(config, path)

    return config


def build_seed_options_prompt(config: dict, premise_hint: str) -> str:
    """Build the prompt used to generate seed options for user selection."""
    foundation = config.get("foundation", {})
    return f"""LANGUAGE CONTRACT:
{language_instruction(config.get("language"))}

Generate 5 distinct novel seed options for an interactive foundation wizard.

PREMISE HINT:
{premise_hint or foundation.get("premise_hint") or "(none supplied)"}

GENRE:
{foundation.get("genre", "fantasy")}

AUDIENCE:
{foundation.get("audience", "adult literary fantasy readers")}

TONE:
{foundation.get("tone", "specific, sensory, emotionally restrained")}

For each option provide:
NUMBER. TITLE
HOOK: one sentence
WORLD: concrete differentiator
MAIN CHARACTER: who carries the story
TENSION: personal and external conflict
WHY THIS OPTION: what makes it worth choosing

Return only the options, not analysis of this prompt."""


def ask(prompt: str, default: str = "") -> str:
    """Prompt for one line of user input."""
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value or default


def run_wizard(args: argparse.Namespace) -> dict:
    """Run the interactive setup and save the resulting config."""
    config_path = Path(args.config) if args.config else CONFIG_FILE
    config = load_config(config_path)
    foundation = config["foundation"]

    print("Hermes Autonovel foundation wizard")
    foundation["premise_hint"] = ask("Идея или направление книги", args.premise or foundation["premise_hint"])
    foundation["genre"] = ask("Жанр", foundation["genre"])
    foundation["audience"] = ask("Аудитория", foundation["audience"])
    foundation["tone"] = ask("Тон", foundation["tone"])

    if args.generate_seeds:
        prompt = build_seed_options_prompt(config, foundation["premise_hint"])
        print("\nGenerating seed options with the configured writer model...\n")
        print(call_writer(prompt, max_tokens=4000))
        foundation["selected_seed"] = ask("Вставьте выбранный seed или свою версию", foundation["selected_seed"])
    else:
        foundation["selected_seed"] = ask("Выбранный seed", foundation["selected_seed"])

    foundation["world_direction"] = ask("Ключевое направление мира", foundation["world_direction"])
    foundation["character_direction"] = ask("Ключевое направление героев", foundation["character_direction"])
    foundation["outline_direction"] = ask("Ключевое направление сюжета", foundation["outline_direction"])

    save_config(config, config_path)
    print(f"\nSaved {config_path}")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive foundation wizard")
    parser.add_argument("--config", default=None, help="Path to book_config.json")
    parser.add_argument("--premise", default="", help="Initial premise hint")
    parser.add_argument(
        "--generate-seeds",
        action="store_true",
        help="Generate seed options through the configured writer model",
    )
    args = parser.parse_args()
    run_wizard(args)


if __name__ == "__main__":
    main()
