# Beta quickstart

This guide is the first-session path for a beta customer. The goal is not to
learn every Stet command. The goal is to prove that the machine is ready, one
repo can be onboarded, and the first Stet evidence can be read without guessing.

## What you will accomplish

By the end of this session, your agent should have:

1. Verified the Stet CLI, Stet auth, Docker, Harbor, GitHub auth, and the Stet
   skill.
2. Read your repo's CI and selected the real repo-level test command.
3. Created or reviewed the repo's Stet harness files.
4. Built a starter dataset from real merged work.
5. Returned an onboarding receipt and a concrete next-step recommendation.

The first session should stop before an expensive eval unless you explicitly
approve the launch.

## Before you start

Use a repo with:

- real Git history
- merged PRs or commits representative of the work you care about
- CI or documented test commands
- a test suite that can run in Docker

Then start Docker and confirm you have access to the beta CLI repo:

```sh
docker info
gh repo view benredmond/stet-cli --json visibility,url
```

If you have not installed Stet yet, start with [README.md](README.md).

## Step 1: ask your agent to check setup

In your coding agent, from the repo you want to evaluate, ask:

```text
Use the Stet skill. Check whether this machine is ready to run Stet. Verify Stet, Stet auth, Docker, Harbor, GitHub auth, model-provider auth, and the Stet skill. Do not run an eval yet.
```

Expected checks:

```sh
stet --version
stet auth status
gh auth status
docker info
harbor --version
npx skills list
```

If any check fails, fix setup before onboarding the repo. Stet should fail
closed on missing commercial auth, missing model-provider auth, and unavailable
Docker rather than launching ambiguous work.

## Step 2: ask your agent to onboard the repo

Use this prompt:

```text
Use the Stet skill. Onboard this repo for Stet evals. Read CI and package/build files first, choose the real repo-level test command, create the Harbor Dockerfile and harness manifest, run Stet init/discover/build, and report the onboarding receipt. Stop before launching smoke, probe, or rules evals.
```

Your agent should inspect CI first. CI is more trustworthy than README prose for
test setup. The selected test command should run the actual repo test suite, not
only lint, build, `echo`, or `true`.

The agent should create or update:

- `.stet/stet.yaml`
- `.stet/harbor.Dockerfile`
- `.stet/stet.harness.yaml`
- a dataset root under `.stet/` or another agreed output path
- `onboarding_receipt.v1.json` in the dataset root

## Step 3: review the onboarding receipt

Ask:

```text
Use the Stet skill. Read the Stet onboarding receipt. Summarize the candidate-task funnel, selected starter slice, skipped-task reasons, test setup, confidence, and recommended next step. Do not launch more work yet.
```

The receipt should answer:

- how many candidate tasks were scanned
- how many passed discover and build
- which tasks are in the starter slice
- why tasks were rejected or skipped
- what test command and setup source were used
- whether the starter slice is high, medium, or low confidence

If the confidence is low, improve repo setup or task selection before running a
larger eval.

## Step 4: choose the first run

Use one of these paths.

For a cheap calibration read:

```text
Use the Stet skill. Run a small first Stet smoke on this repo using the starter dataset. Keep it cheap, explain what evidence it produces, and do not make rollout claims from it.
```

For a directional read on a specific change:

```text
Use the Stet skill. Probe this change with Stet on the starter dataset. Report whether the result is usable for iteration, and do not describe it as rollout evidence.
```

For an `AGENTS.md`, `CLAUDE.md`, shared-skill, model, or harness-policy decision:

```text
Use the Stet skill. Evaluate whether this shared behavior change is safe to ship. Use the manifest-backed Stet rules flow. Run the plan first, explain task count, graders, cost risk, and evidence quality, then ask before launching the full run.
```

The rules path is the right path when you intend to keep, recommend, baseline,
promote, or roll back a shared behavior change.

## Step 5: read the result

Ask your agent:

```text
Use the Stet skill. Read the current Stet result from status/report surfaces. Tell me the recommendation, confidence, evidence quality, grader coverage, task coverage, next action, and residual risk. Do not reconstruct the verdict from pass rate alone.
```

The important lifecycle words are:

- `promote`: the evidence supports keeping the candidate as the current release
  state.
- `hold`: the evidence does not support promotion.
- `inspect`: the evidence is useful for diagnosis or iteration, but not strong
  enough for a rollout decision.

`inspect` is common on small or degraded samples. It is not the same as failure.
It means the evidence should guide the next bounded action rather than justify a
ship/no-ship claim.

## What not to do on day one

- Do not start with a 50+ task dataset unless you are deliberately doing heavy
  dataset onboarding.
- Do not compare many models at once.
- Do not treat a quick smoke or probe as a rollout decision.
- Do not promote from stale, partial, missing-grader, or replay-invalid evidence.
- Do not delete or restart a partial rules run before checking
  `stet eval status`.

## Next docs

- Use [PROMPT_COOKBOOK.md](PROMPT_COOKBOOK.md) for copy-paste prompts.
- Use [ONBOARDING.md](ONBOARDING.md) to understand how replay and grading work.
- Use [TROUBLESHOOTING.md](TROUBLESHOOTING.md) when setup or a run blocks.
