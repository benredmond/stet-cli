# How Stet works

A short, human-readable explainer for customers. Stet is designed to be operated by a coding agent on your behalf, but it helps to understand what your agent is doing when it does.

## What Stet is

Stet is change control for AI coding behavior. When you change a model, a config file like `AGENTS.md` or `CLAUDE.md`, a skill, or a tool policy, Stet measures whether the change is safe to keep. It does that by replaying real work from your repo's history against the new setup and grading the result.

You don't run Stet directly. You ask your agent — Claude Code, Cursor, Codex, or whichever one you use — to evaluate something, and your agent operates Stet on your behalf. What it hands back is a verdict you can act on. The rest of this guide explains the three things your agent does under the hood and how that verdict is earned.

## The shape of one evaluation

Every evaluation is a collection of tasks. Every task is one historical change from your repo, replayed under controlled conditions. A single task moves through four steps:

```
   real PR              repo snapshot          patch from
   from your    ───►    + prompt the    ───►   agent under   ───►   tests +
   history              agent sees             test                 quality
                                                                    graders
                                                                       │
                                                                       ▼
                                                                    verdict
```

By the time the verdict lands, every task has been through the same four steps. The verdict aggregates across them, so what you see isn't one anecdote — it's the pattern across many.

## Task selection: where the work comes from

Tasks are not synthetic benchmarks. Each task is a real merged pull request from your repo's history. Stet mines a bounded range of commits, picks the ones with a clear before and after — failing tests at the base, passing tests after the merge — and packages each one as a replayable unit. The unit contains the repo snapshot at that point in time, a prompt describing what needed to be done, and the tests that judged success.

Most tasks are gated by a fail-to-pass signal: the tests this PR was meant to make pass had to be failing beforehand. That gate is your answer key. The fact that your team merged the change is what makes the task ground truth.

This matters because the dataset isn't invented. It's your own team's merged work, with the gold change set aside as the reference. When a model or a config change is tested on these tasks, it's being tested on real engineering on your codebase, with a clear notion of "correct" because your team already shipped it.

Two details worth naming. The prompt the agent sees is a paraphrase of the PR's intent — close to a given / when / then statement — so the agent isn't handed the answer. And every task is checked for trivial passes: if the base tests already pass before any change is made, the task is rejected so an agent can't earn credit by doing nothing.

## Replay: running the agent against a frozen world

When the evaluation starts, each task launches in its own container. Inside the container is your repo at the base commit, the task prompt, and the agent under test — the model plus its tools and operating shell. The agent works as it normally would, reading files, editing code, and running tests, but the container is isolated, so nothing it does touches your real repo.

Critically, the agent sees only the starting state and the prompt. It does not see the gold patch from the original merge, the tests that will judge it, or any signal about what "correct" looks like. It produces a patch — the diff of what it changed — and a transcript of its session. That patch is what gets scored.

```
    ┌─────────────────────────────────┐        outside the container
    │  container: one per task        │        ──────────────────────
    │                                 │
    │   repo @ base commit            │        orchestrator on your
    │   prompt (paraphrased PR)       │ ───►   runner:
    │   agent under test (tools on)   │          - launches containers
    │                                 │          - collects patches
    │      ▼                          │          - applies + tests
    │   patch + transcript            │          - runs graders
    │                                 │          - writes verdict
    └─────────────────────────────────┘
```

Isolation buys three things. Reproducibility, because the same task starts from the same world every time. Safety, because the agent's actions never leak out. And fair comparison, because two models, or two configs, see the exact same starting state on every task.

## Grading: what counts as "did it land cleanly"

Grading is two layers stacked on the same patch.

The first layer is tests. The patch is applied to the snapshot, the tests the original PR was meant to make pass are run, and the rest of the test suite runs alongside to catch regressions. This is the gate: if the tests fail, the task fails. An LLM judge runs alongside, asking whether the patch is semantically the same as the gold change, but that signal is diagnostic only. It never upgrades a failed task to a pass.

The second layer is quality. Once a patch is past the test gate, eight LLM-judged graders score it on craft — clarity, simplicity, coherence, intentionality, robustness — and discipline — instruction adherence, scope discipline, diff minimality. Each grader returns a 0–4 score with strengths and risks, citing specific lines. Two other LLM passes sit alongside: a code review and a footprint-risk check that asks how much surface area the diff touches.

Two layers, because binary pass rate alone doesn't separate strong frontier models. They all pass most tests on real work. The quality layer is where differentiation lives. It's what lets the verdict say not just "this candidate works" but "this candidate works, and the diffs are tighter, the scope is more disciplined, and the changes are more idiomatic to your codebase."

A note on the judges: the model used for grading is always picked to be different from the model being graded, so no model grades its own work.

## The verdict, and the loop your agent runs

At the end, Stet writes a structured decision: promote, hold, or rollback. It is not a single number. It names the dataset that was used, the two arms being compared (for example, your old config and your new one), the graders that ran, the per-dimension deltas, the evidence quality, and a next action. If the evidence is partial, stale, or mixed, the verdict fails closed — Stet won't say "promote" without enough signal to defend the call. Your agent reads this verdict (it lives in a file called `eval_report.v1.json`) and tells you, in plain language, whether the change is safe to ship and why.

The verdict isn't only an end state — it's also a step. Stet's natural workflow is iterate and improve, and it pairs cleanly with Claude Code's `/goal` to keep your agent working autonomously until the verdict crosses a bar you set. For example:

```
/goal AGENTS.md wins on the weekly Stet eval with no regressions on scope_discipline
```

Your agent then proposes a change, runs the eval, reads the verdict, edits one thing, and reruns — turn after turn — until the goal is met. The same loop works for skills, prompts, tool policies, or your choice of model. The verdict is what closes each turn; `/goal` is what keeps the loop going.

If you want to see your agent run all of this, point it at the agent-facing front door in [`README.md`](README.md).
