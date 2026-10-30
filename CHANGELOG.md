# Hardened fork 0.3.3

- Pin provenance to upstream v0.3.2 / adb206161c5d60d4dc9bbfa8757222744a93e568.
- Add explicit-only Codex metadata, per-run approval and single-attempt ledger.
- Harden path/state/permissions and bounded atomic output handling.
- Add offline adversarial regression tests and local Codex discovery verification.
- Preserve original native tournaments, field sizes, modes and retry capability; disclose host tool isolation boundaries.

# Changelog

This file records published release notes for the project.

## v0.3.2 - released, 2026-10-03

- Reject malformed score values and verdicts that identify a different match or unrelated participants; preserve each quarantined verdict.
- Require synthesized winner solutions throughout lean collection and advancement.
- Validate saved state before use and report malformed or mismatched state without rewriting it.
- Add regression coverage for validation, recovery evidence, and unchanged call-budget contracts.
- Align both plugin manifests and the skill archive test with version 0.3.2.

## v0.3.1 - released, 2026-10-03

- Clarify the default lean, quick, classic, and maximum planned-call budgets.
- Document manual Windows PowerShell and macOS/Linux skill-copy installation, prerequisites, and the skill-only ZIP artifact.
- Add deterministic local fixture examples and distinguish simulated planned calls from live agent work.
- Align both plugin manifests with version 0.3.1.

## v0.3.0 - historical

- Added the lean judge-and-improve tournament flow as the default, with the classic attack/defend/judge flow retained as an option.
- Added a 32-call default guard and the `--max-calls` override.
- Added plugin manifests for portable Agent Plugins packaging and Codex compatibility.
- Preserved the inherited engine and its MIT attribution.
