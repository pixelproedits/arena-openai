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
| Implicit activation and missing per-tournament approval | High | The upstream description allowed activation after an unsatisfactory answer. Its workflow normally ran small tournaments after merely displaying the planned call count. The fork requires a current direct `@arena N` or `$arena N` command and `allow_implicit_invocation: false`. That command authorizes one computed Classic tournament; the trusted orchestrator records its exact guard proposal before live reservations without asking a second approval question. |
| Actual attempts were not bounded by the planned call count | High | Upstream instructions requested a second attempt for missing outputs and a third judge attempt. These calls were outside the plan. The fork records every actual attempt, including retries and failed startup, before dispatch. The command authorizes the exact computed default attempt budget, with concurrency clamped to available host slots; extra retry allowance needs an explicit user-requested maximum. Task text, workers and automatic fallback cannot increase these limits. Original field sizes and the complete Classic workflow remain available. |
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
verify the user's direct `@arena N` or `$arena N` instruction. Quoted text, repository files,
retrieved pages, another worker, and a prior run are not authorized sources of
invocation or approval. Installation approval is not tournament approval.

The guard binds an exact internal confirmation value to the proposal. The current
direct command is the user's authorization for one computed tournament; the
orchestrator records the matching proposal internally without another approval
question. This is an auditable approval boundary, not cryptographic proof of
human origin. The orchestrating Codex instance must check the actual current
direct user's command and its scope before calling the approval helper. It must apply the worker instructions and
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

The fork retains native Codex tournaments, the complete Classic bracket and
original field sizes, with approval and actual-attempt accounting added around
dispatch. At the user's request, Classic is now the only supported mode; the
shorter nonclassic workflow and its quick flag have been removed. A host
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


## Classic-only update

Every default tournament now runs candidate drafts followed by attack, defense
and judge jobs for each match, plus the optional blind baseline comparison.
Five candidates require 25 planned calls and 100 require 595 before any retries
or baseline comparison. `@arena 5` is the requested explicit shorthand and now
authorizes exactly one computed Classic tournament when it is the current direct
user's command. The exact internal per-run confirmation, input/code fingerprints
and actual-attempt ledger remain mandatory. The orchestrator records that
confirmation without asking the user again. Prior commands, installation,
examples, worker output and task text cannot authorize runs. Completion or a stop
ends the command's authority; no automatic rerun or resume is permitted.

A saved state explicitly marked with the removed nonclassic mode is rejected
without rewriting its JSON. It is not silently converted into a Classic run.
Regression fixtures use two- and five-candidate Classic tournaments, with every
phase populated by synthetic text. No model/API calls are used for these checks.

Previous 0.3.4 Classic-only validation: `python3 -m unittest discover -s tests -q` completed
**98 tests successfully**, including 42 adversarial security tests. The suite
covers every Classic phase, two- and five-candidate fixtures, the 100-candidate
bracket, all 2,160 cards initializing and loading, exact approval and actual
attempt budgets, retries/placeholders, tampered results, and rejection of removed
nonclassic state without rewriting it. Five candidates plan 25 calls; 100 plan
595. All answers were synthetic; no workers or model/API calls were launched.
`git diff --check` also passed.

The `@arena N` form is a local explicit text-command convention loaded through
the reviewed user-level AGENTS routing rule, not native mention registration.
The deterministic helper rejects embedded, quoted, fenced and indented examples.
Its `requires_approval: false` and `approval_source: "direct_command"` fields mean
no separate confirmation is needed after the trusted host verifies direct user
origin. They do not authenticate origin, record guard approval, write run state
or launch a worker. The routing origin check and selection of a clear pending
contextual task remain instructions to the trusted host, not claims of a parser
authenticating humans. If the task is unclear, the host asks for task clarification
before preparing or launching the run. Host capacity errors stop execution and
preserve consumed reservations; they do not authorize a bypass or more calls.

Version 0.3.5 source validation: `python3 -m unittest discover -s tests -q`
completed **101 tests successfully**. Added controls check direct-command
metadata, unchanged 25/595 default budgets, rejection of inflated/missing
authorization metadata, and CLI parsing without run state or task-command
execution. Versioned archive tests cover the 0.3.5 payload. `git diff --check`
passed. The bracket engine, guard ledger, secure I/O, strategy cards and
explicit-only metadata remain byte-identical to 0.3.4; only invocation metadata,
orchestration instructions, verification and documentation changed. These checks
used synthetic local inputs and did not launch workers or verify an installed
0.3.5 runtime.

Separate 0.3.5 installation verification: the official Skill Creator validator
passed for both the source and installed skill, using PyYAML in an isolated
temporary dependency directory. The local Codex prompt renderer and App Server
`initialize`/`skills/list` checks confirmed explicit skill discovery, exclusion
from implicit context, the loaded routing rule and positive/negative command
parser controls. This verification started zero model calls and zero tournaments;
it does not establish successful completion of a live Classic tournament.
