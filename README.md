# peek

`/peek` at another Claude Code session from inside the one you're in.

You run 5–10 Claude Code sessions in parallel. Session A built a tool, session B is testing it. To get B's results into A you'd normally switch panes, scroll, copy, paste. `/peek` lets the assistant in A pull a clean digest of B's recent activity into A's context directly.

```
> /peek spotify
```

```
# Peek: 67034089 — /Users/you/Projects/spotify-playlist-maker
1d ago · Create Spotify app integration

### Turn 65 — 2026-05-17 00:59:53
User: ... openers should be on the concert playlist too ...
Assistant: ... extending the CLI to take multiple setlist artists ...
  - Edit [error] .claude/skills/playlist/SKILL.md
    ```
    String to replace not found in file. ...
    ```

### Turn 66 — 2026-05-17 01:04:29
...
```

## What it shows

By default `/peek` keeps the parts of a session that are useful for reasoning about it and drops the rest.

| Kept | Dropped |
|---|---|
| User prompts | File-read dumps (Read tool results) |
| Assistant text replies | Successful bash output bodies |
| Tool calls **that errored** + an excerpt of the error | Verbose tool input JSON |
| | `thinking` blocks |
| | Hook output, system events, attachments |
| | Sidechain (subagent) activity (use `--full` to include) |

Add `--tools` to include all tool call summaries. Add `--full` for no truncation + sidechains.

## Install

In any Claude Code session:

```
/plugin marketplace add jimmypocock/peek
/plugin install peek@peek
```

Restart Claude Code. After that, `/peek` works in every session, every project.

Under the hood: `marketplace add` clones this repo into `~/.claude/plugins/marketplaces/peek/`, `install` caches it at `~/.claude/plugins/cache/peek/peek/<version>/`, and the plugin gets registered in `~/.claude/settings.json` under `enabledPlugins`.

To pick up new upstream changes later: `/plugin update peek@peek`.

## Development setup

For working on this plugin locally without pushing + `/plugin update` on every change, replace the install cache with a symlink to your working clone:

```bash
git clone https://github.com/jimmypocock/peek.git ~/Projects/peek
# Install via the slash commands above first, then symlink the cached install
# at the plugin payload subdirectory (not the repo root):
INSTALL=~/.claude/plugins/cache/peek/peek/0.1.0
rm -rf "$INSTALL"
ln -s ~/Projects/peek/plugins/peek "$INSTALL"
```

Edits in `~/Projects/peek/plugins/peek/` take effect on the next `/peek` invocation in any session — no reinstall needed.

Run the parser directly to iterate quickly:

```bash
python3 plugins/peek/scripts/peek_session.py --limit 5
python3 plugins/peek/scripts/peek_session.py spotify --turns 3 --tools
```

Requires Python 3.9+. No dependencies outside the stdlib.

## Usage

```
/peek                          # list 10 most-recent sessions across all projects
/peek <uuid>                   # show a session by full UUID
/peek 67034089                 # show by short prefix
/peek spotify                  # fuzzy match on project slug, then title/prompt
/peek --project                # list only sessions for the current cwd
/peek <target> --turns 20      # show last 20 turns instead of 10
/peek <target> --full          # no truncation, include sidechain activity
/peek <target> --tools         # include tool call summaries (errors always shown)
/peek <target> --redact        # mask common secret patterns (sk-, ghp_, AKIA, xox*)
```

The slash command forwards arguments to `scripts/peek_session.py`, which is also runnable standalone:

```
python3 plugins/peek/scripts/peek_session.py spotify --turns 5
```

## Secrets in session logs

Claude Code session JSONLs live in `~/.claude/projects/` and are owned by your user account. Anything that ever passed through a Claude Code session — including secrets pasted into prompts or printed by tool calls — sits there in plaintext on disk.

`/peek` does **not** redact by default. The reasoning: your session files are already plaintext on your own machine, and aggressive default redaction creates a false sense of security while sometimes hiding things you actually want to see. If you're peeking output that you intend to share, pass `--redact` to mask common token patterns (`sk-…`, `ghp_…`, `AKIA…`, `xox[bapsr]-…`).

The real fix is to avoid pasting secrets into prompts in the first place.

## How it works

Each Claude Code session writes append-only JSONL to `~/.claude/projects/<slug>/<uuid>.jsonl`. The slug is the cwd with `/` replaced by `-`. Each line is one event: a user prompt, an assistant message (with content blocks for text / `thinking` / tool calls), a tool result, a system event, etc.

`peek_session.py`:
1. Walks `~/.claude/projects/` and reads the tail of each `.jsonl` to grab the most recent `ai-title`, `last-prompt`, and `cwd` — fast enough for hundreds of sessions.
2. Resolves a `target` argument as exact UUID → short prefix → fuzzy project-slug → fuzzy title/prompt text.
3. Streams the full JSONL for the selected session and groups events into "turns" (one real user prompt + the assistant work that followed).
4. Emits markdown to stdout.

The slash command (`commands/peek.md`) executes the script with `!` and inlines the output into the prompt, so the assistant in the calling session sees the digest as context.

## Limitations

- Project paths come from `cwd` events inside the JSONL (with a head-of-file fallback for short sessions). Only if a session has *no* `cwd` event at all do we fall back to slug decoding, which is ambiguous when a path component contains `-` (e.g. `claude-code/peek` vs `claude/code/peek`).
- The JSONL format is stable in practice but not formally documented. New event types are skipped silently.
- `/tail` (continuous monitoring) is not implemented yet. Likely lands as a separate `tail` plugin in this same marketplace, so it gets `/tail` as a bare shorthand.

## Related / prior art

- [Anthropic Agent View](https://code.claude.com/docs/en/agent-view) (`claude agents`) — TUI dashboard of running sessions; deliberately hides transcripts. Doesn't cover the in-session peek use case.
- [delexw/claude-code-trace](https://github.com/delexw/claude-code-trace) — desktop / web / TUI viewer for JSONLs.
- [simonw/claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) — JSONL → static HTML.
- [jtklinger/claude-session-viewer](https://github.com/jtklinger/claude-session-viewer) — CLI parser, exports to markdown files.

`peek` is narrower than any of those: it's a slash command intended to be invoked by one Claude Code session to read another, with output sized for an LLM context rather than a human dashboard.

## License

MIT
