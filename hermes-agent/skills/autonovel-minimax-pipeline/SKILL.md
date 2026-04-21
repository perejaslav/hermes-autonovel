---
name: autonovel-minimax-pipeline
description: Use when operating, debugging, or extending the autonovel project with Hermes Agent, especially running MiniMax-powered foundation, drafting, revision, export, or VPS-safe pipeline steps.
---

# Autonovel MiniMax Pipeline

## Core Principle

Advance the novel pipeline one verified step at a time. Use MiniMax-only configuration, keep optional heavy outputs disabled by default, and stop on the first concrete failure.

## Required Checks

Before running generation or evaluation:

1. Verify the current directory is the `autonovel` repo.
2. Read `.env`, `state.json`, `seed.txt`, and `README.md` or `WORKFLOW.md` as needed.
3. Confirm `.env` contains:

```bash
MINIMAX_API_KEY=<set>
MINIMAX_API_BASE_URL=https://api.minimax.io/anthropic
```

Do not introduce non-MiniMax provider env vars, base URLs, or model defaults.

## Safe Command Order

Use this order on a small VPS:

```bash
uv sync --frozen
uv run python run_pipeline.py --phase foundation
uv run python run_pipeline.py --phase drafting
uv run python run_pipeline.py --phase revision --max-cycles 3
uv run python run_pipeline.py --phase export
```

Use `uv run python run_pipeline.py --from-scratch` only when `seed.txt` exists and the run should start fresh.

## Phase Verification

After `foundation`, verify:

- `world.md` exists and is not empty.
- `characters.md` exists and is not empty.
- `outline.md` exists and contains chapter headings.
- `canon.md` exists and is not empty.
- `state.json` advanced or contains useful failure state.

After `drafting`, verify:

- `chapters/ch_*.md` exists.
- Recent chapters are not tiny placeholders.
- `results.tsv` or `eval_logs/` changed.

After `revision`, verify:

- `edit_logs/` or `eval_logs/` contains new logs.
- `briefs/` contains generated briefs when revisions were requested.
- Modified chapters still exist and are readable.

After `export`, verify:

- `manuscript.md` exists if chapters exist.
- `typeset/chapters_content.tex` is optional.
- PDF generation may be skipped when `tectonic` is unavailable.

## VPS-Safe Defaults

Assume Ubuntu VPS with 2 GB RAM:

- Run text pipeline first.
- Do not run `gen_art.py` unless `FAL_KEY` is configured and the user asks.
- Do not run `gen_audiobook.py` unless `ELEVENLABS_API_KEY` is configured and the user asks.
- Do not pass `--with-deep-review` unless the manuscript is complete and the user asks.
- Avoid starting multiple long-running API jobs at the same time.

## Failure Handling

If a command fails:

1. Read stderr and the relevant log file.
2. Identify the missing input, bad env var, parse failure, or failed external tool.
3. Fix the smallest local issue.
4. Re-run the failed command only.
5. Do not continue to the next phase until the expected output is verified.

Common fixes:

- Missing `seed.txt`: create or ask for a seed concept.
- Foundation generator creates empty output: inspect MiniMax key/base URL and rerun that generator.
- `reader_panel.py` fails: run `uv run python build_arc_summary.py` first.
- Export PDF fails: skip PDF unless `tectonic` is installed; keep text export.

## Reporting

After each work unit, report:

```text
Command: <command>
Result: <success/failure>
Verified: <files checked>
Changed: <files changed>
Next: <next safe command>
```

Keep reports short. Include exact failing command and error summary when blocked.
