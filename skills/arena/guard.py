#!/usr/bin/env python3
"""Offline approval and consumed-before-launch accounting for native Codex jobs.

Never launches AI or tools. The trusted host must enforce actual user approval,
use one reservation per native worker launch and apply the worker instructions.
This ledger is not an OS sandbox or cryptographic human authentication.
"""
import argparse
import hashlib
import json
import os
import sys

import bracket as B
import secure_io as IO

MAX_AGENTS = 2160
MAX_CALLS = 38880  # natural upper bound including upstream retry allowances
MAX_WAVE = 2160
MAX_OUTPUT_BYTES = 1024 * 1024
LEDGER = "approval.json"


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def definition(state, max_attempts=None):
    if state.get("mode", "classic") != "classic":
        raise B.ArenaError("only Classic tournament approval is supported")
    n, wave = state["agents_n"], state["wave"]
    calls = B.plan_totals(n, wave)["calls"] + int(state["has_baseline"])
    if max_attempts is None:
        max_attempts = B.original_attempt_budget(n, state["has_baseline"])
    if (not 1 <= n <= MAX_AGENTS or not 1 <= wave <= MAX_WAVE
            or type(max_attempts) is not int or not calls <= max_attempts <= min(MAX_CALLS, calls * 3)):
        raise B.ArenaError("invalid approved attempt budget")
    files = {}
    for name in ("task.md", "rubric.md") + (("baseline.md",) if state["has_baseline"] else ()):
        files[name] = hashlib.sha256(IO.read_text(os.path.join(state["dir"], name)).encode()).hexdigest()
    for name in ("SKILL.md", "bracket.py", "guard.py", "invoke.py", "secure_io.py", "strategies.json", "agents/openai.yaml"):
        files["skill/" + name] = hashlib.sha256(IO.read_text(os.path.join(B.HERE, name)).encode()).hexdigest()
    return {"run": state["dir"], "seed": state["seed"], "agents": n,
            "mode": "classic", "wave": wave, "calls": calls,
            "max_calls": state.get("max_calls", 32), "max_attempts": max_attempts,
            "attempts_per_candidate": 2, "attempts_per_judge": 3,
            "external_api": False, "project_writes": False, "files": files}


def proposal(state, max_attempts=None):
    spec = definition(state, max_attempts)
    digest = hashlib.sha256(_json(spec).encode()).hexdigest()
    phrase = "APPROVE ARENA %s %s %d ATTEMPTS" % (os.path.basename(state["dir"]), digest[:16], spec["max_attempts"])
    return {"definition": spec, "digest": digest, "confirmation": phrase}


def _path(state):
    return os.path.join(state["dir"], LEDGER)


def require_approved(state):
    if state.get("offline_fixture"):
        raise B.ArenaError("offline fixtures can never authorize real workers")
    try:
        ledger = B.strict_json(IO.read_text(_path(state)))
        budget = ledger["definition"]["max_attempts"]
        expected = proposal(state, budget)
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise B.ArenaError("this tournament needs fresh explicit user approval") from error
    if (not isinstance(ledger, dict) or ledger.get("digest") != expected["digest"]
            or ledger.get("definition") != expected["definition"]
            or ledger.get("confirmation") != expected["confirmation"]
            or ledger.get("status") != "approved" or not isinstance(ledger.get("jobs"), dict)):
        raise B.ArenaError("approval is invalid or the approved task/workflow changed")
    jobs = ledger["jobs"]
    if len(jobs) > budget:
        raise B.ArenaError("job ledger exceeds the approved attempt count")
    for key, item in jobs.items():
        if (not isinstance(key, str) or not isinstance(item, dict)
                or item.get("status") not in ("reserved", "complete", "failed", "rejected")
                or not isinstance(item.get("outputs"), list)
                or not isinstance(item.get("prompt_hash"), str)):
            raise B.ArenaError("invalid job ledger")
    return ledger


def approve(state, confirmation, max_attempts=None):
    if state.get("offline_fixture"):
        raise B.ArenaError("offline fixtures cannot receive live approval")
    expected = proposal(state, max_attempts)
    if confirmation != expected["confirmation"]:
        raise B.ArenaError("confirmation does not match this exact tournament")
    IO.write_text(_path(state), _json(dict(expected, status="approved", jobs={})) + "\n", replace=False)
    return expected


def reserve(state, phase, job_id):
    ledger = require_approved(state)
    current, missing, _ = B.next_action(state)
    if current != phase:
        raise B.ArenaError("job phase is not the next permitted phase")
    B.verify_prerequisite_outputs(state, phase)
    if phase == "final":
        sources = {"champion": state["agents"][state["champion"]]["solution"],
                   "baseline": os.path.join(state["dir"], "baseline.md")}
        for label in ("X", "Y"):
            copied = IO.read_text(os.path.join(state["dir"], "final", label + ".md"))
            if copied != IO.read_text(sources[state["final"][label]]):
                raise B.ArenaError("blind final input differs from its approved source")
    jobs = [j for j in missing if j["id"] == job_id]
    if len(jobs) != 1:
        raise B.ArenaError("job is not pending in the current phase")
    job = jobs[0]
    prefix = "%s:%s#" % (phase, job_id)
    previous = [v for k, v in ledger["jobs"].items() if k.startswith(prefix)]
    if any(v["status"] == "reserved" for v in previous):
        raise B.ArenaError("job already has an active attempt")
    limit = 3 if phase in ("judge", "final") else 2
    if len(previous) >= limit:
        raise B.ArenaError("job retry allowance exhausted; stop this tournament")
    if len(ledger["jobs"]) >= ledger["definition"]["max_attempts"]:
        raise B.ArenaError("approved actual-attempt budget exhausted")
    if sum(j["status"] == "reserved" for j in ledger["jobs"].values()) >= state["wave"]:
        raise B.ArenaError("approved concurrency limit reached")
    if any(IO.file_exists(output) for output in job["outputs"]):
        raise B.ArenaError("job has existing outputs; inspect and reject the previous attempt before retrying")
    prompt = IO.read_text(job["prompt"])
    canonical = B.render_job(state, job, B.load_templates(), B.read_task(state)) + "\n"
    if prompt != canonical:
        raise B.ArenaError("job brief differs from the approved task and installed templates")
    key = prefix + str(len(previous) + 1)
    ledger["jobs"][key] = {"status": "reserved", "outputs": job["outputs"],
                           "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()}
    IO.write_text(_path(state), _json(ledger) + "\n")
    return {"reservation": key, "outputs": len(job["outputs"]), "prompt": prompt}


# Kept as an alias for model-free accounting tests; neither entry point spawns AI.
_reserve_attempt = reserve


def _current_job(state, reservation):
    try:
        phase, tail = reservation.split(":", 1)
        job_id, attempt = tail.rsplit("#", 1)
        if not attempt.isdigit():
            raise ValueError()
    except (AttributeError, ValueError):
        raise B.ArenaError("invalid reservation identifier") from None
    matches = [j for j in B.phase_jobs(state, phase) if j["id"] == job_id]
    if len(matches) != 1:
        raise B.ArenaError("reservation no longer matches the current job")
    return matches[0]


def finish(state, reservation, outputs=None):
    ledger = require_approved(state)
    job = ledger["jobs"].get(reservation)
    if not job or job["status"] != "reserved":
        raise B.ArenaError("reservation is not active")
    expected = _current_job(state, reservation)
    if expected["outputs"] != job["outputs"]:
        raise B.ArenaError("reservation output paths changed")
    if outputs is None:
        job["status"] = "failed"
    else:
        if (not isinstance(outputs, list) or len(outputs) != len(job["outputs"])
                or any(not isinstance(s, str) or not s.strip()
                       or len(s.encode()) > MAX_OUTPUT_BYTES for s in outputs)):
            raise B.ArenaError("expected a bounded nonempty string for each job output")
        if any(IO.file_exists(path) for path in expected["outputs"]):
            raise B.ArenaError("existing outputs cannot be overwritten")
        # A crash during publication preserves the consumed reservation and
        # requires explicit failure/rejection handling before another attempt.
        job["hashes"] = [hashlib.sha256(s.encode()).hexdigest() for s in outputs]
        job["status"] = "publishing"
        # Do not persist an intermediate unrecognized state: failed publication
        # remains reserved, consumes its attempt, and needs explicit local repair.
        for path, content in zip(expected["outputs"], outputs):
            IO.write_text(path, content, replace=False)
        job["status"] = "complete"
    IO.write_text(_path(state), _json(ledger) + "\n")
    return {"status": job["status"], "attempts_consumed": len(ledger["jobs"])}


def reject(state, reservation):
    """Preserve invalid output, enabling an already approved retry, never a launch."""
    ledger = require_approved(state)
    job = ledger["jobs"].get(reservation)
    if not job or job["status"] not in ("complete", "reserved"):
        raise B.ArenaError("attempt cannot be rejected")
    expected = _current_job(state, reservation)
    if expected["outputs"] != job["outputs"]:
        raise B.ArenaError("reservation output paths changed")
    for path in expected["outputs"]:
        if IO.file_exists(path):
            IO.quarantine(path)
    job["status"] = "rejected"
    IO.write_text(_path(state), _json(ledger) + "\n")
    return {"status": "rejected", "attempts_consumed": len(ledger["jobs"])}


def placeholder(state, phase, job_id):
    """Preserve upstream failed-nonjudge continuation without inventing an answer."""
    if phase not in ("spawn", "attack", "defend"):
        raise B.ArenaError("a judge verdict can never be replaced by a placeholder")
    ledger = require_approved(state)
    prefix = "%s:%s#" % (phase, job_id)
    previous = [(key, value) for key, value in ledger["jobs"].items() if key.startswith(prefix)]
    if len(previous) != 2 or any(value["status"] not in ("failed", "rejected") for _, value in previous):
        raise B.ArenaError("failure continuation requires two consumed failed attempts")
    key, item = previous[-1]
    expected = _current_job(state, key)
    if expected["outputs"] != item["outputs"] or any(IO.file_exists(p) for p in expected["outputs"]):
        raise B.ArenaError("failure continuation output paths are unsafe or occupied")
    content = "NO OUTPUT\n"
    for path in expected["outputs"]:
        IO.write_text(path, content, replace=False)
    item.update(status="complete", failure_placeholder=True,
                hashes=[hashlib.sha256(content.encode()).hexdigest()] * len(expected["outputs"]))
    IO.write_text(_path(state), _json(ledger) + "\n")
    return {"status": "failed-placeholder", "attempts_consumed": len(ledger["jobs"])}


def verify_outputs(state, jobs):
    """Unreserved or altered artifacts must not masquerade as live worker output."""
    if state.get("offline_fixture"):
        return
    ledger = require_approved(state)
    for job in jobs:
        prefix = "%s:%s#" % (job.get("phase", "judge"), job["id"])
        candidates = [v for k, v in ledger["jobs"].items()
                      if k.startswith(prefix) and v["status"] == "complete"]
        actual = [hashlib.sha256(IO.read_text(p).encode()).hexdigest() for p in job["outputs"]]
        if not any(v["outputs"] == job["outputs"] and v.get("hashes") == actual for v in candidates):
            raise B.ArenaError("live output lacks a completed reservation or has changed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("proposal", "approve", "reserve", "complete", "fail", "reject", "placeholder", "status"))
    parser.add_argument("--dir", required=True)
    parser.add_argument("--confirmation")
    parser.add_argument("--max-attempts", type=int)
    parser.add_argument("--phase", choices=B.PHASES)
    parser.add_argument("--job")
    parser.add_argument("--reservation")
    args = parser.parse_args(argv)
    try:
        directory = B.run_dir_from(args)
        with IO.lock(os.path.join(directory, ".lock")):
            state = B.load_state(args)
            if args.command == "proposal":
                result = proposal(state, args.max_attempts)
            elif args.command == "approve":
                result = approve(state, args.confirmation, args.max_attempts)
            elif args.command == "reserve":
                result = reserve(state, args.phase, args.job)
            elif args.command == "complete":
                limit = MAX_OUTPUT_BYTES * 12 + 1024
                raw = sys.stdin.buffer.read(limit)
                if len(raw) >= limit:
                    raise B.ArenaError("worker response too large")
                result = finish(state, args.reservation, B.strict_json(raw.decode("utf-8")))
            elif args.command == "fail":
                result = finish(state, args.reservation)
            elif args.command == "reject":
                result = reject(state, args.reservation)
            elif args.command == "placeholder":
                result = placeholder(state, args.phase, args.job)
            else:
                ledger = require_approved(state)
                result = {"status": ledger["status"], "attempts_consumed": len(ledger["jobs"]),
                          "approved_attempts": ledger["definition"]["max_attempts"]}
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except (B.ArenaError, OSError, ValueError, TypeError, KeyError, RecursionError):
        print("Arena guard refused the operation; check approval, state, paths and limits.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
