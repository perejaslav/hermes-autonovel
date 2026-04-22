# Hermes Autonovel Project Dossier

This file records the current factual state of the project. It is an internal
orientation document for future work and does not replace `README.md`.

## Purpose

Hermes Autonovel is a Python 3.12 project for autonomous long-form fiction
production. The system starts from a seed concept, builds foundation documents,
drafts chapters, evaluates quality, revises the manuscript, and can export
print, EPUB, landing-page, art, and audiobook artifacts.

The architecture is built around five co-evolving story layers:

- `voice.md`: style, prose guardrails, and novel-specific voice.
- `world.md`: world bible, setting, speculative rules, history, factions.
- `characters.md`: character registry, arcs, motives, speech patterns.
- `outline.md`: chapter-by-chapter structure and foreshadowing.
- `chapters/ch_*.md`: actual prose.
- `canon.md`: cross-cutting hard facts and consistency constraints.

The reusable framework is documented in `README.md`, `PIPELINE.md`,
`WORKFLOW.md`, `program.md`, `CRAFT.md`, `ANTI-SLOP.md`, and
`ANTI-PATTERNS.md`. The generated or story-specific state currently describes
the novel `The Keeper's Warning`.

## Current Manuscript State

- Working directory: `C:\Users\immor\github2\hermes-autonovel`.
- Git branch: `main`, tracking `origin/main`.
- Git status at inspection time: clean.
- Project package: `autonovel`, version `0.1.0`.
- Python requirement: `>=3.12`.
- Current seed: a retired lighthouse keeper on a small Scottish island finds a
  message in a bottle predicting a shipwreck, with the only survivor being
  someone they know.
- Current novel title found in `outline.md`: `The Keeper's Warning`.
- Current pipeline phase in `state.json`: `revision`.
- `state.json` reports `chapters_drafted: 28`, `chapters_total: 0`,
  `revision_cycle: 0`, `novel_score: 0.0`.
- Actual chapter files: 28 files under `chapters/`.
- Actual manuscript word count from `chapters/ch_*.md`: approximately 80,474
  words.
- `results.tsv` records accepted chapter drafts and discarded attempts through
  chapter 28. Accepted chapter scores are mostly in the 6.0 to 7.5 range.

The project appears to have completed a first full draft and is positioned for
revision rather than final release.

## Project Map

Top-level framework and guidance:

- `README.md`: public project overview and quick start.
- `PIPELINE.md`: detailed automation specification and production lessons.
- `WORKFLOW.md`: command-oriented guide for running phases manually.
- `program.md`: agent instructions and layer propagation rules.
- `CRAFT.md`: craft guidance for plot, character, world, and prose.
- `ANTI-SLOP.md`: word-level and prose-pattern AI slop detection rules.
- `ANTI-PATTERNS.md`: structural AI writing pattern warnings.

Core pipeline and shared code:

- `_api_adapter.py`: unified model adapter for Hermes Agent request files,
  GLM/Z.AI, and OpenAI-compatible endpoints.
- `autonovel_utils.py`: shared file, JSON, chapter discovery, and title helpers.
- `run_pipeline.py`: phase orchestrator for foundation, drafting, revision, and
  export.
- `state.json`: current pipeline state.
- `results.tsv`: tabular log of keep/discard outcomes.
- `tests/test_smoke.py`: small smoke test suite for adapter and utilities.
- `book_config.json`: default book-facing config; currently Russian interactive
  foundation defaults.
- `foundation_wizard.py`: interactive setup for early creative decisions.
- `audit_project.py`: non-mutating state/manuscript audit.

Story foundation:

- `seed.txt`: current story seed.
- `voice.md`: global prose guardrails plus voice section.
- `world.md`: world bible for Torran and the Reading system.
- `characters.md`: character registry.
- `outline.md`: chapter outline for `The Keeper's Warning`.
- `canon.md`: hard facts database.
- `MYSTERY.md`: author-only central mystery notes.

Manuscript and exports:

- `chapters/ch_01.md` through `chapters/ch_28.md`: current chapter draft.
- `novel.pdf`: existing PDF artifact at repository root.
- `typeset/`: TeX and EPUB build scripts, templates, and generated EPUB
  structure.
- `landing/index.html`: landing-page artifact/template.

Hermes agent support:

- `hermes-agent/system-prompt.md`: agent prompt.
- `hermes-agent/skills/autonovel-hermes-pipeline/SKILL.md`: VPS-safe protocol
  for operating the Hermes-oriented pipeline.

## Pipeline Phases

Foundation:

- Inputs: `seed.txt`, craft/rule documents, optional existing layer files.
- Tools: `gen_world.py`, `gen_characters.py`, `gen_outline.py`,
  `gen_outline_part2.py`, `gen_canon.py`, `voice_fingerprint.py`,
  `evaluate.py --phase=foundation`.
- Intended output: populated world, characters, outline, canon, mystery, and
  voice identity.
- Exit target from docs: `foundation_score > 7.5` and lore score above target.

Drafting:

- Inputs: foundation documents plus adjacent chapter context.
- Tools: `draft_chapter.py`, `run_drafts.py`, `evaluate.py --chapter=N`.
- Intended behavior: draft sequential chapters, score them, keep chapters above
  threshold, discard/retry weaker attempts, and log outcomes to `results.tsv`.
- Current evidence: 28 accepted chapter files and draft logs exist.

Revision:

- Inputs: completed chapters, evaluation logs, reader-panel output, cut reports,
  and revision briefs.
- Tools: `adversarial_edit.py`, `apply_cuts.py`, `reader_panel.py`,
  `compare_chapters.py`, `review.py`, `gen_brief.py`, `gen_revision.py`,
  `build_arc_summary.py`, `build_outline.py`, `evaluate.py --full`.
- Intended behavior: remove over-explanation and redundancy, generate reader
  feedback, revise weak chapters, detect score plateaus, and optionally run the
  deep model review loop.
- Current evidence: `state.json` says `revision`, but no populated `eval_logs`,
  `edit_logs`, or `briefs` were visible during inspection.

Export:

- Inputs: revised chapters and metadata.
- Tools: `typeset/build_tex.py`, `typeset/build_epub.py`,
  `gen_cover_composite.py`, `gen_cover_print.py`, optional `tectonic`, optional
  `pandoc`.
- Intended output: manuscript, PDF, EPUB, cover outputs, and landing page.
- Current evidence: a root-level `novel.pdf` exists, and `typeset/EPUB`,
  `typeset/epub_build`, and `typeset/epub_out` exist. Metadata and landing page
  still contain placeholders or old-novel references.

## CLI Tool Map

Foundation and drafting:

- `seed.py`: generate seed concepts.
- `gen_world.py`: generate or update `world.md`.
- `gen_characters.py`: generate or update `characters.md`.
- `gen_outline.py`: generate chapter outline.
- `gen_outline_part2.py`: append foreshadowing ledger.
- `gen_canon.py`: generate hard-fact canon.
- `voice_fingerprint.py`: analyze chapters and voice patterns.
- `draft_chapter.py`: write one chapter.
- `run_drafts.py`: batch chapter drafting helper.

Evaluation and revision:

- `evaluate.py`: mechanical slop scanner plus LLM judge for foundation,
  chapters, or full manuscript.
- `adversarial_edit.py`: generate chapter cut suggestions.
- `apply_cuts.py`: apply selected cut classes to chapter text.
- `compare_chapters.py`: head-to-head chapter comparison tournament.
- `reader_panel.py`: multi-persona manuscript-level evaluation.
- `review.py`: deep model review and review parsing.
- `gen_brief.py`: generate revision briefs from panel, eval, cuts, or auto mode.
- `gen_revision.py`: rewrite a chapter from a brief.
- `build_arc_summary.py`: summarize chapter arcs.
- `build_outline.py`: rebuild outline from chapters.

Art, cover, audiobook, and export:

- `gen_art.py`: style, curate, pick, ornaments, vectorization, and art pipeline.
- `gen_art_directions.py`: generate art directions.
- `gen_cover_composite.py`: overlay title/author on cover art.
- `gen_cover_print.py`: produce print-ready full-wrap cover.
- `gen_audiobook_script.py`: parse chapters into speaker-attributed scripts.
- `gen_audiobook.py`: generate and assemble ElevenLabs audiobook audio.
- `typeset/build_tex.py`: convert chapter Markdown into LaTeX content.
- `typeset/build_epub.py`: build EPUB3 from Markdown/XHTML assets.

## External Dependencies and APIs

Python dependencies declared in `pyproject.toml`:

- `httpx>=0.28.1`
- `python-dotenv>=1.2.2`

Model/API providers:

- Hermes Agent: default provider via `AUTONOVEL_PROVIDER=agent`. The project
  writes request files under `.autonovel/agent_requests/`; Hermes answers them
  with its current selected model and writes response JSON.
- GLM/Z.AI: optional provider selected by `AUTONOVEL_PROVIDER=glm`, with
  `GLM_API_KEY` and `GLM_BASE_URL`.
- OpenAI-compatible: optional provider selected by
  `AUTONOVEL_PROVIDER=openai_compatible`, with `MODEL_API_KEY` and
  `MODEL_API_BASE_URL`.
- fal.ai: optional art generation via `FAL_KEY`.
- ElevenLabs: optional audiobook generation via `ELEVENLABS_API_KEY`.

External command-line tools:

- `uv`: intended package runner from the docs.
- `pandoc`: required by `typeset/build_epub.py` for Markdown to XHTML.
- `tectonic`: optional PDF typesetting path from `run_pipeline.py`.
- `git`: used by the orchestrator for keep/discard commits and state tracking.

Environment/config knobs:

- `AUTONOVEL_WRITER_MODEL`
- `AUTONOVEL_JUDGE_MODEL`
- `AUTONOVEL_REVIEW_MODEL`
- `AUTONOVEL_TITLE`
- `AUTONOVEL_AUTHOR`
- `AUTONOVEL_PROVIDER`
- `AUTONOVEL_LANGUAGE`
- `AUTONOVEL_AGENT_REQUEST_DIR`
- `AUTONOVEL_AGENT_RESPONSE_FILE`
- `AUTONOVEL_API_BASE_URL`

No secrets are recorded in this document.

## Artifact State

Manuscript:

- 28 chapter files exist under `chapters/`.
- Total current chapter word count is approximately 80,474 words.
- Chapter headings are inconsistent: some files begin with Markdown chapter
  headings, while others begin directly with prose.

PDF/TeX:

- `novel.pdf` exists at repository root.
- `typeset/novel.tex` exists as the TeX template.
- `typeset/build_tex.py` generates `typeset/chapters_content.tex` from current
  chapters.

EPUB:

- `typeset/build_epub.py` exists.
- `typeset/EPUB`, `typeset/epub_build`, and `typeset/epub_out` exist.
- `typeset/epub_metadata.yaml` still contains placeholder metadata:
  `TITLE`, `AUTHOR`, `Publisher Name`.
- EPUB cover metadata points at `../art/epub_front_cover.png`; art assets were
  not observed in the top-level directory listing.

Landing page:

- `landing/index.html` exists.
- The page title still references `The Second Son of the House of Bells`, not
  `The Keeper's Warning`.
- The page references `cover_bg.png`; asset presence was not confirmed during
  inspection.

Logs and revision artifacts:

- `results.tsv` exists and records chapter draft attempts.
- `eval_logs`, `edit_logs`, and `briefs` did not show visible contents during
  inspection, despite `state.json` being in the `revision` phase.

## Known Issues and Risks

- `_api_adapter.py` uses provider-neutral configuration for model API fallback.
- `README.md` and `WORKFLOW.md` recommend `uv run python ...`, but `uv run
  python -m unittest tests.test_smoke` currently fails before tests run because
  `uv` cannot initialize its cache at
  `C:\Users\immor\AppData\Local\uv\cache` with `os error 183`.
- `python` is not available in PATH, so `python -m unittest tests.test_smoke`
  cannot be run directly in the current shell.
- `state.json` has `chapters_total: 0` while 28 chapter files exist and
  `chapters_drafted` is 28.
- The project is on `main`, not on a per-novel branch, even though the docs
  describe per-novel branches as the expected workflow.
- `landing/index.html` appears to be from the earlier Bells production, not the
  current `The Keeper's Warning` manuscript.
- `typeset/epub_metadata.yaml` contains placeholder title and author values.
- Story files contain suspicious text fragments such as `Aul迆` and `Mar罐`.
  These may be encoding corruption or model-output artifacts and should be
  reviewed before export.
- `world.md` appears to include a fenced JSON wrapper around Markdown content,
  while other story files are plain Markdown. Confirm whether this is intended.
- Chapter headings are inconsistent, which may affect export scripts and reader
  experience.
- `main.py` is a placeholder that prints `Hello from autonovel!`; operational
  entry points are the individual scripts and `run_pipeline.py`.
- Optional heavy outputs, especially art and audiobook generation, require
  external API keys and may be expensive.

## Recommended Next Steps

1. Fix the local execution environment first:
   - make a Python 3.12 executable available to the shell, or identify the
     interpreter path `uv` should use;
   - repair or remove the broken `uv` cache path;
   - rerun the smoke tests.

2. Reconcile smoke tests and adapter compatibility:
   - decide whether `_api_adapter.py` should expose `BASE_URL` for backward
     compatibility or whether `tests/test_smoke.py` should assert
     provider-neutral model API configuration.

3. Normalize current pipeline state:
   - set or infer `chapters_total: 28`;
   - decide whether revision should start at cycle 1 with fresh `eval_logs`,
     `edit_logs`, and `briefs`.

4. Run a non-destructive manuscript audit before revision:
   - scan for suspicious Unicode artifacts such as `Aul迆` and `Mar罐`;
   - check chapter heading consistency;
   - confirm `world.md` format.

5. Start revision with the smallest verified loop:
   - run full evaluation once;
   - generate reader-panel or adversarial-edit logs;
   - create briefs for the highest-confidence issues;
   - revise one chapter at a time and verify after each change.

6. Defer export polish until after revision:
   - update EPUB metadata;
   - regenerate TeX/EPUB from normalized chapters;
   - replace the old landing page references with `The Keeper's Warning`;
   - verify `novel.pdf` corresponds to the current manuscript.

## Verification Notes

Commands attempted during inspection:

- `git status --short --branch`: clean `main...origin/main`.
- Chapter count and word count: 28 chapters, approximately 80,474 words.
- `Get-Content state.json`: phase is `revision`.
- `uv run python -m unittest tests.test_smoke`: blocked before test execution by
  `uv` cache initialization failure.
- `python -m unittest tests.test_smoke`: blocked because `python` is not found
  in PATH.

This document intentionally does not modify source code, story content,
pipeline state, generated artifacts, or test expectations.
