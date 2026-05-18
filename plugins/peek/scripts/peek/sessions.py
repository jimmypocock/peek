"""Session discovery, summarization, and resolution.

A session lives at `~/.claude/projects/<project-slug>/<uuid>.jsonl`. The slug is
the cwd with `/` replaced by `-`. Each line of the JSONL is one event.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

PROJECTS_DIR = Path.home() / ".claude" / "projects"
SUMMARY_TAIL_BYTES = 32 * 1024


@dataclass
class SessionSummary:
    session_id: str
    project_slug: str
    project_path: str
    path: Path
    mtime: float
    title: Optional[str] = None
    last_prompt: Optional[str] = None


# --- slug + id helpers -------------------------------------------------------

def decode_slug(slug: str) -> str:
    """Reverse Claude Code's project-dir slugification. Ambiguous when a path
    component naturally contains `-` — caller should prefer the real `cwd`
    from event data when available."""
    if slug.startswith("-"):
        return "/" + slug[1:].replace("-", "/")
    return slug.replace("-", "/")


def slugify_cwd() -> str:
    return "-" + os.getcwd().lstrip("/").replace("/", "-")


def short_id(uuid: str) -> str:
    return uuid.split("-")[0]


# --- JSONL streaming ---------------------------------------------------------

def iter_events(path: Path) -> Iterator[dict]:
    """Yield parsed events from a JSONL file, skipping malformed lines."""
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def iter_tail_lines(path: Path, max_bytes: int = SUMMARY_TAIL_BYTES) -> Iterator[str]:
    """Yield complete lines from approximately the last `max_bytes` of a file."""
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > max_bytes:
            f.seek(size - max_bytes)
            f.readline()  # drop partial leading line
        for raw in f:
            yield raw.decode("utf-8", errors="replace")


# --- discovery ---------------------------------------------------------------

def summarize_session(path: Path) -> SessionSummary:
    """Cheap summary read — only inspects the tail of the file."""
    title, last_prompt, cwd = None, None, None
    for raw in iter_tail_lines(path):
        try:
            evt = json.loads(raw)
        except json.JSONDecodeError:
            continue
        t = evt.get("type")
        if t == "ai-title":
            title = evt.get("aiTitle", title)
        elif t == "last-prompt":
            last_prompt = evt.get("lastPrompt", last_prompt)
        if cwd is None and isinstance(evt.get("cwd"), str):
            cwd = evt["cwd"]
    slug = path.parent.name
    return SessionSummary(
        session_id=path.stem,
        project_slug=slug,
        project_path=cwd or decode_slug(slug),
        path=path,
        mtime=path.stat().st_mtime,
        title=title,
        last_prompt=last_prompt,
    )


def list_sessions(project: Optional[str] = None) -> List[SessionSummary]:
    """Return all sessions (optionally scoped to a project slug), newest first."""
    if not PROJECTS_DIR.exists():
        return []
    out: List[SessionSummary] = []
    for project_dir in PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        if project and project_dir.name != project:
            continue
        for jsonl in project_dir.glob("*.jsonl"):
            try:
                out.append(summarize_session(jsonl))
            except OSError:
                continue
    out.sort(key=lambda s: s.mtime, reverse=True)
    return out


# --- resolution --------------------------------------------------------------

def resolve_session(arg: str, sessions: List[SessionSummary]) -> List[SessionSummary]:
    """Find sessions matching arg. Exact > prefix > slug-fuzzy > text-fuzzy."""
    for s in sessions:
        if s.session_id == arg:
            return [s]
    prefix = [s for s in sessions if s.session_id.startswith(arg)]
    if prefix:
        return prefix
    needle = arg.lower()
    by_slug = [s for s in sessions if needle in s.project_slug.lower()]
    if by_slug:
        return by_slug
    return [
        s for s in sessions
        if (s.title and needle in s.title.lower())
        or (s.last_prompt and needle in s.last_prompt.lower())
    ]
