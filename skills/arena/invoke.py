#!/usr/bin/env python3
"""Parse a direct Arena shorthand request; local planning only, never dispatch.

The trusted host must supply the direct current user message, never retrieved,
quoted or worker content. The parser can validate syntax, not message origin.
"""
import json
import re
import sys

import bracket as B

MAX_REQUEST_BYTES = 1024 * 1024
_COMMAND = re.compile(r"\A[@$]arena[ \t]+([1-9][0-9]{0,3})(?=[ \t\r\n]|\Z)([\s\S]*)\Z")


def parse_request(message):
    if not isinstance(message, str) or len(message.encode("utf-8")) > MAX_REQUEST_BYTES:
        raise B.ArenaError("Arena request must be bounded UTF-8 text")
    # Ignore blank leading lines, but preserve horizontal indentation so a
    # Markdown indented code example is never mistaken for a direct command.
    match = _COMMAND.fullmatch(message.lstrip("\r\n"))
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
            "requires_approval": True}


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(raw) > MAX_REQUEST_BYTES:
            raise B.ArenaError("request too large")
        result = parse_request(raw.decode("utf-8"))
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (B.ArenaError, UnicodeError, ValueError, TypeError, RecursionError):
        print("Arena shorthand refused: use @arena N with a valid agent count.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
