"""CLI entry point — argparse, dispatch, and the list/show commands."""

import argparse
import sys
from typing import List

from peek.digest import build_turns
from peek.render import format_digest, format_list
from peek.sessions import (
    SessionSummary,
    decode_slug,
    list_sessions,
    resolve_session,
    slugify_cwd,
)

DEFAULT_LIST_LIMIT = 10
DEFAULT_TURNS = 10


def cmd_list(args, all_sessions: List[SessionSummary]) -> int:
    scope = all_sessions
    header = "Recent sessions (all projects)"
    if args.project:
        slug = slugify_cwd()
        scope = [s for s in all_sessions if s.project_slug == slug]
        display_path = scope[0].project_path if scope else decode_slug(slug)
        header = f"Recent sessions for `{display_path}`"
    print(format_list(scope[: args.limit], header=header))
    return 0


def cmd_show(args, all_sessions: List[SessionSummary]) -> int:
    matches = resolve_session(args.target, all_sessions)
    if not matches:
        print(f"No session matched `{args.target}`.\n")
        print(format_list(all_sessions[:5], header="Recent sessions"))
        return 1
    if len(matches) > 1:
        print(f"`{args.target}` matched {len(matches)} sessions:\n")
        print(format_list(matches[:10], header="Matches"))
        return 2
    s = matches[0]
    turns = build_turns(s.path, include_sidechains=args.full)
    print(format_digest(s, turns, n=args.turns, full=args.full,
                        show_tools=args.tools, do_redact=args.redact))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="peek_session",
        description="Read another Claude Code session's transcript.",
    )
    p.add_argument("target", nargs="?",
                   help="Session UUID, short prefix, or fuzzy slug/text. Omit to list.")
    p.add_argument("--turns", type=int, default=DEFAULT_TURNS,
                   help=f"Turns to show (default {DEFAULT_TURNS})")
    p.add_argument("--full", action="store_true",
                   help="No truncation, include sidechain/subagent activity")
    p.add_argument("--tools", action="store_true",
                   help="Include tool call summaries (errors always shown)")
    p.add_argument("--redact", action="store_true",
                   help="Redact common secret patterns (sk-, ghp_, AKIA, xox*)")
    p.add_argument("--project", action="store_true",
                   help="Scope list to current cwd's project")
    p.add_argument("--limit", type=int, default=DEFAULT_LIST_LIMIT,
                   help=f"Max sessions when listing (default {DEFAULT_LIST_LIMIT})")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    all_sessions = list_sessions()
    if not args.target:
        return cmd_list(args, all_sessions)
    return cmd_show(args, all_sessions)


if __name__ == "__main__":
    sys.exit(main())
