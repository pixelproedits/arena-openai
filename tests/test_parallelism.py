"""Requested Arena concurrency is N; model-free parsing and bookkeeping tests."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1] / "skills" / "arena"
sys.path.insert(0, str(SKILL))
import bracket as B
import guard as G
import invoke


class RequestedParallelism(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="arena-parallelism-")
        self.root = Path(os.path.realpath(self.temporary.name))

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SKILL / "bracket.py"), *map(str, args)],
                              cwd=SKILL.parents[1], text=True, capture_output=True, timeout=20)

    def init(self, count, name="run", *extra):
        run = self.root / name
        result = self.cli("init", "--agents", count, "--max-calls", max(32, 6 * count - 5),
                          "--seed", 7, "--task", "Synthetic planning test; no workers.",
                          "--dir", run, *extra)
        return run, result

    def test_all_explicit_aliases_and_menu_selections_request_n_parallel_turns(self):
        for count in (1, 5, 20, 100):
            commands = (("@arena " + str(count), None),
                        ("$arena " + str(count), None),
                        (invoke.MENU_LINK + " " + str(count), None),
                        (str(count), invoke.CANONICAL_SKILL))
            for message, selected in commands:
                with self.subTest(count=count, message=message):
                    parsed = invoke.parse_request(message, selected_skill=selected)
                    self.assertEqual(parsed["agents"], count)
                    self.assertEqual(parsed["requested_concurrency"], count)
                    self.assertEqual(parsed["wave"], count)
                    self.assertEqual(parsed["planned_calls"], 6 * count - 5)
                    self.assertEqual(parsed["max_attempts"], 13 * count - 11)

    def test_default_plan_has_one_initial_spawn_wave_without_changing_classic_jobs(self):
        for count, rounds, calls in ((1, 0, 1), (5, 3, 25), (20, 5, 115), (100, 7, 595)):
            with self.subTest(count=count):
                result = self.cli("plan", "--agents", count, "--json")
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertEqual(plan["rounds"], rounds)
                self.assertEqual(plan["calls"], calls)
                self.assertEqual(plan["waves"] - sum(row["waves"] for row in plan["rows"]), 1)
                self.assertEqual(plan["waves"], 1 + 3 * rounds)
                self.assertEqual(list(self.root.iterdir()), [])

    def test_default_new_state_and_live_initialization_record_wave_n(self):
        data = B.load_strategies()
        for count in (1, 5, 20, 100):
            with self.subTest(count=count):
                state = B.new_state(count, 7, data, str(self.root / ("memory-%d" % count)))
                self.assertEqual(state["wave"], count)
                run, result = self.init(count, "run-%d" % count)
                self.assertEqual(result.returncode, 0, result.stderr)
                saved = json.loads((run / "arena.json").read_text())
                self.assertEqual(saved["wave"], count)
                self.assertIs(saved["offline_fixture"], False)
                self.assertFalse((run / "approval.json").exists())

    def test_live_initialization_refuses_smaller_and_larger_waves_before_writes(self):
        for wave in (1, 4, 6, 20):
            with self.subTest(wave=wave):
                run, result = self.init(5, "refused-%d" % wave, "--wave", wave)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(run.exists())
        self.assertEqual(list(self.root.iterdir()), [])

    def test_explicit_matching_live_wave_is_supported(self):
        run, result = self.init(5, "matching", "--wave", 5)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((run / "arena.json").read_text())
        definition = G.definition(state)
        self.assertEqual((definition["agents"], definition["wave"]), (5, 5))
        self.assertEqual((definition["calls"], definition["max_attempts"]), (25, 54))

    def test_guard_independently_refuses_a_lower_or_higher_live_wave(self):
        run, result = self.init(5)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((run / "arena.json").read_text())
        for wave in (1, 4, 6, 20):
            with self.subTest(wave=wave):
                changed = copy.deepcopy(state)
                changed["wave"] = wave
                with self.assertRaises(B.ArenaError):
                    G.definition(changed)
        self.assertFalse((run / "approval.json").exists())

    def test_custom_wave_remains_available_for_offline_planning_and_fixtures(self):
        result = self.cli("plan", "--agents", 20, "--wave", 5, "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["calls"], 115)
        self.assertEqual(plan["waves"] - sum(row["waves"] for row in plan["rows"]), 4)
        run, result = self.init(5, "fixture", "--wave", 2, "--offline-fixture")
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads((run / "arena.json").read_text())
        self.assertEqual(state["wave"], 2)
        self.assertIs(state["offline_fixture"], True)
        proposal = G.proposal(state)
        with self.assertRaises(B.ArenaError):
            G.approve(state, proposal["confirmation"])
        self.assertFalse((run / "approval.json").exists())

    def test_historical_smaller_wave_state_still_validates_without_rewriting(self):
        run = str(self.root / "historical")
        state = B.new_state(5, 7, B.load_strategies(), run, wave=2)
        before = copy.deepcopy(state)
        self.assertIs(B.validate_state(state, os.path.join(run, "arena.json"), run), state)
        self.assertEqual(state, before)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
