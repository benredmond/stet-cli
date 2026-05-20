# Prompt cookbook

Use these prompts with your coding agent. They are written to keep Stet
agent-driven: you state the outcome, and the agent chooses the right Stet
surface, reads the canonical artifacts, and reports the decision.

## Setup

```text
Use the Stet skill. Install and verify Stet for this machine using the beta docs. Verify GitHub access, Stet CLI, Stet auth, Docker, Harbor, model-provider auth, and the Stet skill. Stop after setup verification; do not run evaluations yet.
```

```text
Use the Stet skill. Check whether this repo is ready for Stet. Inspect CI, build files, test commands, Docker assumptions, and model-provider auth. Report blockers before editing files or launching evals.
```

## Repo onboarding

```text
Use the Stet skill. Onboard this repo for Stet evals. Read CI and package/build files first, choose the real repo-level test command, create the Harbor Dockerfile and harness manifest, run Stet init/discover/build, and report the onboarding receipt. Stop before launching smoke, probe, or rules evals.
```

```text
Use the Stet skill. Read the Stet onboarding receipt. Summarize the candidate-task funnel, selected starter slice, skipped-task reasons, test setup, confidence, and recommended next step. Do not launch more work yet.
```

```text
Use the Stet skill. The onboarding confidence is low. Diagnose whether the blocker is test setup, Docker/Harbor setup, weak task history, path-sensitive tests, or task selection. Propose the smallest fix before running more Stet work.
```

## First evaluation

```text
Use the Stet skill. Run a small first Stet smoke on this repo using the starter dataset. Keep it cheap, explain what evidence it produces, and do not make rollout claims from it.
```

```text
Use the Stet skill. Probe this change with Stet on the starter dataset. Report whether the result is usable for iteration, and do not describe it as rollout evidence.
```

```text
Use the Stet skill. Read the current Stet result from status/report surfaces. Tell me the recommendation, confidence, evidence quality, grader coverage, task coverage, next action, and residual risk. Do not reconstruct the verdict from pass rate alone.
```

## AGENTS.md or CLAUDE.md changes

```text
Use the Stet skill. Evaluate whether this AGENTS.md change helps. Use the manifest-backed Stet rules flow. Run the plan first, explain task count, graders, cost risk, and evidence quality, then ask before launching the full run.
```

```text
Use the Stet skill. Evaluate whether this CLAUDE.md change is safe to ship. Use the same model in baseline and candidate so the only intended lever is the instruction file. Run the rules plan first and tell me whether the evidence will be decision-grade.
```

```text
Use the Stet skill. Improve this instruction file one lever at a time. After each Stet run, read the Trial Result, explain the bottleneck, make one scoped edit, and stop when evidence is inspect-only or not improving.
```

## Model comparisons

```text
Use the Stet skill. Compare these two models on my repo using Stet. Use existing frozen baseline evidence if available; otherwise start with the smallest useful smoke or probe. Report correctness, quality dimensions, cost, and residual risk.
```

```text
Use the Stet skill. Compare these two reasoning levels on the same model. Keep every other harness setting fixed, expose the effective reasoning setting for both arms, and report whether the evidence is decision-grade or only directional.
```

```text
Use the Stet skill. Tell me which model should be my default for this repo. Use Stet history if available, separate inherent LLM variance from workflow/setup risk, and do not recommend a default from stale or partial evidence.
```

## Skill evaluation

```text
Use the Stet skill. Test whether this skill improves agent behavior. Compare skill absent or effectively empty versus skill present, use behavior-relevant graders, and report whether the evidence supports keeping it.
```

```text
Use the Stet skill. Improve this shared skill with Stet. Use the rules-skill loop, keep the search space to skill text only, run the plan before launch, and after each result choose exactly one next change or stop.
```

```text
Use the Stet skill. Before I publish this skill revision, verify whether the latest Stet evidence supports promotion, hold, or inspect. Include task coverage, grader coverage, freshness, and the exact next action.
```

## Status and recovery

```text
Use the Stet skill. Check the current Stet run. Use status/report surfaces only, tell me whether it is running, stalled, exited, repairable, or complete, and give the exact next command.
```

```text
Use the Stet skill. This Stet rules run looks incomplete. Check status first, identify whether the launcher is still active, and use rules repair only if the run has exited or stalled. Do not restart unless I explicitly approve discarding evidence.
```

```text
Use the Stet skill. This Stet run returned inspect. Explain whether inspect came from small sample size, stale evidence, missing graders, replay validity, infrastructure failure, mixed results, or another concrete reason. Recommend one bounded next action.
```

## Promotion safety

```text
Use the Stet skill. Before recommending promotion, verify the result is decision-grade: fresh evidence, expected graders, enough task coverage, no replay-validity failure, no missing compare decision, and no inspect-only lifecycle state.
```

```text
Use the Stet skill. Summarize this Stet result for a PR or Slack thread. Lead with promote, hold, or inspect; include why, what evidence ran, what risk remains, and the next action. Keep it readable for an engineering lead who has not used Stet.
```

## Custom quality criteria

```text
Use the Stet skill. Help me write a custom Stet grader for this repo. Start by asking what behavior I care about, draft a small rubric, calibrate it against existing patches if possible, and do not use it for a rollout decision until coverage is present in the report.
```

```text
Use the Stet skill. Evaluate this research or plan artifact with Stet. Choose or write a custom rubric first, explain what the rubric measures, and report the result as artifact quality rather than code correctness.
```

## Good default instruction to your agent

```text
Use the Stet skill. Keep the workflow bounded. Read status/report artifacts as the source of truth, change one lever at a time, treat inspect as a diagnostic state, and ask before launching expensive evals or discarding existing evidence.
```
