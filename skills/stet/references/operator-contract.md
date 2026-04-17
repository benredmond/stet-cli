# Operator Contract

Every Stet answer should be legible in one scan. This document defines the
shared terminal receipt format, keyed actions, and error handling that all flows
inherit. The top-level skill defines the agent-facing optimization interface;
this file defines how to project that machine contract back to a human operator.

## Machine Contract vs Human Receipt

- `Trial Result`: canonical completed-trial object, persisted at
  `eval_report.v1.json` and emitted by `stet eval report --json`
- `status`: canonical active health/check-in object from
  `stet eval status --json`
- `terminal receipt`: compact text projection for humans in chat

Use Trial Results and status JSON for machine consumption. Use terminal
receipts to summarize the result in one scan for the operator.

If the persisted `eval_report.v1.json` for the flow already exists, reuse it.
Ordinary output roots commonly persist it at
`<root>/.stet/eval-report/eval_report.v1.json`; change-manifest rules flows
persist it next to the resolved rules runtime under `.stet/eval-rules/...`.
When the locator is unclear, use the matching `stet eval report --out ... --json`
or `stet eval report --change-manifest ... --json` command to locate or
materialize it. Read `decision_receipt` for decision, confidence, readiness,
grader coverage, and next action. Read top-level `trial_context` for task
corpus, task selection, Harness Surface, Search Space, baseline/candidate,
supporting evidence, freshness, and raw machine recommendation refs.

Authority tiers:
- `eval_report.v1.json`: first read for completed optimizer Trial Results
- `stet eval status --json`: first read for active liveness and blockers
- `experiment.json`: compare evidence authority for diagnosis
- `release.v1.json`: lifecycle authority for release and monitoring diagnosis
- `task_decision.json`: task-level scoring authority
- `task_detail.json`, `trajectory.json`, logs: inspectability and debugging

Do not reconstruct a verdict from `experiment.json`, `summary.json`, pass-rate
heuristics, or task files unless you are explicitly inspecting supporting
evidence or handling an old root without a persisted Trial Result.

## Core Agent Loop

```
user question
     │
     ▼
identify Search Space + route (SKILL.md)
     │
     ▼
execute or resume Trial (`stet` command)
     │
     ▼
read status or Trial Result JSON
     │
     ▼
terminal receipt (human projection)
     │
     ▼
keyed actions (user picks one)
     │
     └──► next command ──► terminal receipt ──► ...
```

## Receipt Format

Always:
- Answer the user's actual question first: `safe`, `not safe`, or `inconclusive`
- Include `confidence: high|medium|low`
- Name the current pipeline step
- Show a tiny data view (delta, count, bar) so the user sees what changed
- Explain why the recommended next action is next
- End with keyed single-key actions so the user can reply with one keystroke

Use compact instrument-style ASCII receipts. Prefer plain aligned lines over
heavy box borders.

### Finished Receipt

```text
STET :: <FLOW NAME>

answer      <safe | not safe | inconclusive>
confidence  <high | medium | low>
step        <current> -> <next>
compare     <what vs what>
sample      <N tasks>
delta       <dimension deltas>
driver      <dominant reason>
evidence    <path to root>
why         <why the recommended action is next>

next        > [x] action    meaning
then        [y] action      meaning
then        [s] stop        end here
```

### Running Receipt

```text
STET :: STATUS

step        <current step>
state       <active | waiting_on_model | waiting_on_evaluator | no_progress>
health      <active | stalled>
progress    <N/M tasks>
idle        <time since last artifact>
evidence    <path>
why         <why wait/inspect/stop>

next        > [w] wait     keep running
then        [i] inspect    open evidence if stalled
then        [s] stop       end here
```

### Receipt Rules

- ASCII only, instrument-grade: measured, aligned, signal-first
- Minimum rows: `answer`, `confidence`, `step/state`, data/compare, `driver`,
  `evidence`, `why`, `next`
- Keyed actions imply meaning, not just a command
- The recommended action comes first, marked with `>`
- The agent accepts either the key or the word (`i` or `inspect`)
- Every keyed action maps to: meaning, exact command, expected resulting state
- If no real result exists yet, skip the terminal receipt but still offer keyed actions
- `STET_STATUS_SUMMARY ...` stderr lines are operator-facing mirrors of status,
  not the primary automation contract. For automation, read
  `stet eval status --json`.

### Per-Flow Data Minimums

- Quick probe / config diff: comparator, sample size, pass/equiv/review delta,
  dominant driver
- Smoke / full eval: verdict, confidence, leading model/arm, main
  differentiator, main risk
- Compare: baseline, candidate, delta, decisive dimension, confidence
- Artifact loop: weakest dimension, best/latest delta, target threshold,
  evidence hook
- Release / monitor: trust state, rollout state, freshness, rerun delta

## Keyed Actions

### Shared (available in all flows)

| Key | Name | Meaning | Resulting state |
|---|---|---|---|
| `[i]` | inspect | Drill into task-level evidence | Grounded explanation of regression or win |
| `[g]` | gate | Materialize release state from bounded win | Gated receipt with trust/rollout |
| `[r]` | rerun | Re-execute current flow or return to earlier stage | Fresh bounded evidence |
| `[v]` | revise | Change the candidate, then rerun | New evidence after candidate change |
| `[w]` | wait | Keep current run going, check in later | Updated running receipt |
| `[s]` | stop | End here with current evidence | No new execution |

### Flow-Specific

Defined in their reference docs. Context disambiguates overloaded keys.

| Key | Name | Flows | Meaning |
|---|---|---|---|
| `[a]` | approve | onboarding, full-evals | Accept proposed slice |
| `[b]` | baseline | quick-probe | Freeze evidence as stable baseline |
| `[c]` | calibrate | rubric-authoring, iterative-improvement | Tighten rubric against anchors |
| `[m]` | monitor | release-lifecycle | Replay release contract for fresh signal |
| `[m]` | smoke | full-evals, onboarding | Quick calibration pass |
| `[p]` | promote | release-lifecycle, rules-flow | Persist gated win as release state |
| `[p]` | probe | onboarding | Approve slice and launch first run |
| `[p]` | repair | compare-and-checkin | Repair missing quality evidence |
| `[c]` | resume compare | compare-and-checkin, rules-flow | Finish grader coverage for incomplete compare |
| `[g]` | retry grader | compare-and-checkin | Finish retryable artifact-graded task |
| `[t]` | revalidate | compare-and-checkin | Rerun tests only |
| `[t]` | status | release-lifecycle | Read-only posture check |
| `[w]` | weakest | compare-and-checkin | Inspect weakest-risk explanation |
| `[x]` | rollback | release-lifecycle | Revoke trust, halt monitoring |

### Convention

- Recommended action comes first, marked with `>`
- Agent accepts either the key or the word
- Outcome-specific palettes (which keys for safe/inconclusive/not-safe) are
  defined in each reference doc

## Error Handling

When a `stet` command fails, do not silently retry. Report, diagnose, offer
recovery.

| Error pattern | Agent action |
|---|---|
| Command not found / CLI error | Check `stet` installed and on PATH. Report. |
| Auth failure / 401 / 403 | Report credential issue. Do not retry. |
| Timeout | `stet eval status --out <root>`. Offer `[w]` wait or `[r]` rerun. |
| Docker / container failure | Check `docker ps`, `docker system df`, and `docker network ls`. If no run is active, offer cleanup: `docker container prune -f` and `docker network prune -f`. Then rerun with lower effective concurrency. |
| Partial / incomplete compare | Read `compare_state.next_action`. Offer recovery. |
| Invalid or degraded evidence | Read `validity` / `evidence_quality`. Lower confidence, explain the degradation, and fail closed to inspect when needed. |
| Empty / zero-score grading | Check grader cmd. Offer `[r]` rerun or `[i]` inspect. |
| `HOLD` / `INSPECT` state | Valid terminal states, not errors. Offer `[i]` inspect. |

### Error Receipt

```text
STET :: ERROR

step        <flow that failed>
error       <one-line summary>
evidence    <root or log path>
why         <diagnosis and what to try>

next        > [i] inspect   read error log or deepest evidence
then        [r] rerun       retry after fixing input
then        [s] stop        keep current state
```
