#!/usr/bin/env python3
"""Check local Codex discovery and invocation policy without starting an AI turn.

Only the local `debug prompt-input` renderer and App Server `initialize` /
`skills/list` requests are used. No thread/turn, model, auth, shell-execution,
connector, or credential endpoints are called. Complete rendered prompts and
other skill metadata are kept in memory and never printed or saved.
"""
import argparse
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tempfile
import time


class VerificationError(Exception):
    """A local verification failed; details intentionally exclude raw output."""


def _run_json(command, *, cwd, env=None):
    try:
        completed = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                   text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise VerificationError("Local Codex command could not complete") from None
    if completed.returncode:
        raise VerificationError("Local Codex command returned an error")
    try:
        return json.loads(completed.stdout)
    except (ValueError, TypeError):
        raise VerificationError("Local Codex returned invalid JSON") from None


def _catalog_text(items):
    if not isinstance(items, list):
        raise VerificationError("Unexpected local prompt representation")
    # User text containing a skill mention must not count as automatic discovery.
    return "\n".join(part.get("text", "") for item in items
                     if isinstance(item, dict) and item.get("role") == "developer"
                     for part in item.get("content", [])
                     if isinstance(part, dict) and isinstance(part.get("text"), str))


def _catalog_has(items, name, path=None):
    text = _catalog_text(items)
    return bool(re.search(r"(?m)^- " + re.escape(name) + r":", text)
                or (path is not None and str(path) in text))


def _explicit_policy(skill):
    path = skill / "agents" / "openai.yaml"
    if not path.is_file() or path.is_symlink():
        raise VerificationError("Installed invocation policy is not a regular file")
    text = path.read_text(encoding="utf-8")
    # This verifies the deliberately simple policy emitted by this fork, rather
    # than attempting to implement a general-purpose YAML parser.
    if len(re.findall(r"(?m)^policy:\s*$", text)) != 1:
        raise VerificationError("Installed invocation policy is missing or ambiguous")
    if len(re.findall(r"allow_implicit_invocation\s*:", text)) != 1:
        raise VerificationError("Installed invocation policy is missing or ambiguous")
    if not re.search(r"(?m)^policy:\s*\n  allow_implicit_invocation: false\s*$", text):
        raise VerificationError("Installed skill is not explicitly configured as explicit-only")


def _listed_skill(response, name, expected):
    if not isinstance(response, dict) or not isinstance(response.get("data"), list):
        raise VerificationError("Unexpected local skill listing")
    matches = [skill for entry in response["data"] for skill in entry.get("skills", [])
               if skill.get("name") == name]
    if len(matches) != 1 or not matches[0].get("enabled"):
        raise VerificationError("Installed skill is missing, disabled, or ambiguous")
    listed = Path(matches[0].get("path", ""))
    if listed.resolve() != expected.resolve():
        raise VerificationError("Codex discovered a different copy of the skill")
    return matches[0]


def list_skills(codex, cwd):
    """Ask a local stdio App Server to re-scan installed skills; no AI turn."""
    try:
        proc = subprocess.Popen([codex, "app-server", "--stdio"], cwd=cwd,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except OSError:
        raise VerificationError("Local Codex App Server could not start") from None
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    buffered = bytearray()

    def send(message):
        proc.stdin.write((json.dumps(message) + "\n").encode())
        proc.stdin.flush()

    def read_reply(identifier):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            while b"\n" in buffered:
                line, _, rest = buffered.partition(b"\n")
                buffered[:] = rest
                try:
                    result = json.loads(line)
                except ValueError:
                    raise VerificationError("Local App Server returned invalid JSON") from None
                if result.get("id") == identifier:
                    if "error" in result:
                        raise VerificationError("Local App Server rejected a read-only request")
                    return result.get("result")
            if not selector.select(timeout=min(1, max(0, deadline - time.monotonic()))):
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                raise VerificationError("Local App Server closed before replying")
            buffered.extend(chunk)
            if len(buffered) > 16 * 1024 * 1024:
                raise VerificationError("Local App Server reply exceeded the safety limit")
        raise VerificationError("Local App Server read-only request timed out")

    try:
        send({"id": 0, "method": "initialize", "params": {
            "clientInfo": {"name": "arena_offline_verify", "version": "1.0"}}})
        read_reply(0)
        send({"method": "initialized", "params": {}})
        send({"id": 1, "method": "skills/list", "params": {
            "cwds": [str(cwd)], "forceReload": True}})
        return read_reply(1)
    except (OSError, BrokenPipeError):
        raise VerificationError("Local App Server transport failed") from None
    finally:
        selector.close()
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        proc.stdin.close()
        proc.stdout.close()


def policy_control(codex, cwd):
    """Positive/negative controls in a temporary Codex home, never the real home."""
    name = "arena-offline-invocation-probe"
    with tempfile.TemporaryDirectory(prefix="arena-invocation-check-") as temporary:
        home = Path(temporary)
        skill = home / "skills" / name
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: " + name + "\ndescription: Temporary offline policy probe.\n"
            "---\nOffline policy fixture; never execute a task.\n", encoding="utf-8")
        env = dict(os.environ, CODEX_HOME=str(home))
        observations = []
        for allow in (True, False):
            (skill / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Offline probe"\n'
                '  short_description: "Offline invocation policy fixture"\n'
                'policy:\n  allow_implicit_invocation: ' + str(allow).lower() + "\n",
                encoding="utf-8")
            rendered = _run_json([codex, "debug", "prompt-input", "Offline policy check"],
                                 cwd=cwd, env=env)
            observations.append(_catalog_has(rendered, name))
        if observations != [True, False]:
            raise VerificationError("Local Codex did not enforce invocation policy controls")


def verify(skill, cwd, codex="codex"):
    skill, cwd = Path(skill).absolute(), Path(cwd).absolute()
    if not (skill / "SKILL.md").is_file() or skill.is_symlink():
        raise VerificationError("Installed Arena skill is missing or is a symlink")
    _explicit_policy(skill)
    _listed_skill(list_skills(codex, cwd), "arena", skill / "SKILL.md")
    rendered = _run_json([codex, "debug", "prompt-input", "Offline discovery check"], cwd=cwd)
    if _catalog_has(rendered, "arena", skill / "SKILL.md"):
        raise VerificationError("Installed Arena appeared in automatic model context")
    policy_control(codex, cwd)
    return {
        "skill": "arena",
        "installed_skill": str(skill),
        "explicit_skill_discoverable": True,
        "implicit_context_excluded": True,
        "runtime_policy_controls_passed": True,
        "model_calls": 0,
        "tournaments_started": 0,
        "verification_scope": "Local runtime discovery and policy; no model generation or live tournament",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", default=str(
        Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "skills" / "arena"))
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--codex", default=shutil.which("codex") or "codex")
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.skill_dir, args.cwd, args.codex), indent=2))
    except (VerificationError, OSError, UnicodeError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)
                          if isinstance(exc, VerificationError) else "Local file inspection failed"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
