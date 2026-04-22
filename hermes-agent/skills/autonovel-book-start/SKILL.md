---
name: autonovel-book-start
description: Use when the user wants to begin a new autonovel book from chat intent, including phrases like "хочу написать книгу", "начнем новую книгу", or "помоги придумать роман".
---

# Autonovel Book Start

## Core Principle

Turn a plain chat intent into a guided creative intake, then operate the pipeline yourself. The user should answer story questions, not run terminal commands.

## Intent Triggers

Use this skill when the user writes something like:

- "хочу написать книгу"
- "давай начнем новую книгу"
- "помоги придумать роман"
- "у меня нет идеи, но я хочу книгу"

## Chat Workflow

1. Confirm that you will guide the start in chat.
2. Ask only creative questions: genre, emotional tone, audience, rough premise, protagonist, setting, and what the user wants to avoid.
3. If the user has no premise, propose 3-5 Russian-language directions and ask them to choose or combine.
4. Convert the chosen answers into `book_config.json` fields:
   - `premise_hint`
   - `genre`
   - `audience`
   - `tone`
   - `selected_seed`
   - `world_direction`
   - `character_direction`
   - `outline_direction`
5. Build one intake JSON and call `py -3.12 start_book.py --intake - --archive-existing`, piping the JSON through stdin.
6. Treat `start_book.py` as the project command that archives old generated artifacts, writes `seed.txt`, saves `book_config.json`, resets `state.json`, and launches foundation.
7. Summarize `world.md`, `characters.md`, `outline.md`, and `canon.md` in plain Russian.
8. Wait for explicit approval before drafting.
9. After approval, continue with `autonovel-hermes-pipeline` and run drafting autonomously.

## Operating Rules

- Do not ask the user to run commands manually.
- Do not expose internal request/response files unless the pipeline blocks and the response file must be created.
- Keep book-facing content in Russian by default.
- Use Hermes Agent's current selected model through `AUTONOVEL_PROVIDER=agent`.
- Stop after foundation and wait for explicit approval before drafting.
- Use `start_book.py` with stdin for the one-command start path.
- Leave art, audiobook, revision, and export for later explicit requests.

## Config Helper

For a chat-led start, use `foundation_wizard.apply_foundation_answers(...)` to save collected answers without terminal prompts. This keeps the old terminal wizard available while allowing Hermes to prepare the same config programmatically.

## Handoff To Pipeline Skill

After the user approves drafting, continue with `autonovel-hermes-pipeline` rules: run one phase at a time, verify outputs, and stop on concrete failures.
