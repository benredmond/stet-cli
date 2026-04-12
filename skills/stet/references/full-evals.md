# Full Evals

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
discover ──► build ──► eval run ──► status ──► report
                                      │          │
                                  [w] wait   verdict
                                              ├─ winner ──► [g] gate
                                              ├─ mixed ──► [i] inspect
                                              └─ rerun ──► [r] rerun
```

Use this when the user needs a reusable benchmark, explicit task selection, or
multi-model comparison with more than smoke-level coverage.

## Repo Onboarding

For the complete onboarding flow, see
[onboarding](onboarding.md).

This reference covers the terminal receipt patterns and commands used in onboarding that
also appear in dataset and full eval flows.

When onboarding produces a real artifact, report it with a compact
instrument-style summary and keyed next actions, for example:

```text
STET :: DATASET

answer      starter slice ready
confidence  medium
step        onboard -> probe
funnel      150 scanned -> 18 passed discover -> 9 build-ready
dropoff     131 rejected before build
            top: no_test_changes 72, llm_gate_fail 41, oversize 18
build       9 materialized, 3 skipped
            top: unsafe_external_symlink 3
coverage    auth, cli, config
gap         db
why         Smoke is next because the slice is broad enough to calibrate, but
            still exploratory evidence rather than a locked benchmark.

next        > [m] smoke   quick calibration on this slice before locking it
then        [a] approve   freeze these tasks for probe without running now
then        [p] probe     approve and launch the first bounded run
then        [s] stop      keep the recommendation only
```

Flow-specific actions:
- `[a] approve`: accept the proposed starter slice; locked for next run
- `[m] smoke`: `stet eval smoke --dataset ... --models "..." --json`
- `[p] probe`: approve and launch `stet probe --dataset ... --model "..." --json`

When the flow is active but not finished, use a running terminal receipt:

```text
STET :: BUILD STATUS

step        suite build
state       running
health      active
root        .tmp/stet-dataset
progress    12/34 tasks materialized
eta         unknown
confidence  medium
why         Wait is next because build is still materializing valid tasks and
            has not crossed into a no-progress state.

next        > [w] wait      keep the build running and check again later
then        [i] inspect     open build artifacts if progress flattens
then        [s] stop        keep this as a status read only
```

## Quickest Larger-Scale Entry

```bash
stet eval smoke --repo . --models "opus 4.6,sonnet 4.6" --tasks 30 --keep --json
```

Use this before a full build if the user mainly wants a first directional read.

Smoke and run summaries should always state:
- verdict
- confidence
- main differentiator
- main risk
- why this next action is next

## Reusable Dataset Flow

```bash
stet init --repo . --test "<repo test cmd>"
stet suite discover --repo . --rev-range main~50..main --output discover-manifest.yaml
stet suite build --repo . --manifest discover-manifest.yaml --out ./stet-dataset --workers 4
stet eval run --dataset ./stet-dataset --models "opus 4.6,sonnet 4.6" --out ./eval-output
stet eval status --out ./eval-output --json
stet eval report --out ./eval-output --json
```

Machine-readable default:
- Use `stet eval status --json` for health, liveness, and smoke/full lineage.
- Use persisted `eval_report.v1.json` when present, or
  `stet eval report --json` when it must be generated, for the interpreted
  Trial Result.
- Read `decision_receipt` for the decision and next action, then
  `trial_context` for task corpus, task selection, Harness Surface, Search
  Space, baseline/candidate, supporting evidence, freshness, and machine
  recommendation.
- For per-model comparison truth, prefer `runs.<model>.decision_metrics` from
  summary/report surfaces. Treat `validation_metrics` as legacy aliases and
  detailed counters.
- For per-task authority, prefer `task_decision.json`, then `task_detail.json`
  and `trajectory.json` for inspectability.

For partial reruns on an existing root, keep `--out` pointed at the canonical
root and add `--task-id ... --stitch-rerun`. This preserves the original slice,
refreshes only the selected task artifacts, and regenerates one merged summary.

Before `stet init`, the agent should inspect repo evidence and decide the test
commands itself. Treat `stet init` as config persistence, not as the authority
that decides the repo's test setup.

`stet suite build` strips tracked symlinks that escape the repo root. Unrelated
external links no longer poison the dataset, but diffs that edit those paths
still stop at patch preflight.

If the repo has low test co-change but trustworthy repo-wide test commands, use
`stet suite discover --allow-no-test-changes ...` to admit repo-tests-only
tasks. Those tasks keep `test.patch` as an artifact, record
`has_test_patch: false`, require gold to pass the repo tests, and skip F2P with
`validation.f2p_status: repo_tests_only`.

## Rules-Backed Rollout

Use this when the repo already has change and suite manifests and the operator
wants a formal change-control path.

```bash
stet manifest resolve --change-manifest stet.change.yaml
stet eval rules --change-manifest stet.change.yaml --suite-manifest stet.suite.yaml
stet eval status --change-manifest stet.change.yaml --json
stet eval report --change-manifest stet.change.yaml --json
```

## Rules

- Repo onboarding starts with agent-selected repo tests plus an authored
  `.stet/harbor.Dockerfile` referenced by `.stet/stet.harness.yaml`, then
  `stet init` when repo config is missing, then `stet suite discover` +
  `stet suite build`, not a full `stet eval run`.
- `stet eval smoke` is the canonical quick first-run wrapper.
- `stet eval run` is the canonical public home for multi-model H2H execution.
- `stet eval run --stitch-rerun` is the supported subset-rerun path for an
  existing canonical run root. Do not tell the user to hand-copy retry
  artifacts unless they explicitly need the legacy manual path.
- `stet eval report` is the canonical decision surface over finished artifacts.
- `stet eval status` is the canonical health/check-in surface for active roots.
- Prefer `runs.<model>.decision_metrics.tests.leaderboard_pass_rate` for
  standard model comparison truth.
- `strict_publishable_pass_rate` remains explicit legacy publish gating; do not
  substitute it for leaderboard/model-comparison truth.
- `publish.exclusions_by_reason` and compare-level `blocked_runs` explain why a
  result is not cleanly publishable even when task execution mostly finished.
- `decision_metrics.graders.<grader_id>` is the canonical run-level grader
  summary for both built-in and custom graders. Do not scrape per-task
  `validation.json` if the run-level metric is already available.
- Built-in code review now exposes normalized
  `graders.code_review.rubric_scores` in `task_decision.json`, so review
  dimension names should come from the canonical artifact rather than inferred
  legacy payloads.
- After discover, build, smoke, or report, tell the user the one next step that
  moves the pipeline forward with keyed options.
- Starter-slice proposals should include `confidence`, coverage gaps, and what
  was excluded.
- When repo-tests-only tasks are in scope, say so explicitly and remind the
  operator that graders are independent evidence with their own eligibility
  replacement for repo test commands.
