# Arena - hardened native Codex fork

Based exactly on upstream **v0.3.2**, commit `adb206161c5d60d4dc9bbfa8757222744a93e568`. This fork is version **0.3.3**, a fork version rather than an upstream release. MIT attribution is preserved.

Arena creates diverse candidate answers and refines them through a bracket. All original field sizes, lean/classic modes, strategy cards, byes and optional blind baseline comparison are retained. Four lean candidates use 7 planned native worker jobs; 100 classic candidates use 595. This fork hardens the surrounding files, state, approval and dispatch accounting.

## Invocation and usage approval

`$arena` is explicit-only: `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`. Normal requests, dissatisfaction and critical tasks do not activate it. Each tournament needs fresh approval bound to its exact task, configuration and maximum actual worker attempts, including retries. Installing the skill does not approve a tournament.

The original planned-call ceiling defaults to 32 and can be raised explicitly. Every launched native worker, including retries, must first consume a durable reservation. The default actual-attempt budget equals planned calls; an explicit larger approval enables the original 2 candidate/attack/defend attempts and 3 judge/final attempts. No hidden retries or nested agents. Concurrency adapts to actual host capacity.

Native Codex workers remain available. They use existing Codex usage, with no external model API, model subprocess, API-key fallback or provider switch. Workers receive only their brief and authorized context (`fork_turns="none"`), use read-only tools for authorized sources and return text; guarded local code writes canonical artifacts. The host's generic worker tools are **not** an OS sandbox. These tool-use boundaries and direct-human approval origin depend on the trusted orchestrator following the skill. The ledger counts native worker launch attempts, not each internal model inference or token. See [the security audit](docs/security-audit.md) for exact limits and findings.

## Files and state

Run records live outside the project in private fresh directories, defaulting to `~/.codex/arena-runs`. Symlinks, hardlinks, nonregular files, traversal, duplicate JSON keys, nonfinite values, malicious IDs/cards and unexpected solution paths are refused. Output is bounded, atomic and private. Live outputs require completed reservations and matching hashes. Candidate instructions cannot authorize new file scope, credentials, project edits or paid API calls.

The runtime uses Python 3.10+ and the standard library on POSIX. No model key or Python package install is needed. Code changes are proposals; a tournament does not apply them to the project. No secret detector can guarantee that user-supplied context is free of confidential data, so include only authorized relevant context.

## Install and check

Install a reviewed immutable commit of `skills/arena/` into the actual Codex user's skills directory. The standalone directory includes its license and credits. Do not silently overwrite an existing installation. It will be available on the next turn.

From the repository:

```sh
python3 -m unittest discover -s tests -v
python3 examples/run_fixture.py --output-dir /absolute/private/new-arena-fixtures
python3 scripts/verify_codex.py --cwd /absolute/workspace
```

Fixture output must be outside the project. Synthetic state is marked offline and cannot reserve native workers. Fixtures verify bookkeeping, not answer quality. The verifier uses local Codex discovery and prompt rendering, with positive/negative invocation-policy controls. It checks availability for explicit selection and exclusion from automatic context, without starting an AI turn.

Use `$arena --offline-check` for a safe local policy/quick-plan check, or `$arena <task>` to prepare a tournament for approval. See [SKILL.md](skills/arena/SKILL.md), [LICENSE](LICENSE), [CREDITS.md](CREDITS.md) and [CHANGELOG.md](CHANGELOG.md).
