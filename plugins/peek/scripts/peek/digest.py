"""Build per-turn digests from a session JSONL, and redact secrets on request.

A "turn" is one real user prompt plus all the assistant work that followed,
until the next real user prompt.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Union

from peek.sessions import iter_events

# Secret patterns redacted only when --redact is passed.
SECRET_PATTERNS = [
    re.compile(r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"gho_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
]


@dataclass
class ToolCall:
    name: str
    summary: str
    is_error: bool = False
    result_excerpt: Optional[str] = None


@dataclass
class Turn:
    user_text: str
    timestamp: Optional[str]
    assistant_blocks: list = field(default_factory=list)  # List[Union[str, ToolCall]]


# --- tool input / result helpers ---------------------------------------------

def summarize_tool_input(name: str, inp: dict) -> str:
    """One-line teaser of tool arguments."""
    if not inp:
        return ""
    if name == "Bash":
        return inp.get("command", "")
    if name in ("Read", "Edit", "Write", "NotebookEdit"):
        return inp.get("file_path") or inp.get("notebook_path") or ""
    if name in ("Grep", "Glob"):
        return inp.get("pattern", "")
    if name == "WebFetch":
        return inp.get("url", "")
    if name == "WebSearch":
        return inp.get("query", "")
    if name == "Task":
        return inp.get("description") or inp.get("subagent_type") or ""
    return json.dumps(inp)[:120]


def extract_result_text(content: Union[str, list, None]) -> Tuple[str, bool]:
    """Pull plaintext + is_error out of a tool_result.content payload."""
    is_error = False
    if isinstance(content, str):
        return content, is_error
    if isinstance(content, list):
        parts = []
        for blk in content:
            if isinstance(blk, dict):
                if blk.get("type") == "text":
                    parts.append(blk.get("text", ""))
                elif blk.get("type") == "tool_result":
                    if blk.get("is_error"):
                        is_error = True
                    sub, sub_err = extract_result_text(blk.get("content"))
                    parts.append(sub)
                    is_error = is_error or sub_err
            elif isinstance(blk, str):
                parts.append(blk)
        return "\n".join(parts), is_error
    return "", is_error


# --- turn extraction ---------------------------------------------------------

def build_turns(path: Path, include_sidechains: bool = False) -> List[Turn]:
    """Group events into turns from a session JSONL."""
    turns: List[Turn] = []
    current: Optional[Turn] = None
    pending_tools: dict = {}  # tool_use_id -> ToolCall

    for evt in iter_events(path):
        t = evt.get("type")
        if t not in ("user", "assistant"):
            continue
        if evt.get("isSidechain") and not include_sidechains:
            continue

        msg = evt.get("message") or {}
        content = msg.get("content")
        ts = evt.get("timestamp")

        if t == "user" and isinstance(content, str):
            if current is not None:
                turns.append(current)
            current = Turn(user_text=content, timestamp=ts)

        elif t == "user" and isinstance(content, list):
            for blk in content:
                if not isinstance(blk, dict) or blk.get("type") != "tool_result":
                    continue
                tc = pending_tools.get(blk.get("tool_use_id"))
                if tc is None:
                    continue
                text, is_error = extract_result_text(blk.get("content"))
                if is_error or blk.get("is_error"):
                    tc.is_error = True
                    tc.result_excerpt = text[-600:] if text else None

        elif t == "assistant" and isinstance(content, list):
            if current is None:
                current = Turn(user_text="(no preceding user prompt)", timestamp=ts)
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                btype = blk.get("type")
                if btype == "text":
                    text = (blk.get("text") or "").strip()
                    if text:
                        current.assistant_blocks.append(text)
                elif btype == "tool_use":
                    tc = ToolCall(
                        name=blk.get("name", "?"),
                        summary=summarize_tool_input(blk.get("name", ""), blk.get("input") or {}),
                    )
                    pending_tools[blk.get("id")] = tc
                    current.assistant_blocks.append(tc)
                # "thinking" blocks are intentionally skipped

    if current is not None:
        turns.append(current)
    return turns


# --- redaction ---------------------------------------------------------------

def redact(text: str) -> Tuple[str, int]:
    """Replace common token patterns with [REDACTED]. Returns (text, count)."""
    count = 0

    def sub(_m):
        nonlocal count
        count += 1
        return "[REDACTED]"

    for pat in SECRET_PATTERNS:
        text = pat.sub(sub, text)
    return text, count
