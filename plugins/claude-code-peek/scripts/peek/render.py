"""Markdown rendering — turn lists, session digests, and small text helpers."""

from datetime import datetime
from typing import List, Optional

from peek.digest import ToolCall, Turn, redact
from peek.sessions import SessionSummary, short_id


# --- text helpers ------------------------------------------------------------

def human_age(mtime: float, now: Optional[float] = None) -> str:
    delta = (now if now is not None else datetime.now().timestamp()) - mtime
    if delta < 60:
        return f"{int(delta)}s ago"
    if delta < 3600:
        return f"{int(delta / 60)}m ago"
    if delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"


def truncate(text: str, limit: int) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --- formatters --------------------------------------------------------------

def format_list(sessions: List[SessionSummary], header: str = "Recent sessions") -> str:
    if not sessions:
        return "No sessions found."
    lines = [f"## {header}", ""]
    for s in sessions:
        teaser = s.title or s.last_prompt or "(no title)"
        lines.append(
            f"- `{short_id(s.session_id)}`  {human_age(s.mtime):>6}  `{s.project_path}`"
        )
        lines.append(f"      {truncate(teaser, 120)}")
    return "\n".join(lines)


def format_turn(turn: Turn, idx: int, full: bool, show_tools: bool, do_redact: bool):
    """Render one turn. Returns (markdown, redact_count)."""
    redact_count = 0

    def rd(text: str) -> str:
        nonlocal redact_count
        if not do_redact:
            return text
        out, c = redact(text)
        redact_count += c
        return out

    out = []
    ts = turn.timestamp[:19].replace("T", " ") if turn.timestamp else ""
    out.append(f"### Turn {idx} — {ts}")
    user_limit = 5000 if full else 500
    out.append(f"**User:** {truncate(rd(turn.user_text), user_limit)}")

    for blk in turn.assistant_blocks:
        if isinstance(blk, str):
            text = rd(blk)
            if not full:
                text = truncate(text, 600)
            out.append(f"**Assistant:** {text}")
        elif isinstance(blk, ToolCall):
            if not (show_tools or blk.is_error):
                continue
            marker = " [error]" if blk.is_error else ""
            out.append(f"  - `{blk.name}`{marker} {truncate(blk.summary, 100)}")
            if blk.is_error and blk.result_excerpt:
                excerpt = truncate(rd(blk.result_excerpt), 400)
                out.append(f"    ```\n    {excerpt}\n    ```")
    return "\n".join(out), redact_count


def format_digest(summary: SessionSummary, turns: List[Turn], n: int, full: bool,
                  show_tools: bool, do_redact: bool) -> str:
    out = [
        f"# Peek: `{short_id(summary.session_id)}` — {summary.project_path}",
        f"_{human_age(summary.mtime)} · {summary.title or '(no title)'}_",
        f"_File: `{summary.path}`_",
        "",
    ]
    shown = turns[-n:]
    start = len(turns) - len(shown) + 1
    if len(turns) > n:
        out.append(f"_Showing last {n} of {len(turns)} turns. "
                   f"Use `--turns N` for more, `--full` for verbose._")
        out.append("")

    total_redactions = 0
    for i, turn in enumerate(shown, start=start):
        text, c = format_turn(turn, i, full, show_tools, do_redact)
        total_redactions += c
        out.append(text)
        out.append("")

    if do_redact and total_redactions:
        out.append(f"_Redacted {total_redactions} secret-shaped strings._")
    return "\n".join(out)
