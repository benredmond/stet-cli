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
optimization interface. Use the object model and canonical read path, then pick
the cheapest flow that preserves the decision semantics the operator needs.
Default to the manifest-backed rules flow when the change is a shared
instruction, policy, harness, docs, or model rollout rather than a throwaway
directional check.

## Agent-Facing Optimization Interface

Stet is the Evaluation Function plus the context that teaches the agent how to
use it effectively. The coding agent is the optimizer. The skill's job is to
keep that optimizer inside a bounded search loop over real repo work.

Primitive model:

| Primitive | Agent-facing meaning |
|---|---|
| Harness Surface | Repo-local levers that affect coding-agent behavior: instructions, model, harness, tool access, skills, prompt, reasoning, and runtime context. |
| Task Corpus | Replayable real repo work used to measure behavior. |
| Evaluation Function | Tests as the gate, plus quality dimensions, cost, provenance, validity, and confidence. |
| Search Space | The subset of Harness Surface levers allowed to change. It is both tractability bound and trust boundary. |
| Trial | One candidate harness configuration evaluated against the Task Corpus. |
| Trial Result | Canonical machine-readable outcome for one Trial, persisted as `eval_report.v1.json` in v1. |
| Decision Policy | Read from lifecycle and receipt fields such as `trust_state`, `gateable`, `promotable`, freshness, confidence, and `next_action`. Do not invent a separate policy object. |

Canonical read path:

1. For active work, read `stet eval status --json`.
   Prefer `activity_state`, `active_work`, `blocking_tasks`,
   `last_artifact`, and `lifecycle`. If `activity_state` is
   `waiting_on_quota`, read `retry_after`, `completed_tasks`,
   `remaining_tasks`, and `next_action`; the active Stet process is waiting and
   will resume missing retryable work automatically. Treat
   `STET_STATUS_SUMMARY ...` stderr lines as human-facing mirrors, not
   automation truth.
2. For completed work, read the persisted `eval_report.v1.json` for that flow
   when it exists. Ordinary output roots commonly persist it at
   `<root>/.stet/eval-report/eval_report.v1.json`; change-manifest rules flows
   persist it next to the resolved rules runtime under `.stet/eval-rules/...`.
   If it is not present or the locator is unclear, run
   `stet eval report --out <root> --json` or the matching
   `stet eval report --change-manifest <stet.change.yaml> --json` command to
   locate or materialize it.
3. Inside the Trial Result, read `decision_receipt` first for recommendation,
   confidence, readiness, grader coverage, task issue digests, and next
   action. The verdict string lives on `decision_receipt.recommendation`
   (and is mirrored on the top-level `lifecycle.decision` sibling);
   `decision_receipt` does not
   carry a top-level `decision` field.
4. Read top-level `trial_context` next for Task Corpus, task selection,
   Harness Surface, Search Space, baseline, candidate, supporting evidence,
   freshness, and raw machine-recommendation refs.
5. Read top-level `quality`, `validity`, `evidence_quality`, `lifecycle`, and
   `arms` to interpret the verdict. A good score on degraded evidence is still
   degraded evidence.
   When evidence is not decision-grade, check
   `evidence_quality.directional_read`. A `usable` or `limited` directional
   read can guide iteration or prefilter candidates, but should not be treated
   as a promote, rollback, or superiority decision without more tasks or clean
   validity.
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
  fails closed for promotion and rollback: do not call it safe to ship. If the
  operator requested optimization and `evidence_quality.directional_read.status`
  is `usable` or `limited`, treat `inspect` as a caveated iteration signal:
  explain the evidence limit, choose one bounded next lever or scale-up rerun,
  and continue the loop. If status or report exposes
  `repair.code=GRADE_CUSTOM_REPAIRABLE`, run the emitted
  `stet eval rules repair ... --json` command; it reuses validation artifacts
  and reruns only the affected custom grader coverage. Typed grader-failure
  counters (`malformed_count`, `parse_attempt_count`, `repairable_count`, and
  `public_failure_kind_counts`) are surfaced per arm on
  `eval status`/`eval report` grader coverage and per grader on the
  decision-receipt `compare.graders`/`run.graders` entries; canonical kinds
  are `malformed_json`, `schema_invalid`, `range_invalid`,
  `unsupported_signal`, `timeout`, `auth`, `config`, `unknown`.
- When a rules change declares `change.rules.checkpoint_suite` or
  `change.rules.holdout_suite`, keep normal optimization on the iteration suite.
  Use checkpoint sparingly as validation feedback, not the target. Run holdout
  only for the finalist; read `study.readiness` in `eval_report.v1.json`.
  A declared holdout must pass before the result is decision-grade or promotable.
- For rules and rules-skill runs, `no_gold_pass_commands`,
  `all_commands_ignored_gold_failure_mode_unset`, or a candidate smoke
  preflight failure before `experiment.json` means the selected replay
  evidence is not gold-valid yet. Treat it as a dataset/slice validity problem,
  not model-quality evidence or proof that current-checkout tests are broken;
  diagnose why the verifier failed before choosing a bounded next action.
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
  evidence. For first-in-repo model, reasoning, or harness-setting results,
  make baseline freeze an explicit next action whenever validity is ok and the
  run is likely to anchor future comparisons, even if the evidence is only
  directional; label the frozen baseline's sample size and confidence, and do
  not equate baseline refresh with promote-grade evidence.
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
- When the suite manifest does not carry an `eval:` stanza (fixture suites,
  read-only / shared repos, ad-hoc replays), pass `--grader-ai-cmd "<cmd>"
  --grader-ai-model-id <id>` on `stet eval rules plan` / `launch` / `skill`
  to supply the independent evaluator for LLM-backed graders (`equivalence`,
  `code_review`, craft/discipline). Both flags must be set together. Note
  that `--no-quality` only drops the auto-bundled craft/discipline graders;
  the default `equivalence` and `code_review` graders remain LLM-backed and
  still require an evaluator.
- For compare-backed diagnosis, prefer `decision_receipt.tasks[*]` issue
  summaries, risks, grader coverage, and task flips before opening per-task
  artifacts by hand.
- For LLM-as-a-judge provenance, read both `evaluator_model` and
  `evaluator_model_status` from
  `decision_receipt.tasks[*].{baseline,candidate}_graders.<grader_id>`, and
  read aggregate model sets plus status from `decision_receipt.graders`. Also
  check `decision_receipt.graders.profile_status` and `grader_profile`; treat
  `mixed` or `missing_legacy` profile status as inspect-only evidence.
- For custom graders, verify expected grader IDs are present in
  `decision_receipt.compare.grader_coverage`, `experiment.json.graders`, or arm
  `decision_metrics.graders` before issuing a verdict. Explicitly requested
  grader coverage that is missing or asymmetric should fail closed to
  `inspect`; one-sided graders are coverage evidence, not comparison math.
- For installed MVP binaries, use the private CLI repo update flow:
  `stet --version`, `stet update`, or `stet update --version <tag>`. Pilot
  users need access to `benredmond/stet-cli`.
  `stet update` refreshes both the binary and local Harbor support agents.
- Harbor-installed Codex/Claude support agents are baked into
  `.stet/harbor.Dockerfile` (`ARG BAKE_CLAUDE_CODE` / `ARG BAKE_CODEX`, both
  default on; both fetch the latest published version on each fresh build).
  `/logs/agent/harness_cli_cache.json` reports `status: skipped_image_baked`
  with `baked_binary_path` and `baked_binary_version` — that is the healthy
  default. The host `--harness-cli-cache auto` cache only kicks in for
  unbaked Dockerfiles or operator-pinned versions; `--harness-cli-cache off`
  is for cold-start probes against unbaked images, and 24h TTL refreshes
  apply unless overridden by `STET_HARNESS_CLI_CACHE_TTL_SEC`. Inspect
  `runner_runtime.v1.json` plus `harness_cli_cache.json` before treating
  setup time as model signal.
- To run Codex model-under-test traffic through codex-lb, start codex-lb on a
  host address reachable from Harbor containers, export `CODEX_LB_API_KEY`,
  and optionally export `CODEX_LB_BASE_URL` (defaults to
  `http://host.docker.internal:2455/backend-api/codex` for Harbor). The Codex
  Harbor support agent automatically injects the transient Codex provider
  config; keep independent graders on `--grader-ai-cmd` so codex-lb does not
  judge itself.
- For the shipped Stet agent skill, use the same private CLI repo:
  `npx skills add git@github.com:benredmond/stet-cli.git --skill stet`.
  Release automation syncs `skills/stet` into the distribution skill snapshot
  before publishing dist collateral.
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

Result interpretation:
  The agent owns interpretation. A completed eval, failed eval, inspect-state
  eval, or check-in is not finished until the agent has read the relevant JSON
  evidence and translated it into an operator-facing judgment.

  Do not respond with only report paths, HTML paths, commands to run, or raw
  status output. First answer the operator's question with the verdict,
  confidence, lifecycle/readiness state, decisive metric deltas, evidence
  quality, effective grader coverage, main risks, and one recommended next
  action. Surface JSON/HTML paths only as supporting evidence.

  For active runs, read status JSON and explain liveness, phase, progress,
  blockers, latest artifact, and whether wait, inspect, resume, or repair is
  next. For completed or inspect-state runs, read or materialize the Trial
  Result, then read `decision_receipt`, `trial_context`, `quality`, `validity`,
  `evidence_quality`, `lifecycle`, and `arms` before summarizing.

  If status and persisted evidence disagree, do not stop at the first payload.
  Follow `evidence_refs`, the rules runtime, and any persisted
  `eval_report.v1.json` / compare report, then explain the contradiction and
  fail closed to inspect when the evidence remains degraded.

HTML report:
  Every persisted `eval_report.v1.json` has a sibling `eval_report.v1.html` -
  a self-contained page the operator can open in a browser for a visual
  breakdown of the verdict, metrics, evidence quality, and per-task results.
  After interpreting any completed eval flow, surface the HTML path as
  supporting evidence so the operator can review the results visually. The HTML
  file lives in the same directory as the JSON artifact.

## Route by Intent

When ambiguous, ask one question: "Are you testing a config change, comparing
models, setting up a repo, improving a skill, or checking a release?"

| What the user is asking | Start here | Read next |
|---|---|---|
| "Is this AGENTS.md / CLAUDE.md / policy helping?" | `stet manifest resolve`, `stet eval rules plan`, then `stet eval rules` | [rules-flow](references/rules-flow.md) |
| "Does adding this new skill help?" / "with skill vs without skill" | New-skill A/B: keep baseline skill-absent or effectively empty, use behavior graders, then `stet eval rules` or a frozen-baseline compare | [rules-flow](references/rules-flow.md) |
| "I want the fastest local directional read on a file change" | `stet probe --file` or `stet eval config-diff` | [quick-probe](references/quick-probe.md) |
| "Try this candidate on my repo" | `stet probe` | [quick-probe](references/quick-probe.md) |
| "Is this change safe to ship?" | `stet manifest resolve`, `stet eval rules plan`, then `stet eval rules` for shared behavior changes; otherwise `stet probe` | [rules-flow](references/rules-flow.md), [quick-probe](references/quick-probe.md) |
| "Compare models / reasoning levels / harness settings on my codebase" | `stet context --repo <repo> --json`, then reuse/report or pinned `stet eval run`; use `stet eval smoke` only for first-run/no-history cases | [full-evals](references/full-evals.md), [compare-and-checkin](references/compare-and-checkin.md) |
| "Compare baseline vs candidate" | `stet eval compare` | [compare-and-checkin](references/compare-and-checkin.md) |
| "What is this run doing?" | `stet eval status` | [compare-and-checkin](references/compare-and-checkin.md) |
| "Repair missing additive grader coverage on a finished run" | `stet runs repair-ai-coverage` or `stet runs regrade-graders` | [compare-and-checkin](references/compare-and-checkin.md) |
| "Why is this root taking so much disk?" / "Can I reclaim raw artifacts?" | `stet artifacts status --root <root>` then `stet artifacts compact --root <root>` if not pinned | [compare-and-checkin](references/compare-and-checkin.md) |
| "Repair or resume an incomplete rules compare" | `stet eval rules repair` (`resume` remains accepted) | [rules-flow](references/rules-flow.md) |
| "Set up evals for this repo" | author `.stet/harbor.Dockerfile` + `.stet/stet.harness.yaml`, then `stet init` and `stet suite discover` | [onboarding](references/onboarding.md) |
| "Build a large dataset (50+ tasks)" | `stet suite discover` + `stet suite build` | [dataset-build](references/dataset-build.md) |
| "Is my shared skill revision better?" | `stet eval rules skill --plan --skill <path> --repo <path> --model <id> --goal "<...>" --out <dir>`, then `stet eval rules skill` against the committed prior skill | [rules-flow](references/rules-flow.md), [iterative-improvement](references/iterative-improvement.md) |
| "Is my research / plan better?" | choose or write custom rubrics | [rubric-authoring](references/rubric-authoring.md) |
| "Help me write a custom grader" | rubric design + calibrate | [rubric-authoring](references/rubric-authoring.md) |
| "Keep improving until it passes" | scored improve-eval loop | [iterative-improvement](references/iterative-improvement.md) |
| "Promote / monitor / roll back" | lifecycle commands | [release-lifecycle](references/release-lifecycle.md) |
| "I need a manifest-backed rollout" | `stet manifest resolve`, `stet eval rules plan`, then `stet eval rules` | [rules-flow](references/rules-flow.md) |

## Golden Paths

| Path | When to use | Flow |
|---|---|---|
| Rules rollout | Shared instruction/policy/docs/harness/model change control | `stet manifest resolve` -> `stet eval rules plan` -> `stet eval rules` -> `stet eval status` -> `stet eval report` -> `stet promote` -> `stet baseline freeze` |
| Quick probe | Fastest repo-local answer | `stet probe` -> `stet eval report` |
| Repair a finished run | Recover additive grader coverage without rerunning the harness | `stet runs repair-ai-coverage` / `stet runs regrade-graders` -> `stet eval status` -> `stet eval report` |
| Config A/B (prefilter only) | Fast file-level directional read without rollout state | `stet probe --file` / `stet eval config-diff` |
| Context-first selection | Model, reasoning-level, or harness-setting choice on a repo with Stet history | `stet context --repo <repo> --json` -> reuse/report or pinned `stet eval run` |
| Quick smoke | First multi-model read with no usable Stet history | `stet eval smoke` |
| Artifact retention | Inspect or reclaim raw rescue artifacts | `stet artifacts status --root <root>` -> `stet artifacts compact --root <root>`; use `pin` / `unpin` for operator-retained roots |
| Pairwise compare | Baseline vs candidate | `stet eval compare` -> `stet eval report` |
| Baseline-first | Freeze reusable evidence, then compare candidates without rerunning the baseline arm | `stet baseline freeze` -> `stet eval compare --baseline` |
| New skill A/B | Check whether adding a skill changes agent behavior | baseline absent/effectively empty skill -> choose test posture -> custom behavior graders -> `stet eval rules` |
| Rules skill loop | Replay-backed shared skill improvement on the canonical rules surface | `stet eval rules skill --plan` -> `stet eval rules skill` -> optional `stet eval rules checkpoint` -> finalist `stet eval rules holdout` -> `stet eval report`. Both plan and launch require `--skill`, `--repo`, `--model`, `--goal`, and `--out`; normal cycles remain iteration-only. |
| Repo onboarding | New repo, no dataset yet | author harness Dockerfile -> `stet init` -> `stet suite discover` -> `stet suite build` |
| Dataset eval | Reusable benchmark | `stet suite build` -> `stet eval run` -> `stet eval report` |
| Workbench probe | Iterative artifact improvement | `stet eval workbench probe` -> `stet eval report` -> `stet eval workbench gate` |
| Release lifecycle | Promote, monitor, rollback | gate -> `stet promote` / `stet monitor run` / `stet rollback` |

## Routing Rules

- Before fresh Stet work on a repo, orient with:

  ```bash
  stet context --repo <repo> --json
  ```

- Treat context as the current map of config, dataset/eval history, reusable
  artifacts, baselines, task selection, Harness Surface, and recommended next
  actions. Skip it only for an already-known active run, a specific completed
  root/report, or setup evidence that must be inspected directly.
- Start with the cheapest surface that preserves the operator's decision
  semantics. Use `stet probe` for quick safety reads. Use manifest-backed
  rules flows for shared behavior changes that may become rollout state.
  Treatments split by mechanism: file overlays (`agents_md`, `claude_md`,
  `skill_diff`, `harness_bundle`), prompt-template context (`docs_glob`),
  and runtime selector (`model_update`). See
  [rules-flow](references/rules-flow.md) ("How file overlays work") for why.
- Cheap `stet probe --file` or `stet eval config-diff` runs may discard bad
  AGENTS.md, CLAUDE.md, skill, or policy drafts, but any candidate you keep,
  recommend, baseline, promote, or call an improvement needs rules evidence.
- For raw file A/B without manifests, use `--baseline-file`,
  `--candidate-file`, and `--logical-path`. For non-code outputs such as
  research or plans, choose or write custom rubric YAML before comparing.
- For repo-managed skills under `.agents/skills` or `.claude/skills`, treat the
  changed skill as the target and the full managed skills tree as the frozen
  runtime envelope. Precedence is `.agents/skills` over `.claude/skills`.
- Split skill comparisons by baseline semantics. For a new skill, answer
  "with skill vs without skill": the baseline should have no usable skill
  guidance, and `skill_workbench` is secondary because it grades the skill text,
  not the agent's task output. For a skill revision, answer "candidate skill vs
  committed prior skill" and prefer `stet eval rules skill`.
- Decide test posture before launching a skill A/B. If repo tests are not part
  of the question, do not use `tests_gated` rubrics as the primary signal; use
  `quality_only` behavior rubrics or an existing-details quality-only path, and
  say explicitly whether Harbor repo tests will run.
- For model, reasoning-level, or harness-setting selection, prefer exact
  comparable roots from `stet context --repo <repo> --json`, then pinned reuse
  of prior task selection, then a fresh dataset-backed run. Treat `stet eval
  smoke` as first-run bootstrap, not the default for repos with history.
- Treat reasoning level, sandbox, tool access, prompt profile, and agent kwargs
  as Harness Surface levers. Keep the task slice fixed when comparing those
  levers, especially when both arms use the same model id.
- For reusable evidence, freeze completed comparable roots with
  `stet baseline freeze --from <root> --name <capability> --json`. Reuse
  `task_selection.dataset_key` as `--pinned-dataset-key` when available. In
  baseline-first compare, `--task-id` narrowing works for benchmark baselines
  but not replayable baseline snapshots.
- For completed reads, prefer persisted `eval_report.v1.json`; read
  `decision_receipt`, then `trial_context`, then lower-level artifacts only for
  diagnosis. For active reads, prefer `stet eval status --json`.
- For disk pressure, read `stet artifacts status --root <root>` before
  deleting anything manually. Compacted roots keep `patch_retention.v1.json`
  contracts and report `regrade_capability`; `bounded_only` means decision
  metadata remains but full raw-patch regrade requires a rerun or archive.
- If requested grader coverage is part of the decision, verify the expected
  grader IDs in `decision_receipt.compare.grader_coverage`,
  `experiment.json.graders`, or arm `decision_metrics.graders`. Missing or
  asymmetric explicit coverage should fail closed to `inspect`; one-sided
  graders are excluded from rollout recommendations.
- If LLM grader provenance is part of the decision, read
  `decision_receipt.graders.profile_status` and `grader_profile`. `mixed` or
  `missing_legacy` means the report is inspect-only until rerun or repaired
  with resolved profile evidence.
- Recover incomplete or under-graded roots with the ordered commands emitted by
  `stet eval status` or `stet eval report`: usually
  `stet runs repair-ai-coverage ...`, then `stet runs regrade-graders ...`.
  Add `--parse-retries N` for saved grader prompts that failed parsing.
- For incomplete rules-backed compares, prefer
  `stet eval rules repair --change-manifest <stet.change.yaml>` or
  `--rules-root <dir>`. Do not rerun `stet eval rules` to recover partial
  evidence; use `--restart` only when intentionally discarding it.
- Treat `waiting_on_quota` as an intentional automatic pause. Do not delete
  artifacts or relaunch successful task evidence; wait for `retry_after`, or
  use the flow's resume command only if the active process has exited.
- Treat auth, license, Claude `/login`, and Harbor setup-skew failures such as
  missing `stet_harbor_agents.*` modules as infrastructure risk before
  interpreting candidate quality. For Claude Code auth, prefer the Stet-private
  `~/.config/stet/claude-oauth-token` file with `0600` permissions; avoid
  global shell exports and repo-local env files. Run `stet update` from
  prerelease builds, or use `stet update --prerelease` /
  `stet update --version <tag>` to refresh the Harbor support files explicitly.
  See [onboarding](references/onboarding.md) and
  [operator-contract](references/operator-contract.md) for exact recovery.
- Preserve the release/baseline distinction. Release promotion changes rollout
  state; baseline refresh changes the frozen reference for future compares.
- Prefer `--json` when output feeds another agent step. When a command finishes
  in a non-terminal state, offer keyed next actions.

## Lifecycle and Decisions

Lifecycle: onboard -> probe/compare -> gate -> promote -> monitor or rollback.
Each step produces evidence the next step requires.

| Step | Decision grade | Produces |
|---|---|---|
| Onboard | `exploratory` | dataset + onboarding receipt |
| Probe | `exploratory` to `gateable` | bounded compare verdict |
| Compare | `exploratory` | pairwise experiment |
| Gate | `gated` | release record with trust/rollout |
| Promote | `promoted` to `monitorable` | promoted release |

Decision shortcuts:

- Fast answer wanted: `stet probe` or first-run `stet eval smoke`.
- Baseline vs candidate: `stet eval compare`.
- New repo: `stet suite discover`, `stet suite build`, then propose a starter slice.
- Shared skill improvement: `stet eval rules skill --plan`, then `stet eval rules skill`.
- Custom artifact, research, or plan quality: use workbench or custom rubrics.
- Noisy rubric: read [rubric-authoring](references/rubric-authoring.md).
- Incomplete compare: read status/report `next_action`, not summary prose.
- Clear baseline-first winner: recommend baseline promotion before another iteration.

## Gotchas

- `probe` answers the question directly. Gate is optional, not the default.
- `INSPECT` and `HOLD` are completed decision states, not broken runs.
- Quiet logs are normal, and Stet runs can take a while. Use
  `stet eval status` before assuming a stall.
- If `stet eval status --json` and `stet eval report --json` disagree on a
  compare root, fail closed to inspect instead of inventing a clean verdict.
- Tests are the gate, not the source of truth. Binary pass rate cannot
  differentiate strong models. Quality dimensions above the gate are where
  differentiation lives.
- AGENTS.md/CLAUDE.md treatments are disk overlays, not prompt injection. Harbor
  stages them outside `/app`, installs through existing symlink targets, and
  commits the overlay baseline so captured patches exclude treatment churn.
- Historical tasks default to the repo's current root `AGENTS.md` and
  `CLAUDE.md` at materialize time. These convention files replace any
  historical copies after `repo.tar.gz`, are committed into the task baseline
  when git history is available, and are excluded from captured agent patches;
  explicit rules/config-diff overlays still apply later and take precedence for
  the selected arm.
- Dataset images ship with `install_config.pre_install` and `install` baked in
  at build time, so the agent's first turn can run the project test command
  directly (`pnpm vitest`, `cargo test`, `go test ./...`, `pytest`, etc.)
  without `pnpm install` / `cargo fetch` / `go mod download` / `bundle install`
  / `uv sync` first. Missing or wrong install steps surface deterministically
  at `docker build` rather than as silent first-turn flakes.
- Docker capacity is shared across Harbor task concurrency, model workers,
  validation workers, and command workers. When Docker Desktop cannot allocate
  more memory, keep effective concurrency explicit: harness pressure is roughly
  `model-workers * harbor-concurrency`; validation pressure is roughly
  `workers * command-workers`. Use `stet harbor cleanup` before broad Docker
  spelunking; apply with `--apply` only when no active run is using the listed
  stale Harbor resources.

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
