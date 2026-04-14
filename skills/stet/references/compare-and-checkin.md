# Compare And Check-In

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
compare ──► report ──► complete?
                       ├─ yes, winner (release context) ──► [g] gate  [i] inspect  [s] stop
                       ├─ yes, winner (baseline-first context) ──► [b] promote-baseline  [i] inspect  [s] stop
                       ├─ yes, mixed ──► [i] inspect  [r] rerun  [s] stop
                       └─ incomplete ──► [p] repair  [r] rerun  [s] stop
```

Use this for pairwise compare, active run status, inspect handoff, and recovery
after partial results.

## Pairwise Compare

Use `compare` when the question is "baseline or candidate?" and the dataset or
compare-compatible roots already exist.

Before proposing a fresh compare in a cost-sensitive workflow, run:

```bash
stet context --repo /path/to/repo --json
```

If `artifact_reuse` is present, prefer the listed exact comparable roots before
launching a new eval. If only near matches are available, explain the task-slice
or dataset drift explicitly so the operator can decide whether the extra spend is
worth it.

```bash
stet eval compare \
  --baseline /path/to/baseline-reference.json \
  --candidate-root /path/to/after \
  --out ./stet-compare \
  --json
```

Or with two explicit compare-compatible roots:

```bash
stet eval compare \
  --baseline-root /path/to/before \
  --candidate-root /path/to/after \
  --json
```

Or with two plain files that should be evaluated as one logical repo path:

```bash
stet eval compare \
  --dataset /path/to/dataset \
  --out ./stet-compare \
  --baseline-model "sonnet 4.6" \
  --candidate-model "sonnet 4.6" \
  --baseline-file /path/to/agents.before.md \
  --candidate-file /path/to/empty.md \
  --logical-path AGENTS.md \
  --grader equivalence \
  --grader code_review \
  --grader footprint_risk \
  --json
```

Report compare results with baseline/candidate/delta explicitly. The report now
includes metric narrative lines and a failure taxonomy for all recommendation
types (promote, hold, inspect), not just inspect.

```text
STET :: COMPARE

answer      safe
confidence  medium
step        compare -> gate
baseline    sonnet 4.6
candidate   codex 5.3
sample      24 tasks
delta       pass +0pp  equiv +7pp  review -2pp  footprint +0.15
failures    no_patch 0→3  infra 0→0  test_failure 2→1
driver      candidate wins on equivalence without introducing review regressions;
            3 candidate tasks produced no patch (bootstrap/setup, not model quality)
evidence    .tmp/stet-compare
why         Gate is next because the candidate has a bounded win and this is
            where compare evidence becomes a release decision surface.

next        > [g] gate      materialize trust and rollout state
then        [i] inspect     review mixed or surprising task evidence first
then        [s] stop        keep the pairwise verdict without lifecycle change
```

When the compare is against a frozen baseline and the operator is running a
baseline-first improvement loop rather than a release rollout, change the
default next action:

```text
STET :: COMPARE

answer      winner
confidence  medium
step        compare -> baseline promotion
baseline    current frozen baseline
candidate   latest candidate
sample      9 tasks
delta       tests +50pp  equiv +50pp  review +0pp  footprint -0.01
driver      candidate beats the frozen baseline on the resolved comparison
            metrics and this workflow is baseline-first, not release-gated.

next        > [b] promote-baseline   freeze this candidate as the new current baseline
then        [i] inspect              review remaining quality misses before another loop
then        [s] stop                 keep the compare verdict without updating the baseline
```

When the failure taxonomy shows `no_patch` or `infra` counts, surface them in the
`failures` and `driver` rows. These indicate infrastructure or setup failures, not
genuine model quality differences — the operator needs to know whether the delta is
real signal or artifact of broken tasks.

The report text now includes for all recommendation types:
- A comparison table with baseline/candidate/delta columns
- A failure breakdown section (omitted when both arms are clean)
- Metric narrative lines showing `Label: X% -> Y% (state)` per signal
- Review mean lines now label the contributing population explicitly (`publishable` or `all validated`) and include per-arm `n=` counts when available.

Machine-readable default:
- Read persisted `<compare-root>/.stet/eval-report/eval_report.v1.json` first
  when it exists. Otherwise run `stet eval report --out <compare-root> --json`.
- Read `decision_receipt` as the canonical decision object.
- Do not read top-level `decision` or top-level `metrics`; those legacy fields
  are no longer present in the JSON report.
- For completed compares, the same object is also persisted at
  `<compare-root>/.stet/eval-report/eval_report.v1.json`.
- Read `trial_context` for task corpus, task selection, Harness Surface, Search
  Space, baseline/candidate refs, supporting evidence, freshness, and raw
  machine recommendation before opening sibling artifacts.
- Read the outer `lifecycle`, `validity`, `evidence_quality`, `arms`, and
  `quality` fields too. `decision_receipt` is the interpreted verdict; the
  outer fields tell you whether the evidence is replayable, trustworthy, and
  clearly tied to the expected baseline/candidate lineage.
- Use `decision_receipt.metrics`, `decision_receipt.tasks`, and
  `decision_receipt.compare` instead of reconstructing the answer from
  `experiment.json`, arm summaries, and per-task validation files.
- For LLM-as-a-judge provenance, read `evaluator_model` plus
  `evaluator_model_status` from
  `decision_receipt.tasks[*].{baseline,candidate}_graders.<grader_id>` for the
  exact per-task judge, and read aggregate model sets plus status from
  `decision_receipt.graders.run.<grader_id>.evaluator_models` or
  `decision_receipt.graders.compare.<grader_id>.{baseline,candidate}_evaluator_models`.
- When `quality` is present, use it to identify the enabled grader bundles,
  effective grader IDs, and recurring strengths/risks per dimension. Treat
  those recurring reasons as evidence for follow-up guidance rather than as
  auto-generated AGENTS.md edits.
- For compare review means, prefer the explicit metric rows ending in
  `_publishable` or `_all_validated`; read their `population`,
  `population_label`, `baseline_task_count`, and `candidate_task_count`
  fields before summarizing a winner.
- Within `decision_receipt.compare`, prefer `failure_taxonomy`,
  `grader_coverage`, and `task_flips` before scraping per-task artifacts.
- For AGENTS.md, CLAUDE.md, skill, or policy compares where custom, bundled, or
  repo-configured quality graders are expected, verify those grader IDs survived
  into `grader_coverage`,
  `experiment.json.graders`, or arm `decision_metrics.graders` before giving a
  final verdict. If built-in compare signals exist but the expected additive
  graders are absent, treat the result as degraded evidence and fail closed to
  `inspect`.
- For custom rubric compares, keep the exact rubric file path in follow-up
  commands and receipts. If the operator asked for
  `--grader /path/to/custom.yaml`, reruns, config-diff repros, and
  `stet runs regrade-graders` should keep that same path rather than replacing
  it with the resolved grader ID.
- To add bundled or repo-configured quality graders after completion, use
  `stet runs regrade-graders --grader craft --grader discipline` or
  `stet runs regrade-graders --repo <repo> --from-repo-quality`; this preserves
  the completed harness/test evidence and regenerates run summaries from
  canonical task details.
- If `validity` is partial/invalid, `evidence_quality` is degraded/insufficient,
  or status/report surfaces contradict each other, lower confidence and fail
  closed to `inspect`.

The `failure_taxonomy` field in compare JSON also carries these counts so
programmatic consumers can distinguish `no_patch` from ordinary test failures.

If `experiment.json.compare_state.status=incomplete`, do not present the result
as a finished win/loss verdict. Read:
- `compare_state.next_action` for the safe machine-legible follow-up
- `requested_grader_coverage` for the exact missing or unavailable grader/task work
- `recommendation` as fail-closed context only, usually `inspect_mixed_results`

Commands for shared actions in this flow:
- `[g] gate`: `stet eval workbench gate --from <compare-root>`
- `[b] promote-baseline`: `stet baseline freeze --from <winning-candidate-root> --name <baseline-id> --json`
- `[i] inspect`: `task_detail.json`, `trajectory.json`, or local inspect bundle

Baseline reference rules:
- Prefer `--baseline <reference>` when the operator already froze benchmark
  evidence with `stet baseline freeze`.
- Treat the reference as the frozen slice and provenance authority. Do not
  re-explain the flow as "rediscover the baseline root."
- If the reference is a replayable baseline snapshot and the operator wants
  fresh evidence for the same frozen baseline, use
  `stet baseline rerun --baseline <snapshot>` before comparing again.
- If the candidate wins clearly against a frozen baseline and the operator is
  updating the "current" baseline for future work, recommend
  `stet baseline freeze --from <winning-candidate-root> --name <baseline-id>`
  before suggesting another improvement loop.
- For dataset-backed compare, task selectors are optional. When `--task-id` /
  `--task-pr` are omitted, compare runs all realized tasks from the dataset.
- Do not recommend `--baseline-instruction-file` /
  `--candidate-instruction-file` for raw file A/B. Those flags are only for
  operators intentionally supplying full prompt templates with
  `{{ instruction }}`.

## Active Check-In

Use `status` when the user asks "what is it doing?", "is it stuck?", or "should
we wait?".

```bash
stet eval status --out /path/to/run-root --json
stet eval status --change-manifest /path/to/stet.change.yaml --json
```

Machine-readable default:
- `stet eval status --json` is the canonical health surface.
- Prefer `activity_state`, `active_work`, `last_artifact`, `blocking_tasks`,
  and `lifecycle` from the JSON payload.
- Use `lifecycle.smoke` / `lifecycle.full` when present to explain smoke-to-full
  lineage instead of guessing from sibling directories.
- Treat `STET_STATUS_SUMMARY ...` stderr lines as operator-facing mirrors of the
  same state, not the primary automation contract.
- During an active compare, absence of `experiment.json` by itself is not a
  failure signal. Compare-only roots may write it only at completion, so use
  `stet eval status --json` rather than inferring failure from partial
  directory contents.
- For `--change-manifest` check-ins, a payload with `reasons` and no
  `run_status` or `report` is inspect-class evidence; do not treat the current
  phase alone as a clean wait signal.

Check-in terminal receipt:

```text
STET :: STATUS

step        eval run
state       waiting_on_model
health      active
progress    18/40 tasks
idle        6m
last_seen   validation/model-x/task-18
blocker     candidate/task-19 waiting on evaluator
lineage     smoke complete -> full active
evidence    .tmp/stet-run
why         Wait is next because artifacts are still arriving and the current
            idle window does not yet look like a stall.

next        > [w] wait      keep the run going and check back later
then        [i] inspect     open the latest task evidence if it stops moving
then        [s] stop        keep this as an informational health read
```

State meanings:
- `active`: new artifacts are appearing
- `waiting_on_model`: execution is blocked on model runtime
- `waiting_on_evaluator`: execution is blocked on grading
- `no_progress`: no meaningful artifact progress; inspect before rerun

Status reading rules:
- If `blocking_tasks` is non-empty, name the first blocker explicitly in the
  terminal receipt before recommending wait or inspect.
- Prefer blocker-first explanations over generic "still running" text.
- If status is healthy and heartbeat/progress is advancing, do not recommend a
  rerun just because logs are quiet.

Commands for shared actions in status checks:
- `[w] wait`: `stet eval status --out <root>` (check in again)
- `[i] inspect`: last task detail, trajectory, or runtime status artifact

## Inspect Handoff

`[i] inspect` should not be vague.

Use it this way:
- task-level anomaly: point to `task_detail.json` and `trajectory.json`
- many mixed tasks or richer walkthrough needed: build a local inspect bundle
- custom-rubric artifact check: point to weakest-risk output plus the artifact
  slice that caused it

Inspect should tell the user:
- what changed
- where the evidence lives
- what they will learn by opening it

## Recovery

Use recovery when evidence is incomplete or partially degraded.

Flow-specific recovery actions:
- `[p] repair`: repair missing quality evidence without full rerun
- `[c] resume compare`: recover an incomplete rules compare without
  recomputing completed baseline work; this can rerun a missing or partial
  candidate arm before repairing requested grader coverage
- `[g] retry grader`: finish retryable artifact-graded task; checks
  `validation/<model_key>/<task_id>/task_decision.json`
- `[t] revalidate`: rerun tests only when that is the missing signal

Recovery rules:
- If the compare is blocked by invalid or partially valid evidence, explain that
  as a validity problem first, not as a model-quality regression.
- When grader coverage is partial, prefer `[c] resume compare` or `[g] retry grader`
  over a blind full rerun.
- For rules-backed compares, `[c] resume compare` should start with
  `stet eval rules resume --change-manifest <stet.change.yaml> --json` or
  `--rules-root <dir>` so Stet reuses the persisted runtime and arm artifacts.
- If an arm is missing tasks or has retryable harness failures, resume reruns
  only those tasks, then rebuilds compare evidence. Do not delete the compare
  root just to recover an OOM/rate-limit interruption; file-backed
  AGENTS.md/CLAUDE.md treatments are replayed from the change manifest when the
  candidate digest still matches the persisted runtime.
- When the compare root projects recoverable requested grader gaps, follow the
  surfaced ordered sequence on the existing commands: `stet runs repair-ai-coverage`
  for missing built-in AI coverage, then `stet runs regrade-graders` for custom,
  bundled, or repo-configured quality gaps, then re-check with
  `stet eval status` / `stet eval report`.
  Those repair steps preserve compare-critical metadata and existing custom
  grader surfaces so the arm stays compare-compatible while recovering
  coverage. Add `--parse-retries N` when saved grader prompts failed
  JSON/schema parsing. Keep the original custom rubric file path on the regrade
  command.
- If `stet runs repair-ai-coverage --cr-only` still leaves `code_review`
  unresolved, use the summary's stable `unresolved[].reason` and optional
  `category`/`detail` fields to separate `model_output_shape`,
  `rubric_schema`, and `runtime_failure` before escalating.

Do not use rerun when status says the current run is still healthy.
