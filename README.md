# Arena - Classic-only native Codex fork

Based on upstream v0.3.2, commit `adb206161c5d60d4dc9bbfa8757222744a93e568`, with security hardening and the user's requested Classic-only interface. This fork is version **0.3.9**. MIT attribution is preserved.

## Use

In a Codex chat, select **Arena from the `$` menu**, then type:

```text
5
```

The number is both the competitor count and the requested concurrency. `@arena 20` requests 20 competitors with wave 20; it must not run autonomously in waves of 5. The parser reports both counts, the engine defaults wave to N, and live initialization and guard approval refuse any different wave. Actual simultaneous overlap depends on worker duration and host scheduling. Later phases naturally have fewer jobs. If N cannot fit the available host capacity, Arena reports the blocker before model work. Custom waves remain available only for plan-only calculations and permanently offline fixtures.

Arena uses the clear pending task already being discussed, or asks which task to examine. You can also append the task on the same line or the next line. Plain `$arena 5` and `@arena 5` remain supported. A bare number without a verified current Arena selection does not invoke the skill. No mode or specialist flags are required. `@arena` is a local explicit text shortcut, not a registered native mention/picker.

**Classic is the only mode:** candidates produce solutions, attack each other's answers, defend and revise their own, then a separate judge decides each match. Five candidates require 25 planned native worker-turn attempts; 100 require 595. These are job executions, not newly spawned threads. The removed shorter mode is not available in the engine, templates or fixtures. Old non-Classic records are refused unchanged.

Your current direct Arena menu selection plus `N`, or plain `@arena N`/`$arena N` command, authorizes exactly one computed Classic tournament and its original retries using native Codex usage. Arena states the task and usage allowance, then starts without a second approval question. A current direct instruction to continue a clearly identified pending Arena request also authorizes continuing that same task after a requested update, with a fresh code-bound proposal. Installing/updating the skill, quoted examples and prior commands alone cannot authorize a tournament. Completed tournaments are never rerun automatically.

## Explicit-only routing

`agents/openai.yaml` retains `policy.allow_implicit_invocation: false`. A narrow user-level `AGENTS.md` rule routes explicit menu selections and plain commands through the deterministic `invoke.py` helper. The reviewed block is [integration/codex-routing.md](integration/codex-routing.md). A serialized menu command must begin with the exact `[$arena]` link to the current helper's canonical `SKILL.md` path, followed by `N`; separate structured selection metadata can authorize parsing raw text beginning with `N`. Quoted/embedded links, other labels or paths, examples, retrieved files, ordinary critical tasks and other agents cannot invoke the skill. The helper returns `requires_approval: false` and `approval_source: "direct_command"`, meaning no separate confirmation is required when the host verifies the current direct user and selection origin. It does not authenticate origin, launch workers, write run state or record guard approval.

## Security and usage

All original strategy cards, odd-field byes, complete answers and retries remain supported. The planned-call ceiling defaults to 32 and rises automatically to the plan for an explicitly requested larger field. The complete original retry allowance is automatic: two attempts for each spawn/attack/defend job and three for each judge/final job. Thus five candidates plan 25 turns with up to 54 attempts; 100 plan 595 with up to 1,289. A clearly rejected answer to the same task, or an explicitly requested baseline, adds one planned turn and three attempts. An optional user-selected lower cap remains supported. Every turn, follow-up and failed dispatch consumes a new reservation; no extra approval is needed for original retries. Host failures are disclosed honestly.

Initial candidates are independent native threads with `fork_turns="none"`. When native follow-up is supported, each candidate keeps its own thread for its attack jobs and combined defense/revision jobs; every turn receives its complete generated brief and a new reservation. Judges are separate noncompetitors and may reuse judge-only threads for explicitly scoped match jobs. A candidate never judges, and the orchestrator never competes or judges. A blind final comparison uses an evaluator without previous candidate/judging context that could reveal answer identity. `N` counts competitors; it does not include the separate judges or promise exactly `N` total threads.

Before worker turns, the orchestrator checks exposed capabilities and reported concurrency for the exact requested N, and accounts for known resident/cumulative thread limits against the complete schedule, including retained candidates and separate judges. The open-thread config cap does not establish executing-turn capacity. Genuine close/release tools may free finished workers only after their outputs are saved and the host's release behavior is established; interrupting, marking done or archiving is not closure. Known capacity below N, or a missing required capability that makes the full schedule impossible, stops the run before model work. Unavailable limit metadata does not itself block execution: disclose the uncertainty briefly, use wave=N with a bounded candidate/judge pool and the guarded attempt budget, and stop honestly on a real capacity error. Never silently reduce the wave, shrink the field, drop phases, change settings or switch backend to evade capacity limits. See [the scheduling workflow](skills/arena/SKILL.md).

Original detailed Classic role instructions and model preferences are restored: Sol-tier competitors/attacks/defenses and Astra judges/final when available, preserving explicit user choices and disclosing unavailable selection. A third judge attempt uses a fresh noncompetitor worker. Inspected task-authorized checks may use the private run's scratch directory without a second approval; project/source/input files stay read-only, with no credentials, network writes or unrelated side effects. The orchestrator transports outputs without editorial analysis or hints and reads the winner only after completion.

Workers use existing native Codex usage, without an external model API, model subprocess, API-key fallback, provider switch or nested agents. The guard publishes canonical outputs. Worker tool rules, role/thread mapping, lifecycle checks and human approval origin depend on the trusted orchestrator: generic native workers are not an OS sandbox. The ledger counts worker-turn attempts, not spawned threads, internal inference turns or tokens. See [the security audit](docs/security-audit.md).

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
