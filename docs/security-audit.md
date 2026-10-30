# Security audit: native explicit-only Arena

Audit base: upstream `v0.3.2`, commit `adb206161c5d60d4dc9bbfa8757222744a93e568`.
Scope: the standalone Codex skill, Python bracket engine, local state and output
handling, invocation and approval policy, worker dispatch, packaging and offline
regression tests. No live tournament, external model API request, paid generation,
or user project edit is part of this audit.

## Upstream findings

| Finding | Risk | Evidence and correction |
| --- | --- | --- |
| Existing paths and symlinks were followed during initialization and output writes | High | `init --dir` accepted an existing directory and wrote `task.md`/`rubric.md`; state writes used a predictable `arena.json.tmp`. An attacker controlling those paths could redirect writes. Hardened I/O requires fresh private run directories, rejects symlinks throughout the path, rejects hardlinks and nonregular files, and uses private atomic output. |
| Saved state could redirect reads and inject instructions | High | Reproduced acceptance by upstream `validate_state` of an external `agent.solution`, a `r1-m01/../../../outside` match ID, and changed strategy instructions. The hardened validator constrains derived paths, canonical IDs, bracket invariants and original deterministic strategy cards. |
| Implicit activation and missing per-tournament approval | High | The upstream description allowed activation after an unsatisfactory answer. Its workflow normally ran small tournaments after merely displaying the planned call count. The fork requires explicit `$arena`, `allow_implicit_invocation: false`, and a separate exact-plan approval before live reservations. |
| Actual attempts were not bounded by the planned call count | High | Upstream instructions requested a second attempt for missing outputs and a third judge attempt. These calls were outside the plan. The fork records every actual attempt, including retries, before dispatch. The user explicitly approves the exact attempt budget and concurrency for each run; these cannot be increased by task text, workers or automatic fallback. Original field sizes and modes remain available when their budgets are explicitly approved. |
| Worker instructions exposed excessive capabilities | High | Upstream prompts allowed reading anything the task pointed to and writing throughout a shared run directory. The fork requires sanitized supplied context and native leaf workers returning text only. Read-only access authorized by the task remains available; workers are instructed to avoid credential access, project changes, external model APIs and nested spawning. The generic native interface does not enforce a separate OS sandbox for each worker; this boundary is instruction-level and is disclosed below. |
| Task/candidate text could masquerade as control instructions | High | Upstream task delimiters alone did not establish a trust boundary. The fork separates fixed worker security rules from untrusted task/candidate material and forbids material from changing approval, tools, models, dispatch, budgets or file scope. This is defense in depth, not proof that language models resist every injection. |
| Runtime artifacts inherited the process umask | Medium | Task, state, prompt and answer files were normally opened with ordinary `open(..., "w")`. The fork creates private directories and files independent of permissive umasks and bounds input/output sizes. |
| Installable archive omitted the invocation policy | Medium | The upstream fixed payload list did not include `agents/openai.yaml` or security support modules. The fork packages the complete reviewed runtime payload and preserves MIT attribution. |
| Unreserved or modified artifacts could be treated as worker results | Medium | The original engine treated any nonempty file at an expected path as completed work. The fork verifies completed reservation receipts and content hashes for live prerequisites and results; altered briefs must match the installed template and approved task before reservation. Offline synthetic fixtures are explicitly labelled and cannot receive live approval. |

The first three state-validation examples were reproduced using synthetic paths
and synthetic instruction text only. No credentials were read or disclosed.

## Trust and enforcement boundaries

The local engine performs bookkeeping; it contains no model SDK, HTTP client or
subprocess execution path. It cannot independently make a billed model request.
Live native Codex work can still consume the user's subscription usage.

Codex's skill loader enforces `allow_implicit_invocation: false` for skill
selection. The skill instructions additionally require the orchestrator to
verify the user's direct `$arena` instruction. Quoted text, repository files,
retrieved pages, another worker, and a prior run are not authorized sources of
invocation or approval. Installation approval is not tournament approval.

An exact approval phrase is an auditable guard, not cryptographic proof that a
human typed it. The orchestrating Codex instance must check the actual current user message
before calling the approval helper. It must apply the worker instructions and
use one durable reservation per actual launch, including each retry. Local files and skill
instructions cannot constrain an unrelated, malicious process running as the
same user or prevent an orchestrator from deliberately bypassing the helper.

The worker contract permits deliberately supplied task/context, authorized
read-only project context and candidate text. It forbids inherited unrelated
chat history, credentials, configuration secrets and arbitrary unrelated paths. The
orchestrator must not copy secrets into the task. This fork does not claim
automatic secret removal; no pattern detector can identify all confidential data.

Workers retain authorized read-only investigation. They are instructed not to
read credential files, call external model APIs, spawn children or modify the
project. The current native host does not
enforce those instructions by disabling every worker tool. Consequently this
release makes no claim of per-worker OS isolation. The engine itself never
launches network clients or processes and accepts worker outputs only as data.

## Verification

The offline regression suite exercises the bracket algorithms using synthetic
answers, malicious saved state, symlink and hardlink redirection, nonregular
files, permissions under permissive umasks, bounded reads, output preservation,
and approval/reservation behavior. Fixtures are labelled offline and cannot
obtain a live reservation. Installed-skill discovery and automatic-context
exclusion must also be checked against the user's real Codex executable without
starting a model turn.

Passing these tests is evidence of the exercised invariants. It is not a claim
of a penetration test of Codex itself, a real tournament's answer quality,
physical isolation from the same OS user, or a guarantee of token consumption.

## Native worker compatibility

The fork retains native Codex tournaments, the original bracket modes and field
sizes, with approval and actual-attempt accounting added around dispatch. A host
with native delegation is required for independent candidates. No external API
provider, API-key fallback or billed model subprocess is part of this skill.

The inspected generic native worker interface can retain tools, filesystem
access and collaboration tools. Therefore the skill's no-project-write,
no-secret-access and no-child-spawning worker requirements are instructions to
trusted cooperating Codex agents, not a separate OS or tool-level sandbox. The
engine enforces local path/state/output validation and dispatch bookkeeping; it
cannot technically stop a deliberately noncompliant worker or orchestrator from
using other host tools. This limitation must not be described as enforced worker
isolation or a guarantee against every prompt injection.

Verification uses synthetic outputs only. No real tournament was launched during
this audit; live quality, actual model token usage, and worker obedience were not
measured. Installed-runtime discovery and invocation-policy results are recorded
separately from local Python regression tests.

Final offline validation: `python3 -m unittest discover -s tests -q` completed
**86 tests successfully** in this audit workspace. The suite includes 41
adversarial security tests, original 100-agent synthetic tournament coverage,
all 2,160 strategy cards initializing and loading offline, lean/classic/baseline
fixtures, native-accounting flows with synthetic answers, bounded retries,
failed-job placeholders, exact approval and output-integrity checks. No worker
or model/API call was launched by these tests. `git diff --check` also passed.
The separate installed-runtime verifier records discovery and invocation-policy
results without model generation.
