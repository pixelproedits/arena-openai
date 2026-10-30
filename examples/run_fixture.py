#!/usr/bin/env python3
"""Run deterministic model-free Arena engine examples.
Usage: python examples/run_fixture.py --output-dir <directory>
Synthetic phase outputs are used; no model or agent calls are made.
"""
import argparse
import json
import os
import subprocess
import sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(REPO, "skills", "arena")
sys.path.insert(0, SKILL)
import bracket as arena  # noqa: E402
SCENARIOS = (("lean-quick", "lean", 7, 3), ("classic-two", "classic", 11, 7))

def call(*args):
    result = subprocess.run([sys.executable, os.path.join(SKILL, "bracket.py")] + list(args),
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("bracket.py failed:\n%s%s" % (result.stdout, result.stderr))
    return result.stdout

def read_state(directory):
    with open(os.path.join(directory, "arena.json"), encoding="utf-8") as stream:
        return json.load(stream)

def write(path, text):
    arena.SIO.write_text(os.path.abspath(path), text)

def outputs(phase, jobs):
    for job in jobs:
        if phase == "spawn":
            write(job["outputs"][0], "Synthetic fixture solution for %s.\n" % job["agent"])
        elif phase == "attack":
            write(job["outputs"][0], "ATTACK 1 [MINOR] fixture observation\nWhere: synthetic solution\nProblem: example only.\n")
        elif phase == "defend":
            write(job["outputs"][0], "ATTACK 1: CONCEDE. Fixture response.\n")
            write(job["outputs"][1], "Synthetic revised fixture solution for %s.\n" % job["agent"])
        elif phase == "judge":
            a, b = job["a"], job["b"]
            score = lambda value: {name: value for name, _ in arena.WEIGHTS}
            verdict = {"match": job["match"], "scores": {a: score(8), b: score(7)},
                       "winner": a, "reason": "Deterministic synthetic fixture verdict."}
            write(job["outputs"][0], json.dumps(verdict, indent=2) + "\n")
            if len(job["outputs"]) > 1:
                write(job["outputs"][1], "Synthetic fixture champion solution for %s.\n" % a)
        else:
            raise RuntimeError("unexpected phase: %s" % phase)

def run(root, name, mode, seed, planned_calls):
    directory = os.path.join(root, name)
    if os.path.exists(directory):
        raise RuntimeError("scenario output already exists: %s" % directory)
    args = ["init", "--agents", "2", "--seed", str(seed), "--max-calls", str(planned_calls),
            "--offline-fixture", "--task", "Demonstrate a deterministic fixture run without model calls.", "--dir", directory]
    if mode == "classic":
        args.append("--classic")
    call(*args)
    for _ in range(100):
        state = read_state(directory)
        phase, _, _ = arena.next_action(state)
        if phase == "done":
            break
        if phase in ("collect", "advance"):
            call(phase, "--dir", directory)
            continue
        call("prompts", phase, "--dir", directory)
        outputs(phase, arena.phase_jobs(read_state(directory), phase))
        call("check", phase, "--dir", directory)
    else:
        raise RuntimeError("fixture did not complete in 100 engine steps")
    state = read_state(directory)
    report = json.loads(call("winner", "--json", "--dir", directory))
    with open(report["solution"], encoding="utf-8") as stream:
        solution = stream.read().rstrip()
    write(os.path.join(directory, "winner.txt"),
          "Synthetic fixture; no model or agent calls were made.\n"
          "Mode: %s\nPlanned calls: %d (synthetic, not API usage)\nChampion: %s\n\n%s\n"
          % (mode, planned_calls, state["champion"], solution))
    print("%s: complete champion=%s synthetic_planned_calls=%d" %
          (name, state["champion"], planned_calls))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, help="parent directory for scenario outputs")
    root = os.path.realpath(parser.parse_args().output_dir)
    arena.checked_run_dir(root)
    arena.SIO.make_dirs(root)
    for scenario in SCENARIOS:
        run(root, *scenario)

if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        print("fixture error: %s" % error, file=sys.stderr)
        sys.exit(1)
