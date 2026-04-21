#!/usr/bin/env python3
"""
Rebuild outline.md from the actual chapters.
Reads each chapter, calls the LLM for a structured summary,
and assembles into an outline that reflects the novel as-written.
"""
import os
import sys
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from autonovel_utils import BASE_DIR, discover_chapters, parse_json_response, project_title

load_dotenv(BASE_DIR / ".env")

JUDGE_MODEL = os.environ.get("AUTONOVEL_JUDGE_MODEL", "auto")
CHAPTERS_DIR = BASE_DIR / "chapters"

def call_model(prompt, max_tokens=16000):
    from _api_adapter import call_writer as _orig
    return _orig(prompt, max_tokens=max_tokens)

def main():
    # Load supporting docs for context
    characters = (BASE_DIR / "characters.md").read_text()[:3000]
    
    entries = []
    chapters = discover_chapters(BASE_DIR)
    if not chapters:
        raise SystemExit("ERROR: no chapter files found in chapters/")
    
    for ch, path in chapters:
        text = path.read_text()
        wc = len(text.split())
        
        title_line = text.strip().split('\n')[0].lstrip('# ').strip()
        
        prompt = f"""Analyze this chapter and produce a structured outline entry.

CHAPTER {ch}: "{title_line}" ({wc} words)

{text}

Return JSON with these fields:
- "title": the chapter title (string)
- "location": primary setting (string)
- "characters": list of characters who appear (list of strings)
- "summary": 2-3 sentence summary of what happens (string)
- "beats": list of 3-5 key story beats in order (list of strings)
- "try_fail": the try-fail cycle type: "yes-but", "no-and", "yes-and", or "no-but" (string)
- "plants": foreshadowing threads PLANTED in this chapter (list of strings)
- "harvests": foreshadowing threads PAID OFF in this chapter (list of strings)
- "emotional_arc": one sentence describing the emotional movement (string)
- "chapter_question": the question left open at chapter's end (string)

JSON only, no other text."""

        data = parse_json_response(call_model(prompt))
        data["num"] = ch
        data["words"] = wc
        entries.append(data)
        print(f"  {ch:2d}. {title_line} ({wc}w)")
    
    # Build new outline
    lines = []
    lines.append(f"# {project_title(BASE_DIR)}")
    lines.append("## Chapter Outline (reflects actual novel as-written)")
    lines.append("")
    lines.append(f"**{len(entries)} chapters, {sum(e['words'] for e in entries):,} words**")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for e in entries:
        lines.append(f"### Ch {e['num']}: {e['title']}")
        lines.append(f"**{e['words']} words** | **Location:** {e.get('location', 'N/A')}")
        lines.append(f"- **Characters:** {', '.join(e.get('characters', []))}")
        lines.append(f"- **Try-fail cycle:** {e.get('try_fail', 'N/A')}")
        lines.append(f"- **Emotional arc:** {e.get('emotional_arc', 'N/A')}")
        lines.append("")
        lines.append(f"**Summary:** {e.get('summary', 'N/A')}")
        lines.append("")
        lines.append("**Beats:**")
        for b in e.get("beats", []):
            lines.append(f"1. {b}")
        lines.append("")
        if e.get("plants"):
            lines.append("**Plants:**")
            for p in e["plants"]:
                lines.append(f"- {p}")
            lines.append("")
        if e.get("harvests"):
            lines.append("**Harvests:**")
            for h in e["harvests"]:
                lines.append(f"- {h}")
            lines.append("")
        lines.append(f"**Chapter question:** {e.get('chapter_question', 'N/A')}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Foreshadowing ledger
    lines.append("## FORESHADOWING LEDGER")
    lines.append("")
    lines.append("| Thread | Planted | Harvested |")
    lines.append("|--------|---------|-----------|")
    
    # Collect all plants and harvests
    all_plants = {}
    all_harvests = {}
    for e in entries:
        for p in e.get("plants", []):
            key = p[:60]
            if key not in all_plants:
                all_plants[key] = []
            all_plants[key].append(e["num"])
        for h in e.get("harvests", []):
            key = h[:60]
            if key not in all_harvests:
                all_harvests[key] = []
            all_harvests[key].append(e["num"])
    
    # Match plants to harvests by keyword overlap
    all_threads = set(list(all_plants.keys()) + list(all_harvests.keys()))
    for thread in sorted(all_threads):
        planted = ", ".join(f"Ch {n}" for n in all_plants.get(thread, []))
        harvested = ", ".join(f"Ch {n}" for n in all_harvests.get(thread, []))
        lines.append(f"| {thread} | {planted} | {harvested} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Outline rebuilt from actual chapters, Cycle 5.*")
    
    out = '\n'.join(lines)
    (BASE_DIR / "outline.md").write_text(out)
    print(f"\nSaved outline.md ({len(out.split())} words)")

if __name__ == "__main__":
    main()
