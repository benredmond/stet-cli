# Release Lifecycle

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
gate ──► promote ──► monitor
  ▲        │           │
  │        │       ┌───┴────┐
  │        ▼       ▼        ▼
  │    promoted  [t] status  [m] monitor
  │        │
  │        └── [x] rollback ──► revoked
  │                               │
  └────── [r] rerun ──────────────┘
```

Use this for gate, promote, monitor, and rollback after a compare or workbench
flow produced a bounded decision candidate.

Decision Policy v1 is projected through lifecycle fields, not a separate
manifest or object. Read the Trial Result first, then use `lifecycle` fields
such as `trust_state`, `rollout_state`, `freshness_status`, `gateable`,
`promotable`, `monitorable`, `next_action`, and `next_command` to decide
whether the safe move is promote, monitor, rerun, inspect, or stop.

Do not collapse baseline refresh into release promotion. Baseline refresh
changes the frozen reference for future searches; release promotion changes
rollout state for a gated capability.

Common custom-rubric quality path:

```bash
stet eval workbench probe ...
stet eval report --out <probe-root> --json
stet eval workbench gate --from <probe-root> --json
stet promote --out <compare-gate-root> --reason "..." --json
```

## Gate

Gate is the canonical handoff from bounded evidence to release state.
Gate should follow a completed Trial Result whose `decision_receipt`,
`trial_context`, and lifecycle posture make the candidate gateable. If evidence
is stale, partial, or outside the Search Space, inspect or rerun before gate.

Gate receipt:

```text
STET :: GATE

answer      safe
confidence  medium
decision    promote_candidate
trust       gated
rollout     eligible_for_monitoring
freshness   fresh
evidence    .tmp/stet-compare
why         Promote is next because gate has already established trust, and
            promotion is what turns that bounded win into current release state.

next        > [p] promote   persist the gated win as release state
then        [i] inspect     review release evidence before mutating rollout
then        [s] stop        keep the gated result without promoting
```

State vocabulary:
- `trust`: `inspect`, `hold`, `gated`, `promoted`, `revoked`
- `rollout`: `none`, `candidate_only`, `eligible_for_monitoring`,
  `monitoring`, `rolled_back`
- `freshness`: `fresh`, `aging`, `stale`

Flow-specific actions:
- `[p] promote`: `stet promote --out <compare-gate-root> --reason "..."`
- `[m] monitor`: `stet monitor run --release release.v1.json --out ./monitor-rerun`
- `[x] rollback`: `stet rollback --out <compare-gate-root> --reason "..."`
- `[t] status`: `stet monitor status --release release.v1.json --json`

## Promote

```bash
stet promote --out <compare-gate-root> --reason "quality improved without regressions" --json
```

Promote normally requires a trusted release.
Read `release.v1.json` only as the lifecycle authority for diagnosis or
post-gate state. The completed Trial Result remains the first read for the
decision that made promotion eligible.

If trust is still `inspect` but the operator intentionally wants to ship
despite inconclusive evidence, use an explicit override:

```bash
stet promote --out <compare-gate-root> --reason "shipping with operator override" --allow-inspect --json
```

This preserves `trust_state=inspect`, marks the rollout as operator override,
and should be treated as a higher-risk launch than a trusted promotion.
Do not use this for `hold` results.

When release metadata exists, show it in an instrument-style ASCII receipt:

```text
STET :: RELEASE

answer      safe
confidence  medium
trust       promoted
rollout     monitoring
freshness   aging
data        monitor 5/5 green  last delta +0.04
why         Monitor is next because the candidate is unchanged and the only
            missing thing is fresh evidence, not a new compare decision.

next        > [m] monitor   replay the frozen release contract for fresh signal
then        [r] rerun       return to probe if the candidate or policy changed
then        [x] rollback    revoke trust if new risk outweighs confidence
```

## Monitor

```bash
stet monitor status --release release.v1.json --json
stet monitor run --release release.v1.json --out ./monitor-rerun --json
```

Use `monitor status` for a read-only posture check.

Use `monitor run` to execute a fresh monitoring rerun from the promoted release
contract. It writes a new monitoring output root and refreshes monitoring
evidence on the release. It is not just a status read.

Do not pass a baseline snapshot to `stet monitor run --release ...`. Baseline
snapshots stop at compare or gate; monitor remains release-only.

Replay contract:
- `monitor run` should be explained as replaying the promoted release's frozen
  `task_selection` and arm provenance, not rediscovering tasks from the current
  repo.
- `task_selection` carries the frozen `requested`, `recommended`, and
  `realized` task ids for replay.
- If replay detects drift in the stored slice, repo-state bindings, skill
  digest, context-pack digest, or managed-baseline provenance, the correct
  operator explanation is fail-closed and reprobe, not silent refresh.

When to choose what:
- `monitor status`: read-only posture check
- `monitor run`: unchanged candidate, stale or aging evidence
- `reprobe`: model, policy, artifact, or dataset contract changed

## Monitor Decision Function

Use this to decide which monitor action to take. Read `freshness_status`
and candidate state from the release JSON.

| Condition | Action | Command |
|---|---|---|
| Just checking posture | `monitor status` | `stet monitor status --release release.v1.json --json` |
| freshness=`aging` or `stale`, candidate unchanged | `monitor run` | `stet monitor run --release release.v1.json --out ./monitor-rerun --json` |
| Candidate, model, policy, artifact, or dataset changed | `reprobe` | return to probe or compare flow |
| Trust regression detected | `rollback` or `reprobe` | `stet rollback --out <root> --reason "..."` |

Machine-readable contract:
- `monitor status` is read-only. It queries the release record and returns
  posture without executing work. `lifecycle.execution_status` reflects the
  last known state, not a fresh measurement.
- `monitor run` is execute. It replays the promoted release's frozen
  `task_selection`, runs the evaluator, and writes fresh monitoring evidence.
  `lifecycle.freshness_status` updates to `fresh` on success.
- If the operator only wants refreshed benchmark evidence for a baseline
  snapshot, the correct command is `stet baseline rerun --baseline <snapshot>`,
  not `stet monitor run`.

Never recommend `monitor run` when the candidate has changed. The correct
action is `reprobe` because the frozen task selection contract may no longer
apply.

## Roll Back

```bash
stet rollback --out <compare-gate-root> --reason "regression detected" --json
```

Rollback postconditions:
- `trust = revoked`
- `rollout = rolled_back`
- monitoring should halt until new evidence exists
- the default next step is inspect or reprobe, not promote again

## Rules

- Release path, trust state, and rollout state appear only after gate.
- Promote, monitor, and rollback are lifecycle actions, not first-line eval
  entry points.
- Decision Policy v1 is the lifecycle projection; do not invent a separate
  policy artifact or override `next_action` without explicit operator intent.
- `monitor status` reads the promoted release; `monitor run` executes work
  again and merges fresh evidence back into that release record.
- When a release regresses, the next step is usually re-probe or re-run after
  fixing the candidate, not repeated promote attempts.
- Always end lifecycle answers with keyed next actions so the operator knows
  whether to monitor, re-probe, or roll back.
- Use state-conditioned action palettes:
  `hold|inspect` -> `> [i] inspect [r] rerun [s] stop`
  `promoted+fresh` -> `> [t] status [m] monitor [x] rollback`
  `promoted+stale` -> `> [m] monitor [r] rerun [x] rollback`
  `rolled_back` -> `> [i] inspect [r] rerun [s] stop`
