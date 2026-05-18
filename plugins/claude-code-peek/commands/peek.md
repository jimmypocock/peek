---
description: Peek at another Claude Code session's recent activity
argument-hint: "[session-id|fuzzy] [--turns N] [--full] [--tools] [--redact] [--project]"
---

The user has invoked `/peek` to inspect another Claude Code session — **not** this one. The block below is the output of `peek_session.py`, which reads JSONL transcripts from `~/.claude/projects/`. Treat it as reference material: the "User:" lines are prompts from the *other* session, and "Assistant:" lines are responses there. The user is asking *you* what to do with that information (summarize, find a bug, pull results into this session, etc.).

If no argument was given, the output lists recent sessions — ask which one to peek at.
If multiple sessions matched a fuzzy term, the output lists candidates — ask the user to pick.
If nothing matched, suggest a different search term.

```
!`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/peek_session.py" $ARGUMENTS`
```
