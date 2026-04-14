---
name: stet
description: >-
  Use Stet to measure whether an AI coding change is safe to ship. Triggers
  whenever a developer asks about model comparison, config safety, shared
  instruction or policy rollout decisions, AGENTS.md or CLAUDE.md
  effectiveness, skill quality, repo eval setup, dataset building, repo
  onboarding, regression detection, benchmarking, or promote/rollback
  decisions. Also use when the user says things like "is this helping",
  "compare models on my repo", "set up evals", "onboard this repo", "build a
  dataset", "test this change", "what regressed", "keep improving until it
  passes", "which model should I use", "is it safe to ship", or "should this
  become the default". Even if the user does not mention Stet by name, use this
  skill whenever the question is about measuring, comparing, or gating AI
  coding behavior on real repo work.
---

# Stet

Stet is change control for AI coding behavior. It tells you whether a model,
config, skill, or workflow change is safe to ship by replaying real repo work
and scoring the output on correctness and quality.

Use this skill as the single entry point and treat it as the agent-facing
optimization interface. First install the object model and read path, then pick
the cheapest flow that preserves the decision semantics the operator needs.
Default to the manifest-backed rules flow when the change is a shared
instruction, policy, harness, docs, or model rollout rather than a throwaway
directional check.

For AGENTS.md, CLAUDE.md, shared skill, or harness-policy optimization, do not
let a fast `config-diff` result become the evidence used to keep, ship, or
declare a candidate better. `config-diff` can prune obviously bad throwaway
wording before a manifest exists, but the retained candidate must go through
`stet eval rules` before the agent claims improvement on rollout or custom
`agents_*` axes.

## Agent-Facing Optimization Interface

Stet is the Evaluation Function plus the context that teaches the agent how to
use it effectively. The coding agent is the optimizer. The skill's job is to
keep that optimizer inside a bounded search loop over real repo work.

Primitive model:

| Primitive | Agent-facing meaning |
|---|---|
| Harness Surface | All repo-local levers that can affect coding-agent behavior: instructions, model, harness provider, tool access, skills, system prompt, reasoning level, and related runtime context. |
| Task Corpus | Replayable real repo work used to measure candidate behavior. |
| Evaluation Function | The reproducible scoring protocol: tests as the gate plus quality dimensions, cost, provenance, validity, and confidence. |
| Search Space | The subset of Harness Surface levers the agent is allowed to change in this optimization run. It is both a tractability bound and a trust boundary. |
| Trial | One concrete candidate harness configuration evaluated against the Task Corpus. |
| Trial Result | The canonical machine-readable outcome for one Trial. In v1, this is persisted `eval_report.v1.json`. |
| Decision Policy | The rule for what to do next. In v1, read it from lifecycle and receipt fields such as `trust_state`, `gateable`, `promotable`, freshness, confidence, and `next_action`; do not invent a separate policy object. |
| Agent-Facing Optimization Interface | This contract: choose a bounded Trial, read the canonical Trial Result first, mutate only allowed levers, and use lower-level artifacts only for diagnosis. |

Canonical read path:

1. For active work, read `stet eval status --json`.
   Prefer `activity_state`, `active_work`, `blocking_tasks`,
   `last_artifact`, and `lifecycle`. Treat `STET_STATUS_SUMMARY ...` stderr
   lines as human-facing mirrors, not automation truth.
2. For completed work, read the persisted `eval_report.v1.json` for that flow
   when it exists. Ordinary output roots commonly persist it at
   `<root>/.stet/eval-report/eval_report.v1.json`; change-manifest rules flows
   persist it next to the resolved rules runtime under `.stet/eval-rules/...`.
   If it is not present or the locator is unclear, run
   `stet eval report --out <root> --json` or the matching
   `stet eval report --change-manifest <stet.change.yaml> --json` command to
   locate or materialize it.
3. Inside the Trial Result, read `decision_receipt` first for decision,
   confidence, readiness, grader coverage, task issue digests, and next action.
4. Read top-level `trial_context` next for Task Corpus, task selection,
   Harness Surface, Search Space, baseline, candidate, supporting evidence,
   freshness, and raw machine-recommendation refs.
5. Read top-level `quality`, `validity`, `evidence_quality`, `lifecycle`, and
   `arms` to interpret the verdict. A good score on degraded evidence is still
   degraded evidence.
6. Drill into lower-level artifacts only for diagnosis:
   `experiment.json` for compare evidence authority, `release.v1.json` for
   lifecycle authority, `task_decision.json` for task authority,
   `task_detail.json` / `trajectory.json` for inspectability, and logs for
   runtime failures. Do not reconstruct the primary verdict from summaries or
   pass rates when a Trial Result is available.

Legal optimization loop:

```
operator question
  -> identify Harness Surface and Search Space
  -> choose the cheapest valid Trial
  -> execute or resume the Stet flow
  -> read status or the persisted Trial Result
  -> state what you believe is causing the current bottleneck and what change would test it
  -> choose exactly one next action
  -> mutate one allowed lever, refresh baseline, gate/promote, inspect, or stop
```

Rules for the optimizer:

- Treat harness optimization as bounded search. If the desired edit is outside
  the current Search Space, stop and explain that the search boundary changed.
- Mutate one allowed lever at a time unless the operator explicitly asks to
  change the Search Space.
- Trust the Trial Result's `next_action` and lifecycle posture unless there is
  clear contradictory evidence. Mixed, stale, missing, or partial evidence
  fails closed to `inspect` or repair/resume.
- Distinguish release promotion from baseline refresh. Promotion changes
  rollout state; baseline refresh changes the frozen reference for future
  searches.
- Freeze baseline evidence when it will be reused. If a completed probe, smoke,
  or eval root is the stable reference for future candidate work, prefer
  `stet baseline freeze --from <root> --name <capability> --json` and later
  compare with `--baseline <reference>` instead of rerunning the baseline arm.
  This saves model/evaluator tokens and constrains the task slice, provenance,
  and Search Space for the next iteration. Skip only when the baseline evidence
  is stale, invalid, unrepresentative, or the operator needs fresh release-gate
  evidence.
- When pass rates tie, use quality dimensions above the gate: equivalence,
  code review, footprint/risk, cost, and custom graders.
- To discover common coding-outcome grader IDs, run
  `stet graders --repo <path> --json`. It lists built-in coding graders,
  bundled `craft` / `discipline` bundles, repo `quality:` config, and
  repo-local `rubrics/*.yaml` graders. For plan/research grading, write or
  select a custom rubric first; read
  [rubric-authoring](references/rubric-authoring.md).
- For first-time repo setup, ask once for the quality-grader posture before
  non-interactive init or the first smoke/probe/eval: recommended, standard, or
  custom. See [onboarding](references/onboarding.md).
- For compare-backed diagnosis, prefer `decision_receipt.tasks[*]` issue
  summaries, risks, grader coverage, and task flips before opening per-task
  artifacts by hand.
- For LLM-as-a-judge provenance, read both `evaluator_model` and
  `evaluator_model_status` from
  `decision_receipt.tasks[*].{baseline,candidate}_graders.<grader_id>`, and
  read aggregate model sets plus status from `decision_receipt.graders`.
- For custom graders, verify expected grader IDs are present in
  `decision_receipt.compare.grader_coverage`, `experiment.json.graders`, or arm
  `decision_metrics.graders` before issuing a verdict. Missing expected grader
  coverage is degraded evidence.
- For installed MVP binaries, use the private dist repo update flow:
  `stet --version`, `stet update`, or `stet update --version <tag>`. Pilot
  users need access to `benredmond/stet-dist`, not the private source repo.
  `stet update` refreshes both the binary and local Harbor support agents.
- For the shipped Stet agent skill, use the same private dist repo:
  `npx skills add git@github.com:benredmond/stet-dist.git --skill stet`.
  Release automation syncs `skills/stet` into
  `distribution/stet-dist/skills/stet` before publishing dist collateral.
- On command failure, read status when possible, fail closed, and use the
  recovery patterns in [operator-contract](references/operator-contract.md).

Multi-turn state:
  Track the current output root path or change manifest across turns. The root
  or manifest is the anchor for every later status, report, repair, rerun, or
  lifecycle command.

Human receipts:
  Terminal receipts are compact human-facing projections of the machine
  contract. Use them to answer the operator and offer keyed actions, but do not
  treat them as the primary agent API. See
  [operator-contract](references/operator-contract.md).

HTML report:
  Every persisted `eval_report.v1.json` has a sibling `eval_report.v1.html` —
  a self-contained page the operator can open in a browser for a visual
  breakdown of the verdict, metrics, evidence quality, and per-task results.
  After any completed eval flow, surface the HTML path to the operator so they
  can review the results visually. The HTML file lives in the same directory as
  the JSON artifact.

## Route by Intent

```
user intent
     │
     ├─ "Is this AGENTS.md / CLAUDE.md / shared skill helping?" ──► rules flow
     ├─ "Is this change safe to ship?" ────────► rules flow or quick-probe
     ├─ "Compare models/settings on my repo" ──► context, then reuse or eval run
     ├─ "Compare baseline vs candidate" ───────► eval compare
     ├─ "What is this run doing?" ─────────────► eval status
     ├─ "Set up evals for this repo" ──────────► onboarding
     ├─ "Build a large dataset (50+)" ─────────► dataset-build (heavy pipeline)
     ├─ "Is my shared skill better?" ───────────► rules skill loop
     ├─ "Is my plan/research better?" ──────────► rubric authoring
     ├─ "Help me write a custom grader" ───────► rubric authoring
     ├─ "Keep improving until it passes" ──────► iterative improvement
     ├─ "Promote / monitor / roll back" ───────► release lifecycle
     └─ "Roll out a shared rules/config change" ──► rules flow
```

When ambiguous, ask one question: "Are you testing a config change, comparing
models, setting up a repo, improving a skill, or checking a release?"

| What the user is asking | Start here | Read next |
|---|---|---|
| "Is this AGENTS.md / CLAUDE.md / shared skill / policy helping?" | `stet manifest resolve` then `stet eval rules` | [rules-flow](references/rules-flow.md) |
| "I want the fastest local directional read on a file change" | `stet probe --file` or `stet eval config-diff` | [quick-probe](references/quick-probe.md) |
| "Try this candidate on my repo" | `stet probe` | [quick-probe](references/quick-probe.md) |
| "Is this change safe to ship?" | `stet manifest resolve` then `stet eval rules` for shared behavior changes; otherwise `stet probe` | [rules-flow](references/rules-flow.md), [quick-probe](references/quick-probe.md) |
| "Compare models / reasoning levels / harness settings on my codebase" | `stet context --json`, then reuse/report or pinned `stet eval run`; use `stet eval smoke` only for first-run/no-history cases | [full-evals](references/full-evals.md), [compare-and-checkin](references/compare-and-checkin.md) |
| "Compare baseline vs candidate" | `stet eval compare` | [compare-and-checkin](references/compare-and-checkin.md) |
| "What is this run doing?" | `stet eval status` | [compare-and-checkin](references/compare-and-checkin.md) |
| "Repair missing additive grader coverage on a finished run" | `stet runs repair-ai-coverage` or `stet runs regrade-graders` | [compare-and-checkin](references/compare-and-checkin.md) |
| "Resume an incomplete rules compare" | `stet eval rules resume` | [rules-flow](references/rules-flow.md) |
| "Set up evals for this repo" | author `.stet/harbor.Dockerfile` + `.stet/stet.harness.yaml`, then `stet init` and `stet suite discover` | [onboarding](references/onboarding.md) |
| "Build a large dataset (50+ tasks)" | `stet suite discover` + `stet suite build` | [dataset-build](references/dataset-build.md) |
| "Is my shared skill better?" | `stet eval rules skill` | [rules-flow](references/rules-flow.md), [iterative-improvement](references/iterative-improvement.md) |
| "Is my research / plan better?" | choose or write custom rubrics | [rubric-authoring](references/rubric-authoring.md) |
| "Help me write a custom grader" | rubric design + calibrate | [rubric-authoring](references/rubric-authoring.md) |
| "Keep improving until it passes" | scored improve-eval loop | [iterative-improvement](references/iterative-improvement.md) |
| "Promote / monitor / roll back" | lifecycle commands | [release-lifecycle](references/release-lifecycle.md) |
| "I need a manifest-backed rollout" | `stet manifest resolve` then `stet eval rules` | [rules-flow](references/rules-flow.md) |

## Golden Paths

| Path | When to use | Flow |
|---|---|---|
| Rules rollout | Shared instruction/policy/docs/harness/model change control | `manifest resolve` -> `eval rules` -> `status` -> `report` -> `promote` -> `baseline freeze` |
| Quick probe | Fastest repo-local answer | `stet probe` -> `stet eval report` |
| Repair a finished run | Recover additive grader coverage without rerunning the harness | `runs repair-ai-coverage` / `runs regrade-graders` -> `eval status` -> `eval report` |
| Config A/B (prefilter only) | Fast file-level directional read without rollout state | `stet probe --file` / `stet eval config-diff` |
| Context-first selection | Model, reasoning-level, or harness-setting choice on a repo with Stet history | `stet context --json` -> reuse/report or pinned `eval run` |
| Quick smoke | First multi-model read with no usable Stet history | `stet eval smoke` |
| Pairwise compare | Baseline vs candidate | `stet eval compare` -> `stet eval report` |
| Baseline-first | Freeze reusable evidence, then compare candidates without rerunning the baseline arm | `stet baseline freeze` -> `stet eval compare --baseline` |
| Rules skill loop | Replay-backed shared skill improvement on the canonical rules surface | `stet eval rules skill` -> `stet eval status` -> `stet eval report` |
| Repo onboarding | New repo, no dataset yet | author harness Dockerfile -> `stet init` -> `suite discover` -> `suite build` |
| Dataset eval | Reusable benchmark | `suite build` -> `eval run` -> `report` |
| Workbench probe | Iterative artifact improvement | `workbench probe` -> `report` -> `workbench gate` |
| Release lifecycle | Promote, monitor, rollback | gate -> `promote` / `monitor` / `rollback` |

## Routing Rules

- For quick safety reads that do not need rollout state or manifest
  provenance, start with `stet probe`. Escalate only when broader coverage is
  needed.
- For shared AI behavior changes that may become rollout state, default to the
  manifest-backed rules flow (`stet manifest resolve` then `stet eval rules`
  with `stet.change.yaml` + `stet.suite.yaml`). This includes `agents_md`,
  `claude_md`, `skill_diff`, `docs_glob`, `harness_bundle`, and
  `model_update` treatments. Read `eval_report.v1.json` after the run: rules
  reports include bounded treatment diffs for AGENTS.md, CLAUDE.md, and skill
  file changes, plus model from/to summaries for model-update trials.
- For iterative AGENTS.md / CLAUDE.md prompt search, use the same rule at each
  decision boundary: cheap reads may eliminate throwaway candidates, but any
  candidate you keep, recommend, promote, baseline, or describe as improving
  shared agent behavior needs a manifest-backed rules result. State explicitly
  when earlier `config-diff` evidence was only a directional prefilter.
- For file-level A/B on AGENTS.md, CLAUDE.md, skill files, or adjacent policy
  files, prefer the rules flow whenever the operator is asking a release-style
  question such as "is this helping", "is this safe to ship", "should we roll
  this out", or "what should become the default". Fall back to `stet probe
  --file` or `stet eval config-diff` only for quick directional reads,
  pre-manifest iteration, or cases where rollout provenance does not matter.
- For raw file A/B without manifests, use `--baseline-file` /
  `--candidate-file` with `--logical-path`.
- For non-code outputs such as skills, research, or plans, choose or write
  custom rubric YAML before running a comparison.
- For repo-managed skills under `.agents/skills` or `.claude/skills`, treat the
  changed skill as the target and the full managed skills tree as the frozen
  runtime envelope. Precedence: `.agents/skills` over `.claude/skills`.
- Prefer `--json` when the output feeds another agent step.
- Start with the cheapest surface that answers the question without discarding
  provenance or release-state semantics the operator is asking for.
- If a Claude Code run reports that `/login` is required, treat it as a host
  auth/bootstrap issue before interpreting eval quality. Prefer
  `claude setup-token`, then export `CLAUDE_CODE_OAUTH_TOKEN` with the printed
  token. Stet also accepts `CLAUDE_CODE_CREDENTIALS_JSON_B64`,
  `CLAUDE_CODE_CREDENTIALS_JSON`, `ANTHROPIC_API_KEY`,
  `ANTHROPIC_AUTH_TOKEN`, or the macOS Keychain item named
  `Claude Code-credentials`, and fails before launching Claude when none are
  available.
- If `stet eval report` shows
  `harbor_claude_code_concurrent_setup_cache_skew`, treat candidate setup
  failures as infrastructure risk before interpreting treatment quality.
  Harbor `--force-build` still reuses Docker layers, so the second compare arm
  can start Claude Code installs more synchronously than the first. Prefer
  `--tb-concurrency 2` for Claude Code compare runs and use `runner.tb_args`
  memory overrides when pods still OOM.
- Commercial access control gates eval execution, replay, evaluator AI, grader
  repair, and monitor reruns. If a user hits a Stet license/trial denial, direct
  them to `stet auth login` and use `stet auth status` to confirm email,
  entitlement, trial expiration, and commercial workflow availability. Preserve
  local command guidance for ungated flows such as `suite discover`,
  `suite build`, `eval status`, `eval report`, rollback, and local artifact
  inspection.
- In cost-constrained compare or baseline-first workflows, check `stet context --json` first and inspect `artifact_reuse` before proposing a fresh eval. Reuse an exact comparable root when one exists; when that root is likely to anchor repeated candidate work, freeze it as a baseline before the next compare. If only a near match exists, explain the drift explicitly before spending more.
- For model, reasoning-level, or harness-setting selection on a repo with Stet
  history, run `stet context --repo <repo> --json` before proposing a fresh
  eval. Prefer completed exact comparable roots, then pinned reuse of prior task
  selection, then a fresh dataset-backed run. Treat `stet eval smoke` as a
  first-run bootstrap path, not the default for repos with prior Stet evidence.
- Treat reasoning level, sandbox, tool access, prompt profile, and agent kwargs
  as Harness Surface levers. Do not collapse them into a plain `--models`
  comparison unless the CLI supports distinct arm identities for those levers.
  If the requested arms share the same model id, keep the task slice fixed and
  vary only the requested harness lever.
- For pinned reuse on repo-local datasets, `--pinned-dataset-key` is not limited to weekly keys. Reuse `task_selection.dataset_key` from onboarding receipts or prior output roots when it is available, and otherwise pass the repo-local key explicitly.
- In baseline-first compare, `--task-id` narrowing works for benchmark baselines but not for replayable baseline snapshots. Treat those as different baseline kinds before proposing the next command.
- For completed Trial Result reads, prefer persisted `eval_report.v1.json` when
  present. Read `decision_receipt` for decision/confidence/readiness/next action
  and top-level `trial_context` for task-corpus, task-selection,
  harness-surface, search-space, baseline, candidate, supporting-evidence,
  freshness, and raw machine-recommendation refs before opening sibling
  artifacts or inferring from summary pass rates.
- For compare-backed operator diagnosis, prefer `decision_receipt.tasks[*]`
  issue summaries/risks before opening per-task artifacts by hand.
- For active run reads, prefer `activity_state`, `active_work`,
  `blocking_tasks`, `last_artifact`, and `lifecycle` from
  `stet eval status --json`. Treat `STET_STATUS_SUMMARY ...` stderr lines as
  operator-facing mirrors, not the automation contract.
- For incomplete compare roots with missing requested grader coverage, prefer
  the ordered recovery commands projected by `stet eval status` /
  `stet eval report` over manual artifact inspection. Use the surfaced
  `stet runs repair-ai-coverage ...` step before `stet runs regrade-graders ...`
  when both built-in AI coverage and custom rubric coverage are missing.
- For incomplete rules-backed compares, prefer `stet eval rules resume
  --change-manifest <stet.change.yaml>` or `--rules-root <dir>` before manually
  constructing sibling arm roots or running repair commands. Do not rerun
  `stet eval rules` to recover partial evidence; use `--restart` only when the
  operator intentionally discards existing evidence for that change manifest.
- For AGENTS.md, CLAUDE.md, skill, or policy compares where custom graders are
  part of the decision, verify the expected custom grader IDs are present in
  `decision_receipt.compare.grader_coverage`, `experiment.json.graders`, or arm
  `decision_metrics.graders` before issuing a verdict. If custom grader
  coverage is missing, report the evidence gap and fail closed to `inspect`.
- For run/model comparison surfaces, prefer `runs.<model>.decision_metrics`
  and `decision_metrics.graders` over legacy `validation_metrics` or scraping
  per-task `validation.json`.
- When pass rates tie, check quality dimensions above the gate (equivalence,
  review, footprint, cost) — that is where differentiation lives.
- When the operator is iterating on AGENTS.md, CLAUDE.md, or a skill against a
  frozen baseline, distinguish release promotion from baseline promotion.
  Release promotion changes rollout state; baseline promotion refreshes the
  frozen "current" reference used for future compares.
- After a compare against a frozen baseline returns a clear winner and the
  workflow is baseline-first rather than release-gated, explicitly recommend
  baseline promotion as the default next action.
- When a command finishes in a non-terminal state, offer keyed next actions.

## Lifecycle

```
                    ┌──────────┐
                    │ onboard  │
                    └────┬─────┘
                         │ [m] smoke / [p] probe
                         ▼
    [v] revise ──► ┌──────────┐ ◄── [r] rerun
                   │  probe   │
                   └──┬────┬──┘
                      │    │
            [g] gate  │    │ [b] baseline
                      │    ▼
                      │  ┌─────────┐
                      │  │ compare │ ◄── [r] rerun
                      │  └────┬────┘
                      │       │ [g] gate
                      ▼       ▼
                ┌───────────────────┐
                │       gate        │
                └────────┬──────────┘
                         │ [p] promote
                         ▼
                ┌───────────────────┐
                │     promoted      │
                └───┬───────────┬───┘
                    │           │
          [m] monitor     [x] rollback
                    ▼           ▼
              ┌──────────┐  ┌──────────┐
              │ monitor  │  │ revoked  │
              └──────────┘  └──────────┘
```

Evidence grades:

| Step | Decision grade | Produces |
|---|---|---|
| Onboard | `exploratory` | dataset + onboarding receipt |
| Probe | `exploratory` → `gateable` | bounded compare verdict |
| Compare | `exploratory` | pairwise experiment |
| Gate | `gated` | release record with trust/rollout |
| Promote | `promoted` → `monitorable` | promoted release |

Each step produces evidence the next step requires. Onboarding → probe → gate.

## Decision Rules

- Fast answer wanted → `probe` or `eval smoke`
- Baseline-vs-candidate → `eval compare`
- New repo → `suite discover` + `suite build`, then propose a starter slice
- "Safe to ship?" → gated flow before promote
- Improving skill quality → custom artifact graders via workbench
- Scored improvement loop → workbench with
  [iterative-improvement](references/iterative-improvement.md)
- Rubric noisy or too coarse →
  [rubric-authoring](references/rubric-authoring.md)
- Pass rates tie → check quality dimensions above the gate
- Incomplete compare → read `compare_state.next_action`, not the recommendation
- Clear compare win in a baseline-first loop → recommend baseline promotion
  before suggesting another iteration

## Gotchas

- `probe` answers the question directly. Gate is optional, not the default.
- `INSPECT` and `HOLD` are completed decision states, not broken runs.
- Quiet logs are normal, and Stet runs can take a while. Tell the operator to
  be patient, and use `stet eval status` before assuming a stall.
- If `stet eval status --json` and `stet eval report --json` disagree on a
  compare root, fail closed to inspect instead of inventing a clean verdict.
- Tests are the gate, not the source of truth. Binary pass rate cannot
  differentiate frontier models. Quality dimensions above the gate are where
  differentiation lives.
- AGENTS.md/CLAUDE.md treatments are disk overlays, not prompt injection. Harbor
  stages them outside `/app`, installs through existing symlink targets, and
  commits the overlay baseline so captured patches exclude treatment churn.

## Read As Needed

Only load the reference doc that matches the current routing decision:

- [references/operator-contract.md](references/operator-contract.md)
  Receipt format, keyed actions, reporting rules, error handling.
- [references/quick-probe.md](references/quick-probe.md)
  Probe, file-mode config checks, config-diff, quick smoke.
- [references/full-evals.md](references/full-evals.md)
  Eval run, eval smoke, suite discover/build, rules-backed rollout.
- [references/compare-and-checkin.md](references/compare-and-checkin.md)
  Pairwise compare, eval status, inspect handoff, recovery.
- [references/rules-flow.md](references/rules-flow.md)
  Manifest resolve, eval rules, manifest-backed decisions.
- [references/release-lifecycle.md](references/release-lifecycle.md)
  Gate, promote, monitor, rollback.
- [references/onboarding.md](references/onboarding.md)
  First-run repo setup, dataset building, starter-slice approval.
- [references/dataset-build.md](references/dataset-build.md)
  Heavy dataset builds, Docker debug loops, ecosystem templates, scaling.
- [references/rubric-authoring.md](references/rubric-authoring.md)
  Custom grader design, calibration, scored rubric templates.
- [references/iterative-improvement.md](references/iterative-improvement.md)
  Scored improve-eval-log-repeat loop, loop log, stop rules.
- [references/examples.md](references/examples.md)
  Complete multi-turn interaction traces showing the agent protocol.
