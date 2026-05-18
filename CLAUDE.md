# peek — contributor context

A Claude Code plugin: `/peek` reads another Claude Code session's JSONL
transcript at `~/.claude/projects/<slug>/<uuid>.jsonl` and emits a markdown
digest into the calling session's context.

## Repo layout

```
peek/
├── .claude-plugin/marketplace.json   declares the plugin to CC's marketplace loader
├── plugins/peek/                     plugin payload — everything users install
│   ├── .claude-plugin/plugin.json
│   ├── commands/peek.md              /peek slash command (uses ! to inline script output)
│   └── scripts/
│       ├── peek_session.py           thin entry point
│       └── peek/                     actual code, split into modules
│           ├── sessions.py           discovery + resolution + JSONL streaming
│           ├── digest.py             turn extraction + redaction
│           ├── render.py             markdown formatting
│           └── cli.py                argparse + dispatch
├── README.md                         user-facing docs
└── CLAUDE.md                         this file
```

`${CLAUDE_PLUGIN_ROOT}` in `commands/peek.md` resolves at runtime to the
cached payload dir at `~/.claude/plugins/cache/peek/peek/<version>/`.

## Constraints

- **Python 3.7+, stdlib only.** No pip dependencies — users get this via
  `/plugin install`, not `pip install`.
- **Keep each module under ~160 lines.** If a module grows past that, split.
- **No emojis** in code or output.
- **stdout is the digest** — downstream may parse it. Don't print debug
  chatter there.

## JSONL format notes (learned by inspection — not formally documented)

Each line is one event with a `type` field.

- **Real user prompt:** `type: user`, `message.content` is a **string**.
- **Tool result:** `type: user`, `message.content` is a **list** of `tool_result` blocks.
- **Assistant:** `type: assistant`, `message.content` is a list of blocks with
  `type: text | thinking | tool_use`. `thinking` blocks are skipped.
- **Metadata types** (skipped or used selectively): `ai-title`, `last-prompt`,
  `permission-mode`, `file-history-snapshot`, `attachment`, `system`.
- **Sidechains:** `isSidechain: true` marks subagent activity. Filtered by
  default; included with `--full`.
- **Sentinel "user" messages from the CC harness — NOT real prompts.** Currently
  filtered in `digest.build_turns`:
  - `<command-name>...</command-name>` — slash commands like `/clear`
  - `<local-command-caveat>...` — appears after a `!`-prefixed shell command
- **Project slugs** (`~/.claude/projects/<slug>/`) replace `/` with `-` and are
  ambiguous when a path component contains `-`. Always prefer the real `cwd`
  from event data; fall back to `decode_slug` only as a last resort.

## Testing

No formal test suite — testing is done against real sessions in
`~/.claude/projects/`. Useful invocations:

```
python3 plugins/peek/scripts/peek_session.py --limit 5
python3 plugins/peek/scripts/peek_session.py <prefix> --turns 5 --tools
python3 plugins/peek/scripts/peek_session.py <prefix> --redact   # verify secret patterns
python3 plugins/peek/scripts/peek_session.py <prefix> --full     # max verbosity sanity check
```

Add a formal test suite when there's a real regression to lock down.

## Common iteration patterns

- **New JSONL event type observed.** Decide if it's a turn boundary, an
  assistant output worth showing, or noise. Add handling in `digest.build_turns`.
- **New harness sentinel in user messages.** Add to the `startswith` checks
  near the top of the `user`/string branch in `digest.build_turns`.
- **New output format / new flag.** Touch `render.py` for formatting and
  `cli.py` for the flag — don't reach into digest internals from CLI code.

## What's deliberately not here

- **`/tail`** (continuous monitoring) — planned as a *separate* `tail` plugin
  in this same marketplace so it gets bare `/tail` shorthand. Deferred until
  `/peek`-repeatedly proves annoying in real use.
- **Tests.** Add when we have a real bug to regress.
- **Cross-platform support.** Tested on macOS/Linux. Windows untested — the
  slash command body invokes `python3` explicitly, which isn't always present
  on Windows by default.

## How the plugin loader works (for debugging install issues)

1. `/plugin marketplace add jimmypocock/peek` clones the repo to
   `~/.claude/plugins/marketplaces/peek/`.
2. CC reads `.claude-plugin/marketplace.json`, finds the `peek` plugin entry
   with `source: ./plugins/peek`.
3. `/plugin install peek@peek` copies `plugins/peek/` to
   `~/.claude/plugins/cache/peek/peek/<version>/` and registers the install
   in `~/.claude/plugins/installed_plugins.json`.
4. CC reads `commands/peek.md` from the cached payload and registers
   `/peek:peek` (collapses to `/peek` because plugin name matches command name).

Known install gotcha: source paths like `.` or `./plugin` get rejected on
older CC versions with "source type your Claude Code version does not support."
The proven pattern is `./plugins/<plugin-name>` (matches what the official
marketplace uses).
