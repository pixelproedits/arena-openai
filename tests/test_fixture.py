"""Smoke deterministic model-free Arena fixture scenarios."""
import json, os, subprocess, sys, tempfile, unittest
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "examples", "run_fixture.py")

class FixtureSmoke(unittest.TestCase):
    def test_scenarios_complete_with_winner_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="arena-fixture-") as temp:
            output = os.path.join(os.path.realpath(temp), "runs")
            result = subprocess.run([sys.executable, FIXTURE, "--output-dir", output],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for name, mode, calls in (("lean-quick", "lean", 3), ("classic-two", "classic", 7)):
                directory = os.path.join(output, name)
                with open(os.path.join(directory, "arena.json"), encoding="utf-8") as stream:
                    state = json.load(stream)
                self.assertEqual(state["mode"], mode)
                self.assertIs(state["offline_fixture"], True)
                self.assertIn(state["champion"], state["agents"])
                self.assertEqual(sum(agent["alive"] for agent in state["agents"].values()), 1)
                with open(os.path.join(directory, "winner.txt"), encoding="utf-8") as stream:
                    winner = stream.read()
                self.assertIn("no model or agent calls were made", winner)
                self.assertIn("synthetic, not API usage", winner)
                self.assertIn("Planned calls: %d" % calls, winner)

if __name__ == "__main__":
    unittest.main(verbosity=2)
