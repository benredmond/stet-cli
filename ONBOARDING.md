# How Stet works

A short explainer of Stet. Stet is designed to be operated by a coding agent on your behalf, but it helps to understand what your agent is doing when it does.

## What Stet is

Stet is a measurement function for AI coding behavior. When you change a model, a config file like `AGENTS.md` or `CLAUDE.md`, a skill, or a tool policy, Stet measures whether the change is safe to keep, and how it performs. It does that by replaying real work from your repo's history against the new setup and grading the result.

You don't run Stet directly. You ask your agent - Claude Code, Cursor, Codex, or whichever one you use - to evaluate something, and your agent operates Stet on your behalf. What it hands back is a recommendation that you can act on. The rest of this guide explains, at a high level, what Stet is doing under the hood when it's evaluating your change.

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

## Task selection: where the work comes from

Tasks are not synthetic benchmarks, instead, each task is a real merged pull request (or commit) from your repo's history. Stet mines a bounded range of PRs, does some filtering, and packages each one as a replayable unit. The unit contains the repo snapshot at that point in time, a prompt describing what needed to be done, and the tests that judged success for that task. The prompt the agent sees is a paraphrase of the PR's original intent.

Most tasks are gated by a fail-to-pass signal: the tests this PR was meant to make pass had to be failing beforehand. In other words, if PR #123 adds test fooBar(), then fooBar() should fail prior to #123, and succeed after it. However, if your repo doesn't operate this way, this option can be disabled.

When a model or a config change is tested on these tasks, it's being tested on real engineering on your codebase, with a clear notion of "correct" because your team already code reviewed and shipped it.

## Replay: running the agent against a frozen world

When the evaluation starts, each task launches in its own container. Inside the container is your repo at the base commit, the task prompt, and the agent under test - the model plus its tools and operating shell. The agent works as it normally would, reading files, editing code, and running tests, but the container is isolated, so nothing it does touches your real repo.

Critically, the agent sees only the starting state and the prompt. It does not see the gold patch from the original merge, the tests that will judge it, or any signal about what "correct" looks like. It simply produces a patch (the diff of what it changed) and a transcript of its session. That patch is what gets scored.

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

## Grading: what counts as "did it land cleanly"

Grading is two layers stacked on the same patch.

The first layer is tests. The patch is applied to the snapshot, the tests the original PR was meant to make pass are run, and the rest of the test suite runs alongside to catch regressions. An LLM judge runs alongside, asking whether the patch is semantically the same as the gold change, testing whether the patch matches human intent.

The second layer is quality. Once a patch is past the test gate, Two LLM-judged graders sit alongside: a code review, and a footprint-risk check that asks how much surface area the diff touches compared to the .

Eight other optional, but default enabled, LLM passes score it on craft: clarity, simplicity, coherence, intentionality, robustness, and discipline: instruction adherence, scope discipline, diff minimality. Each grader returns a 0–4 score with strengths and risks, citing specific lines. 

You can also ask your agent write your own custom graders to evaluate the agent patches on metrics that matter to you.

This is two layers because binary pass rate alone doesn't separate strong frontier models. They all pass most tests on real work. The quality layer is where differentiation lives. It's what lets the verdict say not just "this candidate works" but "this candidate works, and the diffs are tighter, the scope is more disciplined, and the changes are more idiomatic to your codebase."

A note on the judges: ideally, the model used for grading is different from the model being graded, so the model isn't grading its own work.

## The verdict, and the loop your agent runs

At the end, Stet writes a structured decision. It names the dataset that was used, the two arms being compared (for example, your old config and your new one), the graders that ran, the per-dimension deltas, the evidence quality, and a next action. If the evidence is partial, stale, or mixed, the verdict fails closed - Stet won't say "promote" without enough signal to defend the call. Your agent reads this verdict (it lives in a file called `eval_report.v1.json`) and tells you, in plain language, whether the change is safe to ship and why.

Note that often, graders will return "inspect" due to lack of sufficient data, or mixed signals. This is very normal when evaluating LLMs, and should be read as a signal rather than a mandate. 

The verdict isn't only an end state - it's also a step. Stet's natural workflow is iterate and improve, and it pairs cleanly with Claude Code's `/goal` to keep your agent working autonomously until the verdict crosses a bar you set. For example:

```
/goal improve CLAUDE.md on my Stet dataset to make my diffs more aligned with human intent
```

Your agent then proposes a change, runs the eval, reads the verdict, makes an edit, and reruns, turn after turn, until the goal is met. The same loop works for skills, prompts, tool policies, or your choice of model. The verdict is what closes each turn; `/goal` is what keeps the loop going.

If you want to see your agent run all of this, point it at the agent-facing front door in [`README.md`](README.md).
