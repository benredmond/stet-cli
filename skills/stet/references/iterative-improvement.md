# Iterative Improvement

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
baseline eval ──► inspect ──► edit one thing ──► rerun ──► threshold?
     ▲                                                     ├─ met ──► [g] gate
     │                                                     └─ not ──► ↺
     └── [c] calibrate if grader trust is low ─────────────┘
```

Use this when one-shot execution is weak and the task gets better through a
scored loop. Treat the loop as bounded harness search: read the Trial Result,
choose one bottleneck, mutate one allowed Search Space lever, and rerun.

## When To Use

- "Keep iterating until the eval passes."
- "Do not stop at the first acceptable result."
- "The result is visual or subjective, but we can still score it."
- "Track progress across a long session."

Do not use this for one-shot repo safety, model comparison, or rollout
questions. Use the main routing table for those.

## Reporting

```text
STET :: LOOP

answer      improving
confidence  medium
target      recommendation_quality >= 3.6
cycle       3
best        3.4 / 4
latest      3.4 / 4
baseline    2.8 / 4
dim         rec_quality 2.8 -> 3.4  trust=med
weakest     recommendation_quality
driver      recommendation_quality improved +0.6 but trust is medium
evidence    summary.md:L42-L67
why         Rerun is next because the gain needs confirmation as stable, not
            one noisy grade.

next        > [r] rerun       confirm the gain is stable across 2 consecutive runs
then        [c] calibrate     tighten the grader if trust stays medium
then        [g] gate          materialize release state when thresholds are met
then        [s] stop          end the loop with current best
```

## Preconditions

Have:
- a repeatable eval command
- machine-readable scores or a stable report
- inspectable artifacts when logs are not enough
- an explicit stop rule (separate overall and judge thresholds)
- a known Search Space, so the agent knows which lever may change next

If the grader is mushy, split or calibrate the rubric first with
[rubric-authoring](rubric-authoring.md).

## Loop

1. Read `AGENTS.md` and find the scoring command before editing.
2. Identify the current Search Space. If the next desired edit is outside it,
   stop and ask to change the search boundary instead of silently widening it.
3. Run the baseline eval and record the current Trial Result.
4. Read persisted `eval_report.v1.json` first. Use `decision_receipt` for
   decision/confidence/readiness/next action and `trial_context` for task
   corpus, task selection, Harness Surface, Search Space, baseline/candidate,
   supporting evidence, freshness, and machine recommendation.
5. Inspect lower-level evidence only for diagnosis. Use weakest-risk output,
   `decision_receipt.tasks`, or direct artifact inspection to find the current
   bottleneck. If the output is visual, use `view_image`.
6. State a hypothesis before changing anything: "I believe ___ is causing this
   bottleneck because ___. If I change ___, I expect ___ to happen." If you
   cannot fill this in, you are guessing, not searching.
7. Make one focused change to one allowed lever that tests the hypothesis.
8. Re-run the eval immediately and read the new Trial Result.
9. Read the result against the hypothesis: confirmed, refuted, or inconclusive?
   Log the implication — what does this result teach you about the next
   hypothesis?
10. Keep the current best version. Revert only if the new result is clearly
    worse in scores or artifacts.
11. Continue until thresholds are met, evidence quality blocks the decision, or
    the eval design itself is the blocker.

Never end a loop update with scores alone. The user should always know whether
the next move is "iterate again", "calibrate the grader", or "stop and ship."

## Stet Pattern

For shared skill improvement, use the rules skill loop so the iteration stays on
the canonical rules surface and records durable loop state:

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

Read `decision_receipt` first, then `evidence.skill_loop_path`. The linked
`skill_loop.v1.json` is the loop ledger: it carries cycle, best/latest scores,
weakest dimension, diagnosis, and next recommended change. Use that weakest
dimension to form the next one-change hypothesis. Do not infer a new cycle from a
fresh report timestamp alone; only a substantively different candidate result
should advance the cycle.

For custom-rubric quality work:

```bash
stet eval workbench probe ... --out ./stet-loop
stet eval report --out ./stet-loop --json
stet eval workbench risks --grades-dir ./stet-loop/graded/candidate --weakest --json
```

Then inspect the artifact, apply one change, and repeat.

Keep a running log near the output root. Each cycle is one row in a hypothesis
chain — the implication from the previous cycle feeds the hypothesis for the
next:

```
cycle       3
hypothesis  "the 'prefer minimal diffs' rule is too vague — tasks 18/25
             show the agent ignoring it"
test        tightened wording to "never touch files outside the issue scope"
result      equiv +4pp on tasks 18/25, but task 12 regressed (-2pp review)
implication wording works for scope control but created a new rigidity
             problem on task 12 — next hypothesis should target that
scores      baseline 2.8 → latest 3.2 / best 3.4 / target 3.6
decision    iterate — target not met, new bottleneck identified
```

Minimum fields per cycle: `hypothesis`, `test`, `result`, `implication`,
`scores`, `decision`. Without `implication`, the chain breaks and the next
cycle starts from scratch instead of building on what you learned.

## Stop Condition

The loop is done when ALL three criteria are met:

1. Every dimension meets its target threshold.
2. Grader trust is high on the weakest dimension for 2 consecutive runs.
3. No dimension regressed from best.

If any criterion fails, keep iterating or calibrate.

## Flow-Specific Actions

- `[c] calibrate`: `stet eval calibrate ...` — tighten weakest/noisiest rubric
- `[g] gate`: `stet eval workbench gate --from <loop-root> --json` — only after
  stop condition is met

## Decision Rules

- If the same weakest dimension repeats twice with low trust, calibrate.
- If the artifact looks better but the score stays flat, inspect rubric trust.
- If the candidate wins clearly and the weakest remaining risk is acceptable,
  gate or ship.
- If evidence is partial, stale, missing requested graders, or outside the
  declared Search Space, inspect or repair/resume before another edit.
- If the candidate wins a baseline-first loop, refresh the baseline reference;
  do not describe that as release promotion.

## Common Mistakes

- Changing the candidate without stating what you expect to happen. If you
  cannot fill in "I believe ___ because ___", you are guessing, not searching.
- Treating each iteration as independent instead of reading the previous
  cycle's implication before forming the next hypothesis.
- Changing several things at once, then not knowing what moved the score.
- Stopping at the first pass instead of the target threshold.
- Trusting scores without looking at the generated artifact.
- Using thread memory instead of a durable loop log.
- Reconstructing the verdict from summaries when a persisted Trial Result is
  available.
