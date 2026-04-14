# Onboarding

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

Use this when the user wants to set up a new repo for Stet evals, build a
dataset, or get a starter task slice. For heavy dataset builds (50+ tasks,
Docker debug loops), see [dataset-build](dataset-build.md).

```
read CI ──► init ──► discover ──► build ──► receipt
                                              │
                                ┌─────────────┼─────────────┐
                                ▼             ▼             ▼
                          [m] smoke    [a] approve    [p] probe
```

## When To Use

- "Onboard this repo for evals"
- "Set up Stet on this repo"
- "Build a dataset from this repo"
- First time on a repo with no `.stet/stet.yaml`
- User wants a reusable task slice before running probes or comparisons

## Quick Path

For most repos, the quick path is enough:

```bash
# 1. Resolve test setup from CI evidence
#    Read .github/workflows/*.yml, Makefile, package.json scripts, README.
#    Pick the real repo-level test command. CI is ground truth, not README.

# 2. Author the Harbor environment
#    Write .stet/harbor.Dockerfile for this repo and reference it from
#    .stet/stet.harness.yaml under environment.dockerfile.

# 3. If Claude is the selected provider, set up host auth first
#    Run `claude setup-token`, then export CLAUDE_CODE_OAUTH_TOKEN with the
#    printed token. Stet fails before launching Claude runs if auth is missing.

# 4. Ask the operator which first-run quality posture to use
#    [r] recommended: discipline bundle + intentionality
#    [s] standard: repo tests plus default coding graders only
#    [c] custom: inspect `stet graders --repo . --json`, then choose

# 5. Persist config
stet init --repo . --yes --test "<repo test cmd>"

# If the operator chose [r] while using --yes automation, ensure .stet/stet.yaml
# contains:
# quality:
#   bundles:
#     - discipline
#   include_graders:
#     - intentionality

# 6. Mine candidate pool
stet suite discover --repo . --rev-range main~50..main

# 7. Build dataset
stet suite build --repo . --manifest .stet/discover-manifest.yaml

# 8. Read receipt and propose starter slice
# Build writes onboarding_receipt.v1.json to the dataset root.
```

Test-setup rules:
- The agent owns test-command selection. `stet init` writes config; it does not
  replace repo reading and judgment.
- Priority order: CI workflow steps (highest trust) > Makefile/justfile targets
  > package.json scripts > README (lowest trust).
- Avoid placeholder commands (`echo`, `true`, lint-only, build-only).
- `stet suite build` now requires a repo harness manifest with
  `environment.dockerfile`; the agent should author that Dockerfile explicitly
  from repo setup knowledge instead of relying on generated install recipes.
- If the repo rarely co-locates test edits with code changes, use
  `stet suite discover --allow-no-test-changes ...` to admit repo-tests-only
  tasks.

Quality onboarding rules:
- Interactive `stet init` now recommends enabling the `discipline` bundle plus
  `intentionality` as an extra grader. Accepting that prompt writes the repo
  `quality` selection into `.stet/stet.yaml`.
- Before any automated setup that would use `stet init --yes`, ask the
  operator for the first-run quality-grader posture: `[r] recommended`
  `discipline` + `intentionality`, `[s] standard` with no repo quality bundle,
  or `[c] custom` after inspecting `stet graders --repo <path> --json`.
- `stet init --ai-provider claude` requires usable Claude auth. Prefer
  `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token`; Stet also accepts
  Claude credential JSON, Anthropic API/auth token env vars, or the macOS
  `Claude Code-credentials` Keychain item.
- `stet init --yes` stays low-friction and does not enable quality bundles by
  default. Silent auto-init paths should keep bundle selection empty until an
  operator opts in.
- Do not launch the first smoke, probe, or eval run while the repo has no
  `quality:` block, `--grader`, or explicit operator decline. If the operator
  chooses the recommended posture, write the `quality:` selection before the
  run or pass equivalent explicit graders where the command supports them.

## Onboarding Receipt

Build writes `onboarding_receipt.v1.json` to the dataset root with:

- `candidate_pool`: total, passed, build_ready, build_skipped, skip_reasons
- `task_selection`: frozen `TaskSelectionRecord` with requested/realized IDs
- `task_rationale`: per-task selected/rejected with reasons
- `test_setup`: commands and source
- `confidence`: `high`/`medium`/`low` with reasons
- `lifecycle`: `journey_kind: "onboard"`, `decision_grade: "exploratory"`

## Reporting

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
coverage    workflow, validation, leaderboard, model routing, market context
why         Breadth is good enough for a starter slice, but the slice is still
            exploratory, so smoke buys a quick calibration read before probe.

next        > [m] smoke   quick calibration on this slice before locking it
then        [a] approve   freeze these tasks for probe without running now
then        [p] probe     approve and launch the first bounded run
then        [s] stop      keep the recommendation only
```

## Proposal Rules

- Recommend a variable-size starter slice, not a fixed `N`.
- Prefer tasks with strong test signal and plausible medium difficulty.
- Avoid trivially small, obviously huge, duplicate-looking, or weak-signal
  tasks.
- Keep light subsystem coverage.
- Include `confidence`, the funnel, what was excluded, and coverage gaps.
- Show at most 5 representative tasks, then `+N more`.

## Flow-Specific Actions

- `[a] approve`: accept the proposed starter slice; slice is locked for probe.
- `[m] smoke`: after quality posture is resolved, run
  `stet eval smoke --dataset .stet/dataset --models "..." --json`
- `[p] probe`: approve and immediately launch
  `stet probe --dataset .stet/dataset --model "..." --json`

## Escalation Handoff

After onboarding, the next lifecycle step is **probe**, not gate or eval run.
Probe inherits the onboarding receipt's `task_selection` contract.

For benchmark-first workflows, freeze the finished probe as a baseline:

```
onboard -> probe -> baseline freeze -> compare -> gate -> promote
```

Onboarding produces `exploratory`-grade evidence; gate requires `gateable`-grade
evidence from probe.
