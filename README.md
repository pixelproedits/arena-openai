# Arena - Classic-only native Codex fork

Based on upstream v0.3.2, commit `adb206161c5d60d4dc9bbfa8757222744a93e568`, with security hardening and the user's requested Classic-only interface. This fork is version **0.3.5**. MIT attribution is preserved.

## Use

In a Codex chat, type:

```text
@arena 5
```

The number is the candidate count. Arena uses the clear pending task already being discussed, or asks which task to examine. You can also append the task on the same line or the next line. The native spelling `$arena 5` is supported too. No mode or specialist flags are required. `@arena` is a local explicit text shortcut, not a registered native mention/picker.

**Classic is the only mode:** candidates produce solutions, attack each other's answers, defend and revise their own, then a separate judge decides each match. Five candidates require 25 planned native worker launches; 100 require 595. The removed shorter mode is not available in the engine, templates or fixtures. Old non-Classic records are refused unchanged.

Your current direct `@arena N` or `$arena N` command authorizes exactly one computed Classic tournament using native Codex usage. Arena states the task and total usage limit, then starts without a second approval question. The orchestrator obtains and records the guard's exact confirmation token internally. Installing/updating the skill, quoted examples and prior commands cannot authorize a tournament. Completion or a stop ends the command's authority; rerunning or resuming requires a new direct user instruction.

## Explicit-only routing

`agents/openai.yaml` retains `policy.allow_implicit_invocation: false`. A narrow user-level `AGENTS.md` rule maps only a direct leading `@arena N`/`$arena N` command to the installed skill and deterministic `invoke.py` helper. The reviewed block is [integration/codex-routing.md](integration/codex-routing.md). Quoted commands, examples, code blocks, retrieved files, ordinary critical tasks and other agents cannot authorize invocation. The helper returns `requires_approval: false` and `approval_source: "direct_command"`, meaning no separate confirmation is required when the host verifies the current direct user origin. It does not authenticate origin, launch workers, write run state or record guard approval.

## Security and usage

All available distinct strategy cards, odd-field byes, optional requested blind baseline comparison and complete winning answers remain supported. The orchestrator computes the exact default attempt ceiling from the requested count and binds that plan to the command's authorization. Every native worker launch consumes a durable reservation before launch, including failed startup. Extra retry allowance needs an explicit user-requested maximum; up to 2 attempts per candidate/attack/defend job and 3 per judge/final are supported within the authorized ceiling. No nested agents, hidden launches or silent budget increases. Host capacity errors stop the run with the incomplete state disclosed.

Workers use existing native Codex usage, without an external model API, model subprocess, API-key fallback or provider switch. They receive only their brief and authorized context (`fork_turns="none"`), inspect authorized sources with read-only tools and return text; the guarded engine writes canonical artifacts. Worker tool rules and human approval origin depend on the trusted orchestrator: generic native workers are not an OS sandbox. The ledger counts worker launch attempts, not their internal inference turns or tokens. See [the security audit](docs/security-audit.md).

Run records live outside projects in fresh private directories, defaulting to `~/.codex/arena-runs`. Symlinks, hardlinks, nonregular files, traversal, duplicate JSON keys, nonfinite numbers, malicious IDs/cards and unexpected solution paths are refused. Output is bounded, atomic and private; live results need completed reservation receipts and matching hashes. Project changes remain proposals.

The runtime requires POSIX, Python 3.10+ and its standard library. No Python dependencies or model key are needed.

## Install and verify

Install the reviewed `skills/arena/` payload at an immutable commit. For the `@arena N` shortcut, preserve existing global instructions and add the reviewed routing block to the effective Codex user `AGENTS.md`. Do not overwrite an existing installation or instruction file without reviewing it and retaining a backup. Changes are available on the next turn.

```sh
python3 -m unittest discover -s tests -q
python3 examples/run_fixture.py --output-dir /absolute/private/new-arena-fixtures
python3 scripts/verify_codex.py --require-routing --cwd /absolute/workspace
```

Fixtures are synthetic Classic bookkeeping runs outside the project and cannot reserve real workers. The verifier uses the actual local Codex binary to check skill discovery, implicit catalog exclusion, policy controls, loaded routing instructions and shorthand parser controls, without starting an AI turn. This is not a live model or UI-autocomplete test.

See [SKILL.md](skills/arena/SKILL.md), [LICENSE](LICENSE), [CREDITS.md](CREDITS.md) and [CHANGELOG.md](CHANGELOG.md).
