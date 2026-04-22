---
name: autonovel-hermes-pipeline
description: Use when operating, debugging, or extending the autonovel project with Hermes Agent, especially running Hermes-native foundation, drafting, revision, export, or VPS-safe pipeline steps.
---

# Autonovel Hermes Pipeline

## Core Principle

Advance the novel pipeline one verified step at a time. Prefer Hermes Agent's current selected model via `AUTONOVEL_PROVIDER=agent`, keep optional heavy outputs disabled by default, and stop on the first concrete failure.

## Required Checks

Before running generation or evaluation:

1. Verify the current directory is the `autonovel` repo.
2. Read `.env`, `state.json`, `seed.txt`, and `README.md` or `WORKFLOW.md` as needed.
3. Confirm `.env` contains for Hermes-native runs:

```bash
AUTONOVEL_PROVIDER=agent
AUTONOVEL_LANGUAGE=ru
AUTONOVEL_AGENT_REQUEST_DIR=.autonovel/agent_requests
```

Do not hard-code model names in scripts. API providers are fallback modes only.

## Safe Command Order

Use this order on a small VPS:

```bash
uv sync --frozen
uv run python foundation_wizard.py
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
- Missing `book_config.json`: run `uv run python foundation_wizard.py`.
- In `AUTONOVEL_PROVIDER=agent` mode, a model call creates `.autonovel/agent_requests/*.request.json` and stops. Answer that request with the current Hermes model, write JSON `{"content": "..."}` to the requested response path, then rerun with `AUTONOVEL_AGENT_RESPONSE_FILE=<response path>`.
- Foundation generator creates empty output: inspect provider configuration and rerun that generator.
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
