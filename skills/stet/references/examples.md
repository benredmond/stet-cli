# Interaction Examples

Three complete multi-turn traces showing the agent protocol in action. Use
these to pattern-match on routing decisions, receipt composition, and keyed
action handling.

## Trace 1: Rules Flow - Happy Path

**User:** "Is our new CLAUDE.md helping on this repo?"

Agent routes to: rules flow (`claude_md` treatment).
Agent reads: `references/rules-flow.md`

```bash
stet manifest resolve --change-manifest stet.change.yaml
stet manifest resolve --suite-manifest stet.suite.yaml
stet eval rules --change-manifest stet.change.yaml --suite-manifest stet.suite.yaml
stet eval report --change-manifest stet.change.yaml --json
```

Agent reads the Trial Result first: `decision_receipt` for the verdict and next
action, `trial_context` for task selection and baseline/candidate context, then
outer `lifecycle` and `evidence_quality` for readiness and trust posture. It
then projects the compact terminal receipt:

Agent reports:

```text
STET :: RULES REPORT

answer      safe
confidence  medium
phase       report
compare     candidate (with CLAUDE.md) vs baseline (without)
sample      8 tasks
delta       pass +0pp  equiv +12pp  review +4pp
driver      equivalence improved on 5/8 tasks without review regression
evidence    stet.change.yaml
why         Promote is available because this is the formal rollout decision
            surface and the required graders are present.

next        > [p] promote   persist this as the current release state
then        [i] inspect     review task-level evidence
then        [s] stop        keep the verdict without rollout mutation
```

**User:** `s`

Agent acknowledges stop, names the change manifest and rules report path. Done
in 2 turns.

---

## Trace 2: Config Diff Prefilter - Rules Handoff

**User:** "I have several AGENTS.md wording drafts. Give me a cheap first pass
before we spend on the release eval."

Agent routes to: quick-probe prefilter.
Agent reads: `references/quick-probe.md`

```bash
stet eval config-diff --repo . --file AGENTS.md --model "sonnet 4.6" --json
```

Agent treats the result as directional only and says so explicitly.

Agent reports:

```text
STET :: CONFIG DIFF PREFILTER

answer      inconclusive
confidence  medium
step        probe -> inspect
compare     candidate (new AGENTS.md) vs baseline (git HEAD~1)
sample      8 tasks
delta       pass +0pp  equiv -4pp  review +1pp
driver      equivalence dropped on 3/8 tasks; review gain is noise
evidence    .tmp/stet-config-diff
why         This can prune a weak draft, but it is not release evidence for
            AGENTS.md and does not prove custom agents_* grader coverage.

next        > [i] inspect   read task-level evidence
then        [r] rerun       gather fresh evidence after a change
then        [s] stop        keep the bounded verdict
```

**User:** `i`

Agent forms a hypothesis before inspecting:

> **Hypothesis:** I believe the equiv drop is caused by scope creep in the
> candidate's edits — the original AGENTS.md had a "prefer minimal diffs"
> constraint that the new version removed. If that constraint was the
> guardrail, I expect tasks with multi-file changes to show the largest
> regressions.

Agent inspects `.tmp/stet-config-diff` task evidence and reports:

> **Result:** Confirmed. Tasks 18 and 25 both show the agent touching 3-4
> files when the baseline touched 1. Task 12 is a direct regression — the
> agent rewrote a helper it didn't need to.
>
> **Implication:** The "prefer minimal diffs" constraint was load-bearing.
> Restoring it with tighter wording should recover equiv without regressing
> review. The next hypothesis should check whether tighter wording
> introduces rigidity on tasks that legitimately need multi-file changes.

```text
next        > [v] revise    restore the constraint with tighter wording and rerun
then        [r] rerun       rerun as-is to confirm the signal
then        [s] stop        keep the current diagnosis
```

**User:** restores the constraint with clearer wording, says "try again"

Agent recognizes this as another cheap prefilter pass. The prior implication
said to watch for rigidity on legitimate multi-file tasks, so the agent
carries that forward:

> **Hypothesis:** The tighter wording ("never touch files outside the issue
> scope") will recover equiv on tasks 18/25/12, but may cause the agent to
> under-edit on tasks that legitimately span multiple files.

```bash
stet eval config-diff --repo . --file AGENTS.md --model "sonnet 4.6" --json
```

> **Result:** Equiv recovered +2pp overall. Tasks 18 and 25 improved. No
> rigidity regression visible in this sample — but sample is only 8 tasks,
> so confidence is medium.

```text
STET :: CONFIG DIFF

answer      safe
confidence  medium
step        directional prefilter
compare     candidate (revised AGENTS.md) vs baseline (git HEAD~1)
sample      8 tasks
delta       pass +0pp  equiv +2pp  review +1pp
driver      equivalence recovered; revised constraint is working
evidence    .tmp/stet-config-diff

next        > [R] rules     run manifest-backed eval before claiming improvement
then        [i] inspect     spot-check the recovered tasks
then        [s] stop        keep only the directional read
```

**User:** `R`

Agent runs the retained candidate through the rules flow:

```bash
stet eval rules --change-manifest stet.change.yaml --suite-manifest stet.suite.yaml
stet eval report --change-manifest stet.change.yaml --json
```

Done in 5 turns. The inspect -> revise -> rerun cycle recovered a regression,
and the retained AGENTS.md candidate still had to pass the rules flow before
the agent could recommend it.

---

## Trace 3: Onboard → Smoke → Probe

**User:** "Set up evals for this repo"

Agent routes to: onboarding.
Agent reads: `references/onboarding.md`

Agent inspects CI (`.github/workflows/test.yml`), finds `npm test`.

```bash
stet init --repo . --yes --test "npm test"
stet suite discover --repo . --rev-range main~50..main --output discover-manifest.yaml
stet suite build --repo . --manifest discover-manifest.yaml --out ./stet-dataset
```

Agent reports:

```text
STET :: DATASET

answer      starter slice ready
confidence  medium
step        onboard -> probe
funnel      87 scanned -> 14 passed discover -> 9 build-ready
dropoff     73 rejected: no_test_changes 48, oversize 15, llm_gate_fail 10
build       9 materialized, 2 skipped (unsafe_external_symlink)
coverage    api, auth, validation, cli
gap         db migrations (no test co-changes found)
why         Smoke is next because the slice is untested — a quick
            multi-model read will calibrate before you commit to a probe.

next        > [m] smoke     calibrate on this slice
then        [a] approve     freeze for probe without calibrating
then        [p] probe       approve and launch first probe
then        [s] stop        keep the recommendation only
```

**User:** `m`

```bash
stet eval smoke --dataset ./stet-dataset --models "opus 4.6,sonnet 4.6" --tasks 5 --json
```

```text
STET :: SMOKE

answer      directional: opus leads
confidence  low
step        smoke -> probe
models      opus 4.6: pass 80%  sonnet 4.6: pass 60%
sample      5 tasks (too small for high confidence)
driver      opus solved 1 additional task; both failed the same hard task
evidence    .tmp/stet-smoke
why         Probe is next because smoke gave a directional signal but the
            sample is too small for a release decision.

next        > [p] probe     launch full probe with this dataset
then        [r] rerun       rerun smoke with more tasks
then        [s] stop        keep the directional read
```

**User:** `p`

```bash
stet probe --dataset ./stet-dataset --model "opus 4.6" --json
stet eval report --out .tmp/stet-probe --json
```

```text
STET :: PROBE

answer      safe
confidence  medium
step        probe -> baseline
compare     opus 4.6 on 9 tasks
sample      9 tasks
delta       pass 78%  equiv 3.2/4  review 3.0/4
driver      strong baseline established across api/auth/validation/cli
evidence    .tmp/stet-probe
why         This is your first real evidence. Baseline freeze is the natural
            next step so you have a stable reference for future comparisons.

next        > [b] baseline   freeze as the repo's first baseline
then        [g] gate         skip to release state if shipping now
then        [s] stop         keep as directional evidence
```

Done in 4 turns. The onboard → smoke → probe pipeline produced the repo's
first real eval evidence.

---

## Trace 4: Active Status With Heartbeat And Lineage

**User:** "What is this eval doing right now?"

Agent routes to: compare-and-checkin (status).
Agent reads: `references/compare-and-checkin.md`

```bash
stet eval status --out .tmp/stet-run --json
```

Agent reads `activity_state`, `active_work`, `blocking_tasks`, `last_artifact`,
and `lifecycle` from status JSON. The terminal `STET_STATUS_SUMMARY ...` lines
are treated as operator-facing mirrors, not the primary contract.

Agent reports:

```text
STET :: STATUS

step        eval run
state       waiting_on_evaluator
health      active
progress    18/40 tasks
idle        4m
last_seen   validation/candidate/task-18
blocker     candidate/task-19 waiting on evaluator
lineage     smoke complete -> full active
evidence    .tmp/stet-run
why         Wait is next because the run still has fresh task heartbeat and a
            specific blocker, not a no-progress stall.

next        > [w] wait      keep the run going and check back later
then        [i] inspect     open the blocking task evidence if progress stops
then        [s] stop        keep this as an informational health read
```

Done in 1 turn. The agent reports liveness and lineage from status JSON rather
than inferring from directory shape or partial logs.

---

## Trace 5: Shared Skill Loop

**User:** "Is my updated planning skill better?"

Agent routes to: rules skill loop.
Agent reads: `references/rules-flow.md` and
`references/iterative-improvement.md`.

```bash
stet eval rules skill \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --json

stet eval report \
  --change-manifest .stet/skill-loops/planner/stet.change.yaml \
  --json
```

Agent reads the Trial Result first, then opens the linked
`evidence.skill_loop_path` for the loop ledger.

Agent reports:

```text
STET :: SKILL LOOP

answer      improving
confidence  medium
cycle       2
compare     candidate skill vs baseline skill
sample      12 tasks
best        3.1 / 4
latest      3.1 / 4
weakest     skill_specificity
driver      routing improved, but planning instructions still stay generic on
            setup-heavy tasks
evidence    .stet/skill-loops/planner/stet.change.yaml
loop        skill_loop.v1.json
why         Iterate is next because the weakest dimension points to one
            specific edit: make setup-heavy planning guidance concrete.

next        > [v] revise    tighten the weakest skill dimension and rerun
then        [i] inspect     read task-level risks before editing
then        [p] promote     only after rules evidence is trusted
then        [s] stop        keep the current best without rollout mutation
```

Done in 2 turns. The wrapper generated the change/search-space/suite bundle,
built the replay dataset, delegated into rules, and persisted `skill_loop.v1.json`
so the next iteration starts from the weakest dimension instead of thread memory.
