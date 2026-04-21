"""Shared lightweight helpers for the autonovel command-line tools."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent


class MissingInputError(RuntimeError):
    """Raised when a pipeline step is missing a required input file."""


def read_required_file(path: Path, label: str, min_chars: int = 1) -> str:
    """Read a required text file and fail with an actionable error."""
    if not path.exists():
        raise MissingInputError(f"Required input missing for {label}: {path}")
    text = path.read_text(encoding="utf-8")
    if len(text.strip()) < min_chars:
        raise MissingInputError(f"Required input empty for {label}: {path}")
    return text


def read_optional_file(path: Path) -> str:
    """Read a text file if present, otherwise return an empty string."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_generated_file(path: Path, content: str, label: str, min_chars: int = 100) -> None:
    """Write generated content, refusing obviously empty model output."""
    if len(content.strip()) < min_chars:
        raise RuntimeError(
            f"Generated {label} is too short ({len(content.strip())} chars); refusing to write {path}"
        )
    path.write_text(content.strip() + "\n", encoding="utf-8")


def strip_markdown_fence(text: str) -> str:
    """Remove a surrounding Markdown code fence when an LLM adds one."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```.*$", "", text, flags=re.DOTALL)
    return text.strip()


def parse_json_response(text: str) -> Any:
    """Extract and parse the first JSON object or array from an LLM response."""
    text = strip_markdown_fence(text)
    starts = [idx for idx in (text.find("{"), text.find("[")) if idx != -1]
    if not starts:
        raise ValueError("No JSON object or array found in response")
    start = min(starts)
    opener = text[start]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == opener:
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1], strict=False)
    return json.loads(text[start:], strict=False)


def discover_chapters(root: Path = BASE_DIR) -> list[tuple[int, Path]]:
    """Return existing chapter files as sorted ``(chapter_number, path)`` pairs."""
    chapters_dir = root / "chapters"
    found: list[tuple[int, Path]] = []
    for path in chapters_dir.glob("ch_*.md"):
        match = re.fullmatch(r"ch_(\d+)\.md", path.name)
        if match:
            found.append((int(match.group(1)), path))
    return sorted(found, key=lambda item: item[0])


def project_title(root: Path = BASE_DIR) -> str:
    """Best-effort title discovery without depending on story-specific names."""
    outline = root / "outline.md"
    if outline.exists():
        for line in outline.read_text(encoding="utf-8").splitlines():
            title = line.strip().lstrip("#").strip()
            if title:
                return title
    chapters = discover_chapters(root)
    if chapters:
        first_line = chapters[0][1].read_text(encoding="utf-8").splitlines()[0]
        title = first_line.strip().lstrip("#").strip()
        if title:
            return title
    return "Untitled Novel"
