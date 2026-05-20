# How Stet works

This is a short explainer for humans. Stet is designed to be operated by a
coding agent on your behalf, but it helps to understand what your agent is doing
when it runs Stet.

## What Stet is

Stet is a measurement function for AI coding behavior. When you change a model,
an instruction file such as `AGENTS.md` or `CLAUDE.md`, a shared skill, or a tool
policy, Stet measures whether the change is safe to keep.

It does that by replaying real work from your repo's history against the new
setup and grading the result. The output is not just a scorecard. It is a
decision artifact your agent can read and explain.

You usually do not run Stet directly. You ask your agent, such as Claude Code,
Codex, Cursor, or another coding agent, to evaluate something. The agent uses
Stet, reads the result, and tells you what action the evidence supports.

## Why real repo history matters

Stet tasks are not synthetic benchmark prompts. Each task comes from a real
merged pull request or commit from your repo. Stet packages that historical work
as a replayable unit:

- the repo snapshot before the change
- a prompt describing what needed to be done
- the tests or validation signal that judged success
- the original shipped change, kept hidden from the model under test

This matters because the task represents engineering work your team already
accepted. When a model or config change performs better on these tasks, the
evidence is grounded in your codebase rather than a generic benchmark.

## What one evaluation looks like

An evaluation is a collection of replayed tasks. Each task follows this shape:

```text
real PR or commit
  -> repo snapshot before the change
  -> prompt shown to the agent under test
  -> patch produced by that agent
  -> tests and quality graders
  -> task verdict
```

Across the task set, Stet compares the baseline and candidate behavior and
writes a structured result.

## Replay: running the agent against a frozen world

When a task starts, Stet launches a container with the repo at the base commit,
the task prompt, and the agent under test. The agent can read files, edit code,
and run commands as it normally would, but the container is isolated from your
real checkout.

The agent does not see the gold patch from the original merge. It does not see
the hidden judging tests. It sees the starting state and the task prompt, then
produces a patch and a transcript. Stet applies and scores that patch.

```text
container: one task
  repo at base commit
  prompt
  agent under test
      |
      v
  patch + transcript
      |
      v
orchestrator
  applies patch
  runs tests
  runs graders
  writes verdict
```

## Grading: tests first, quality next

Grading has two layers.

The first layer is correctness. Stet applies the candidate patch to the task
snapshot and runs the relevant tests. It also checks whether the patch is
semantically aligned with the original human intent, so a patch can be judged as
more than just "some tests passed."

The second layer is quality. Once Stet has a patch to inspect, LLM-backed
graders can review it for dimensions such as code review quality, equivalence,
footprint risk, clarity, simplicity, coherence, intentionality, robustness,
instruction adherence, scope discipline, and diff minimality.

Footprint risk asks whether the patch touched more surface area than the task
called for. A model can pass tests and still make a broad, fragile, or
hard-to-review change. This is why pass rate alone is not enough for Stet's
core decisions.

You can also ask your agent to write custom graders for dimensions that matter
to your team, such as migration safety, API compatibility, documentation
quality, or security posture.

## The verdict

At the end, Stet writes a structured decision, usually through
`eval_report.v1.json` and the matching `stet eval report` command. The result
names:

- the task corpus that ran
- the baseline and candidate arms
- which tests and graders ran
- per-dimension deltas
- evidence quality
- lifecycle posture
- the recommended next action

If evidence is partial, stale, missing important graders, replay-invalid, or
otherwise not decision-grade, Stet fails closed. It should not say "promote"
unless the evidence is strong enough to defend that call.

## Promote, hold, and inspect

Stet's most important outputs are lifecycle recommendations:

- `promote`: the evidence supports keeping the candidate as the current release
  state.
- `hold`: the evidence does not support promotion.
- `inspect`: the evidence is useful for diagnosis or iteration, but not strong
  enough for a rollout decision.

`inspect` is common and normal, especially on small samples or degraded
evidence. Treat it as a signal to choose the next bounded action, not as a
generic failure.

## The improvement loop

Stet is meant to support iteration, not only one-time gates. The loop is:

```text
ask a question
  -> identify the behavior change being tested
  -> run the cheapest Stet flow that preserves the decision you need
  -> read the Trial Result
  -> choose one next action
  -> edit one allowed lever, rerun, promote, hold, inspect, or stop
```

For example:

```text
Use the Stet skill. Pursue this goal: improve CLAUDE.md on my Stet dataset to make my diffs more aligned with human intent.
```

Your agent can propose an edit, run Stet, read the result, make one scoped
change, and rerun. The same loop works for instruction files, skills, prompts,
tool policies, model choices, and reasoning levels.

The important constraint is that each iteration should change one meaningful
lever at a time. If you change the model, instructions, tools, and task slice
together, the result may still be interesting, but it will be hard to know what
caused the difference.

## Where to go next

- Start with [README.md](README.md) for install and verification.
- Use [BETA_QUICKSTART.md](BETA_QUICKSTART.md) for your first repo onboarding.
- Use [PROMPT_COOKBOOK.md](PROMPT_COOKBOOK.md) for copy-paste prompts.
- Use [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when setup or a run blocks.
