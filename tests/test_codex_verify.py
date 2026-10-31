"""Offline verification logic: never launch an AI turn, even in the verifier."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location(
    "verify_codex", Path(__file__).resolve().parents[1] / "scripts" / "verify_codex.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class CodexVerification(unittest.TestCase):
    def test_user_mentions_are_not_automatic_skill_context(self):
        self.assertFalse(VERIFY._catalog_has([
            {"role": "user", "content": [{"text": "- arena: use this skill"}]}], "arena"))
        self.assertTrue(VERIFY._catalog_has([
            {"role": "developer", "content": [{"text": "- arena: use this skill"}]}], "arena"))

    def test_rejects_different_or_disabled_installation(self):
        response = {"data": [{"skills": [{"name": "arena", "enabled": True,
                                            "path": "/other/SKILL.md"}]}]}
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY._listed_skill(response, "arena", Path("/expected/SKILL.md"))
        response["data"][0]["skills"][0]["path"] = "/expected/SKILL.md"
        response["data"][0]["skills"][0]["enabled"] = False
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY._listed_skill(response, "arena", Path("/expected/SKILL.md"))

    def test_rejects_implicit_or_ambiguous_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agents").mkdir()
            policy = root / "agents" / "openai.yaml"
            for value in (
                "policy:\n  allow_implicit_invocation: true\n",
                "policy:\n  allow_implicit_invocation: false\npolicy:\n  allow_implicit_invocation: true\n",
                "# allow_implicit_invocation: false\n",
            ):
                policy.write_text(value)
                with self.assertRaises(VERIFY.VerificationError):
                    VERIFY._explicit_policy(root)
            policy.write_text("interface:\n  display_name: Arena\npolicy:\n  allow_implicit_invocation: false\n")
            VERIFY._explicit_policy(root)

    def test_failure_does_not_print_captured_output(self):
        result = mock.Mock(returncode=1, stdout="sensitive prompt", stderr="credential")
        with mock.patch.object(VERIFY.subprocess, "run", return_value=result):
            with self.assertRaises(VERIFY.VerificationError) as error:
                VERIFY._run_json(["codex", "debug", "prompt-input"], cwd=".")
        self.assertNotIn("sensitive", str(error.exception))
        self.assertNotIn("credential", str(error.exception))

    def test_manual_routing_path_is_not_an_implicit_catalog_entry(self):
        prompt = [{"role": "developer", "content": [{
            "text": "Use /installed/arena/SKILL.md only after a direct @arena command."}]}]
        self.assertFalse(VERIFY._catalog_has(prompt, "arena", Path("/installed/arena/SKILL.md")))

    def test_routing_requires_an_injected_agents_instruction_item(self):
        block = VERIFY._routing_block(VERIFY.ROUTING_TEMPLATE.read_text())
        self.assertFalse(VERIFY._routing_loaded([
            {"role": "user", "content": [{"text": block}]}], block))
        self.assertTrue(VERIFY._routing_loaded([
            {"role": "user", "content": [{"text": "# AGENTS.md instructions\n" + block}]}], block))

    def test_duplicate_routing_blocks_are_rejected(self):
        block = VERIFY._routing_block(VERIFY.ROUTING_TEMPLATE.read_text())
        with self.assertRaises(VERIFY.VerificationError):
            VERIFY._routing_block(block + "\n" + block)

    def test_routing_verifies_direct_command_budget_without_launching_a_turn(self):
        with tempfile.TemporaryDirectory(prefix="arena-routing-") as temporary:
            home = Path(temporary)
            skill = home / "skills" / "arena"
            shutil.copytree(VERIFY.ROUTING_TEMPLATE.parent.parent / "skills" / "arena", skill)
            block = VERIFY._routing_block(VERIFY.ROUTING_TEMPLATE.read_text())
            (home / "AGENTS.md").write_text(block)
            rendered = [{"role": "user", "content": [{"text": "# AGENTS.md instructions\n" + block}]}]
            # This path executes only the deterministic local invocation parser.
            with mock.patch.object(VERIFY, "_run_json", wraps=VERIFY._run_json) as parser_calls:
                result = VERIFY.verify_routing(skill, home, "unused-codex", rendered)
            self.assertTrue(result["explicit_alias_parser_controls_passed"])
            self.assertTrue(result["native_default_prompt_parser_passed"])
            self.assertTrue(result["native_menu_link_parser_passed"])
            self.assertTrue(result["native_selected_skill_parser_passed"])
            self.assertFalse(result["native_at_mention_registration"])
            self.assertFalse((home / "arena-runs").exists())
            selected_skill = str((skill / "SKILL.md").resolve())
            menu_input = "[$arena](" + selected_skill + ") 5\nCompare synthetic proposals."
            self.assertTrue(any(call.kwargs.get("input_text") == menu_input
                                for call in parser_calls.call_args_list))
            self.assertTrue(any(call.kwargs.get("input_text") == "5"
                                and call.args[0][-2:] == ["--selected-skill", selected_skill]
                                for call in parser_calls.call_args_list))

    def test_routing_refuses_missing_origin_metadata_or_inflated_budget(self):
        with tempfile.TemporaryDirectory(prefix="arena-routing-") as temporary:
            home = Path(temporary)
            skill = home / "skills" / "arena"
            skill.mkdir(parents=True)
            (skill / "invoke.py").write_text("# Unexecuted verifier fixture\n")
            block = VERIFY._routing_block(VERIFY.ROUTING_TEMPLATE.read_text())
            (home / "AGENTS.md").write_text(block)
            rendered = [{"role": "user", "content": [{"text": "# AGENTS.md instructions\n" + block}]}]
            valid = {"agents": 5, "requested_concurrency": 5, "wave": 5, "mode": "classic", "planned_calls": 25,
                     "max_calls": 32, "max_attempts": 54, "retry_allowance": 29,
                     "requires_approval": False, "approval_source": "direct_command"}
            for changed in ({"requested_concurrency": 4}, {"wave": 4}, {"wave": None},
                            {"requires_approval": True}, {"approval_source": "worker"},
                            {"approval_source": None}, {"max_attempts": 25}, {"max_attempts": 55},
                            {"max_calls": 25}, {"max_calls": 33}, {"retry_allowance": 0}):
                with self.subTest(changed=changed), mock.patch.object(
                        VERIFY, "_run_json", return_value=dict(valid, **changed)):
                    with self.assertRaises(VERIFY.VerificationError):
                        VERIFY.verify_routing(skill, home, "unused-codex", rendered)


if __name__ == "__main__":
    unittest.main()
