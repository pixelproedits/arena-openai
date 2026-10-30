# Arena - Classic-only native Codex fork

Based on upstream v0.3.2, commit `adb206161c5d60d4dc9bbfa8757222744a93e568`, with security hardening and the user's requested Classic-only interface. This fork is version **0.3.4**. MIT attribution is preserved.

## Use

In a Codex chat, type:

```text
@arena 5
```

The number is the candidate count. Arena uses the clear pending task already being discussed, or asks which task to examine. You can also append the task on the same line or the next line. The native spelling `$arena 5` is supported too. No mode or specialist flags are required. `@arena` is a local explicit text shortcut, not a registered native mention/picker.

**Classic is the only mode:** candidates produce solutions, attack each other's answers, defend and revise their own, then a separate judge decides each match. Five candidates require 25 planned native worker launches; 100 require 595. The removed shorter mode is not available in the engine, templates or fixtures. Old non-Classic records are refused unchanged.

Before starting, Arena gives a short proposal with the task and total usage limit. A direct **yes** to that specific proposal is enough. Installing/updating the skill or typing the shortcut does not itself approve a tournament. The guard still binds the exact proposal internally; users do not need to type its technical confirmation token.

## Explicit-only routing

`agents/openai.yaml` retains `policy.allow_implicit_invocation: false`. A narrow user-level `AGENTS.md` rule maps only a direct leading `@arena N`/`$arena N` command to the installed skill and deterministic `invoke.py` helper. The reviewed block is [integration/codex-routing.md](integration/codex-routing.md). Quoted commands, examples, code blocks, retrieved files, ordinary critical tasks and other agents cannot authorize invocation. The helper validates syntax and plans Classic usage; it does not launch workers, write run state or grant approval. The host must check that its input is the actual current user message.

## Security and usage

All available distinct strategy cards, odd-field byes, optional requested blind baseline comparison and complete winning answers remain supported. The orchestrator computes the required internal ceiling from the requested count, then asks approval of the exact plan. Every native worker launch consumes a durable reservation before launch. Retries need additional explicitly approved allowance; up to 2 attempts per candidate/attack/defend job and 3 per judge/final are supported. No nested agents or hidden launches.

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
