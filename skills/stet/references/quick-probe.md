# Quick Probe

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
probe ──► report ──► safe?
                     ├─ yes ──► [g] gate  [b] baseline  [s] stop
                     ├─ uncertain ──► [i] inspect  [r] rerun  [s] stop
                     └─ no ──► [i] inspect  [v] revise  [s] stop
```

Use this for the smallest repo-local answer.

## Repo candidate

```bash
stet probe --model "sonnet 4.6" --repo . --json
stet eval report --out <probe-root> --json
```

## Config or instruction file

```bash
stet probe --file AGENTS.md --model "sonnet 4.6" --repo . --json
stet eval report --out <probe-root> --json
```

`stet probe --file ...` is the fastest directional read for an instruction or
skill file on a real repo. It is not the release-grade path for "is this
AGENTS.md / CLAUDE.md / shared skill safe to ship?", "is this helping?", or
"should this become the default?" Use the manifest-backed rules flow for those
questions.

When the target lives under `.agents/skills/...` or `.claude/skills/...`,
`stet eval config-diff --file ...` evaluates the managed-skill runtime envelope,
not just an isolated prompt-template file.

## Explicit file diff

Use `config-diff` when the operator is thinking in terms of before/after files
or wants a cheap A/B prefilter.

```bash
stet eval config-diff --repo . --file CLAUDE.md --model "sonnet 4.6" --json
```

Or with explicit files:

```bash
stet eval config-diff \
  --repo . \
  --before ./.tmp/stet-config-diff/claude.before.md \
  --after ./CLAUDE.md \
  --logical-path CLAUDE.md \
  --model "sonnet 4.6" \
  --json
```

Treat the config-diff root itself as the canonical operator surface. If both
arms finish but `experiment.json` is missing, Stet now either materializes the
compare on that same root or fails closed with an inspect receipt that includes
the exact `stet eval config-diff ... --out <same-root>` rerun command.

For pairwise compare semantics over arbitrary plain files without template
authoring:

```bash
stet eval compare \
  --dataset ./.tmp/my-dataset \
  --out ./.tmp/stet-compare \
  --baseline-model "sonnet 4.6" \
  --candidate-model "sonnet 4.6" \
  --baseline-file ./.tmp/agents.before.md \
  --candidate-file ./AGENTS.md \
  --logical-path AGENTS.md \
  --grader equivalence \
  --grader code_review \
  --grader footprint_risk \
  --json
```

**Use the manifest-backed rules flow** for AGENTS.md / CLAUDE.md A/B testing
when the result will guide a retained candidate, rollout, baseline refresh, or
claim that shared agent behavior improved. The rules flow (`stet eval rules`
with `stet.change.yaml` + `stet.suite.yaml`) provides provenance, release
lifecycle integration, and the custom grader surface. Use `config-diff` and
`--baseline-file`/`--candidate-file` only as prefilters for throwaway
iterations, and label their results as directional. See
[rules-flow](rules-flow.md) for the manifest-backed approach.

## Quick first-run benchmark

Use `eval smoke` when the user wants a tiny multi-model read, not a formal
benchmark suite.

```bash
stet eval smoke --repo . --models "opus 4.6,sonnet 4.6" --tasks 5 --json
```

## Escalate Only When Needed

- Need a reusable frozen "before" object for later compare or rerun continuity:
  `stet baseline freeze --from <probe-root> --name <capability> --json`
- Need a read-only baseline snapshot check after freezing:
  `stet baseline status --baseline <snapshot> --json`
- Need trust state, rollout state, or a release path: run a gated flow.
- Need a broader benchmark: move to [full-evals](full-evals.md).
- Need to grade a skill, research note, or plan: first define a custom rubric
  with [rubric-authoring](rubric-authoring.md).

## Reporting Contract

When you report a quick-probe result:
- say whether this was a `probe`, `report`, or `status` read
- answer the user first with `safe`, `not safe`, or `inconclusive`
- include `confidence: high|medium|low`
- show baseline vs candidate, sample size, and explicit deltas
- name the dominant driver behind the call
- explain why the recommended next action is next and what it means
- end with keyed next actions so the user can reply with one keystroke
- use an instrument-style ASCII receipt when the probe already finished

Example:

```text
STET :: QUICK PROBE

answer      inconclusive
confidence  medium
step        probe -> inspect
compare     candidate vs baseline
sample      5 tasks
delta       pass -0pp  equiv -6pp  review +3pp
driver      review risk rose on 2/5 tasks
why         Inspect is next because the regression signal is real, but still
            too small to treat as either a release block or a false alarm.

next        > [i] inspect   read task-level evidence before rollout changes
then        [r] rerun       gather fresh evidence after revising the candidate
then        [s] stop        keep the current bounded verdict only
```

Outcome palettes:
- safe with benchmark intent: `> [b] baseline [g] gate [s] stop`
- safe: `> [g] gate [i] inspect [s] stop`
- inconclusive: `> [i] inspect [r] rerun [s] stop`
- not safe: `> [i] inspect [v] revise [s] stop`

Flow-specific action:
- `[b] baseline`
  command: `stet baseline freeze --from <probe-root> --name <capability> --json`
  use when the operator wants a trackable snapshot before gate or promotion

## Rules

- Read completed quick-probe roots with `stet eval report --out ... --json`.
- For machine reads, prefer persisted `eval_report.v1.json` when present. Read
  `decision_receipt` for the verdict and next action, then `trial_context` for
  task selection, Harness Surface, Search Space, baseline/candidate, freshness,
  and machine recommendation. Use outer `lifecycle`, `validity`,
  `evidence_quality`, and `arms` to interpret the verdict.
- For dataset-backed `config-diff` and plain-file `compare`, Stet uses all
  realized tasks by default; add `--task-id` / `--task-pr` only when you need a
  narrower slice.
- Do not tell the operator to repair `origin/HEAD` or default-branch metadata
  for repo-file flows unless the command actually failed. Stet now falls back to
  repo-local default-branch resolution when possible.
- If the next operator question is "freeze this as the baseline" or "rerun this
  same baseline later," prefer `stet baseline freeze` over telling them to
  preserve a raw probe root by path convention.
- Use `stet eval status` only when a run is active or the user explicitly wants
  status/health.
- Prefer repo-local `.tmp/stet-*` roots over system `/tmp` because they are
  easier to inspect later and avoid macOS symlink-ancestor surprises.
- If the user only asked for a quick safety read, do not dump extra commands
  without giving keyed next actions that make the next step obvious.
- Do not recommend `gate` by default on an inconclusive or unsafe quick probe.
