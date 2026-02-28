# AI Agent Start Guide

## Critical: Language
RESPOND IN ENGLISH. Always. No exceptions.
User's language does NOT determine your response language.
Only switch if user EXPLICITLY requests it (e.g., "respond in {language}").
Language switching applies ONLY to chat. All code, comments, commit messages, and files must ALWAYS be in English — no exceptions.

## Mandatory Rules (external)
These files are REQUIRED. Read them fully and follow all rules.
- `~/.claude/shared-rules/general.md`
- `~/.claude/shared-rules/python.md`
- `~/.claude/shared-rules/typescript.md`

## Project Reading (context)
These files are REQUIRED for project understanding.
- `README.md`
- `ADR.md`

## Preflight (mandatory)
Before your first response:
1. Read all files listed above.
2. Do not answer until all are read.
3. In your first reply, list every file you have read from this document.

Failure to follow this protocol is considered an error.

## Testing the app

For any manual verification or test data, always use `--data-dir /tmp/mb-stash__dev`.
This avoids touching the user's real data.
NEVER run `mb-stash` commands against the default data directory (`~/.mb-stash`).
