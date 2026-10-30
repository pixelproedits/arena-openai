#!/usr/bin/env python3
"""Parse a direct Arena shorthand request; local planning only, never dispatch.

The trusted host must supply the direct current user message, never retrieved,
quoted or worker content. The parser can validate syntax, not message origin.
Its approval metadata describes direct-command authorization; it does not record
guard approval, write state or establish the origin of its input.
"""
import json
from pathlib import Path
import re
import sys

import bracket as B

MAX_REQUEST_BYTES = 1024 * 1024
CANONICAL_SKILL = str(Path(__file__).resolve().with_name("SKILL.md"))
MENU_LINK = "[$arena](" + CANONICAL_SKILL + ")"
_COUNT_TASK = r"([1-9][0-9]{0,3})(?=[ \t\r\n]|\Z)([\s\S]*)\Z"
_COMMAND = re.compile(r"\A(?:[@$]arena|" + re.escape(MENU_LINK) + r")[ \t]+" + _COUNT_TASK)
_SELECTED_COMMAND = re.compile(r"\A" + _COUNT_TASK)


def parse_request(message, selected_skill=None):
    # A selected-skill value is trusted host metadata, never inferred from task
    # text or skill context. Exact comparison rejects aliases and traversal;
    # resolving a supplied path would broaden this input contract.
    if selected_skill is not None and selected_skill != CANONICAL_SKILL:
        raise B.ArenaError("selected skill does not match this invocation helper")
    if not isinstance(message, str) or len(message.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise B.ArenaError("Arena request must be bounded UTF-8 text")
    # Ignore blank leading lines, but preserve horizontal indentation so a
    # Markdown indented code example is never mistaken for a direct command.
    match = _COMMAND.fullmatch(message.lstrip("\r\n"))
    if match is None and selected_skill is not None:
        match = _SELECTED_COMMAND.fullmatch(message.lstrip("\r\n"))
    if not match:
        raise B.ArenaError("use @arena followed by the number of agents")
    agents = int(match.group(1))
    if not 1 <= agents <= B.MAX_AGENTS:
        raise B.ArenaError("requested agent count is outside the available strategy cards")
    task = match.group(2).strip()
    calls = B.plan_totals(agents)["calls"]
    return {"agents": agents, "task": task,
            "task_source": "inline" if task else "context", "mode": "classic",
            "planned_calls": calls, "max_calls": calls, "max_attempts": calls,
            "requires_approval": False, "approval_source": "direct_command"}


def main():
    try:
        args = sys.argv[1:]
        if not args:
            selected_skill = None
        elif len(args) == 2 and args[0] == "--selected-skill":
            selected_skill = args[1]
        else:
            raise B.ArenaError("unsupported invocation helper arguments")
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise B.ArenaError("request too large")
        result = parse_request(raw.decode("utf-8"), selected_skill=selected_skill)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (B.ArenaError, UnicodeError, ValueError, TypeError, RecursionError):
        print("Arena request refused: select Arena and type N, or use @arena N with a valid count.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
