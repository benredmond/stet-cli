# Rules Flow

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
manifest resolve ──► eval rules plan ──► eval rules ──► status ──► report
                                                        │          │
                                                    [w] wait   [p] promote  [i] inspect  [s] stop
                                                        │
                                                    [c] resume compare
```

Use this for manifest-backed change control.

This is the right path when the operator wants a formal rollout decision from
`stet.change.yaml` and `stet.suite.yaml`, not just a repo-local directional
read.

For AGENTS.md, CLAUDE.md, shared skill, or harness-policy optimization, this is
also the required path for any candidate the agent intends to keep, recommend,
baseline, promote, or describe as improving shared behavior. A prior
`config-diff` can be cited only as a directional prefilter; it does not replace
the rules run or prove custom `agents_*` grader coverage.

## Flow

```bash
stet manifest resolve --change-manifest .stet/rules/stet.change.yaml
stet eval rules plan --change-manifest .stet/rules/stet.change.yaml --suite-manifest .stet/rules/stet.suite.yaml --json
stet eval rules --change-manifest .stet/rules/stet.change.yaml --suite-manifest .stet/rules/stet.suite.yaml
stet eval status --change-manifest .stet/rules/stet.change.yaml --json
stet eval rules resume --change-manifest .stet/rules/stet.change.yaml --json
stet eval report --change-manifest .stet/rules/stet.change.yaml --json
```

Roles:
- `manifest resolve`: inspect normalized inputs before launch. Prints the canonical resolved change manifest as YAML (or JSON with `--json`); injected defaults (e.g. `context.baseline.source`, `context.candidate.source`, `policy.version`, `treatments[*].path`) are inlined silently — there is no separate validation verdict.
- `eval rules plan`: preflight tasks, arms, graders, frozen-baseline reuse, cost confidence, missing pricing/cost data, and cheaper alternatives without writing runtime artifacts or launching evaluator work. This is the last cheap step — the next command, `stet eval rules` without `--plan`, is the charged launch.
- `eval rules`: launch the bounded rules-backed run
- `eval status`: explain the current phase or health
- `eval rules resume`: recover an incomplete rules compare from the persisted runtime; when the surface is replayable, it can resume a baseline-phase compare or rerun a missing/partial candidate arm while preserving completed evidence, then repair/regrade missing coverage. Pass `--parse-retries N` to forward grader JSON parse-repair attempts during regrade recovery. Pass `--report-mode separate_axes|strict_publishable_pass` to pin the reporting mode when the baseline and candidate arms were produced by Stet binaries whose default drifted; baseline mode is used automatically otherwise.
- `eval report`: read the finished rollout decision

`--ai-cmd` is a launch-only override for `stet eval rules`; use an absolute
script path when launching from scratch directories. When the model under test
should not grade its own work, persist `eval.grader_ai_cmd` and
`eval.grader_ai_model_id` in `stet.suite.yaml` so validation graders use the
same independent evaluator across reruns. Use `--grader-ai-cmd` plus
`--grader-ai-model-id` only for one-off launch overrides.

To iterate on a high-signal slice from an existing dataset, pass repeatable
`--task-id <id>` to `eval rules plan` and `eval rules`, or put the stable slice
in the suite manifest as `selection.task_ids`. Task IDs must match ready task
directories in `eval.dataset`.

`stet eval rules` is non-destructive by default when a matching rules runtime
already exists. It reuses completed evidence, auto-resumes candidate-phase
partial evidence when Stet can prove the replay is safe, and refuses to discard
partial arm evidence. Use `stet eval status --change-manifest ...` before any
recovery decision, then `stet eval rules resume --change-manifest ... --json`
when the active process has exited or status is stalled. Use `--restart` only
when intentionally discarding existing evidence and starting over.

Fresh rules runs use the same bounded preflight policy as `stet eval run`: one
representative smoke pre-pass before canonical work, not one smoke run per arm.
Candidate arms are preferred over baseline arms for that single smoke. Successful
smoke artifacts are seeded into the canonical root so smoked tasks count toward
the full run.

## Default Quality Graders

For non-skill treatments (AGENTS.md, CLAUDE.md, model_update, harness_bundle,
docs_glob), `eval rules` automatically includes the repo's quality graders from
`stet.yaml` `quality:` config, or the recommended default (`discipline` bundle +
`intentionality`) when no quality config exists. This ensures decision-grade
evidence on the first run without requiring post-hoc `regrade-graders`.

Use `--no-quality` to suppress automatic quality grader inclusion.

Skill treatments (`skill_diff`) do not receive bundled quality graders; they use
the `skill_workbench` pack instead (see below).

Missing expected quality graders produce an `inspect` verdict with a concrete
`regrade-graders` repair command.

## Skill Comparison Modes

Classify the skill question before choosing a command:

| Question | Baseline | Surface | Graders |
|---|---|---|---|
| Does adding this skill help? | no usable skill guidance | manifest-backed `stet eval rules`, or frozen-baseline compare | `equivalence`, `footprint_risk`, and custom behavior rubrics; use `quality_only` rubrics when repo tests are not signal |
| Is this skill revision better? | committed prior skill | `stet eval rules skill` | wrapper defaults, or explicit `--grader` overrides |
| Is the SKILL.md itself well written? | prior or candidate skill text | `skill_workbench` | `skill_workbench` dimensions |

For new-skill A/B tests, do not commit a vague v0 skill just to create an
anchor. Prefer a true skill-absent baseline. If `skill_diff` needs exactly one
baseline match, a committed placeholder is acceptable only when it has an
impossible trigger and no actionable guidance; report it as "effectively no
skill", not as literal absence.

For manifest-backed `stet eval rules`, put custom graders in
`change.rules.graders`; `stet eval rules` does not accept `--grader` launch
flags. For `stet eval rules skill`, repeated `--grader` flags are wrapper
inputs and replace the default grader set.

Use `skill_workbench` when the decision is about skill text quality. For the
first "with skill vs without skill" sanity check, behavior graders should carry
the decision because they grade the agent's output on replay tasks.

Choose test posture before launch. Use `tests_gated` only when repo test
pass/fail is part of the skill decision. If the skill is intended to improve
agent process, routing, or transcript behavior and repo tests add no signal,
use `quality_only` in `change.rules.mode` and make custom behavior rubrics
`mode: quality_only`. Do not tell the operator tests will be skipped unless the
chosen flow actually avoids fresh Harbor validation; validation-backed runs may
still materialize task details even when tests are non-decisive.

## Shared Skill Wrapper

For repo-managed shared skill iteration, prefer the wrapper instead of hand-writing
the first change/search-space/suite bundle:

```bash
stet eval rules skill \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --plan \
  --json

stet eval rules skill \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --test "go test ./..." \
  --json

stet eval status --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
stet eval report --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
```

Use the `--plan` form before launch when the operator needs a budget decision;
it does not write the wrapper bundle, build the replay dataset, or launch
`eval rules`.
For wrapper runs, put any `--ai-cmd` on the non-plan launch; the wrapper
forwards it to delegated `stet eval rules`.
If `stet eval rules plan` is blocked by commercial entitlement, treat that as an
access/preflight limitation rather than evidence that the manifest is invalid.

The wrapper writes:
- `.stet/skill-loops/<name>/stet.change.yaml` with a single `skill_diff` treatment
- `stet.search_space.yaml` with treatments as the only mutable lever
- `stet.suite.yaml` and a replay dataset under `dataset/`

In v1, `--task-source replay` is the only executable source. `scenarios` and
`hybrid` are accepted by the parser but rejected at launch. Relative `--out`
paths are repo-relative, so `.stet/skill-loops/planner` lands under `--repo`
even when the agent runs from another working directory. The wrapper accepts an
absolute `--skill` path under the repo, but the suite-backed rules runtime sees
the logical repo path such as `.agents/skills/planner/SKILL.md`; that preserves
repo-managed skill staging and `.agents/skills` over `.claude/skills`
precedence.

Default graders are the normal coding-quality trio plus the bundled
`skill_workbench` pack:
- `equivalence`
- `code_review`
- `footprint_risk`
- `skill_routing`
- `skill_actionability`
- `skill_specificity`
- `skill_command_exactness`
- `skill_tool_selection`
- `skill_regression_risk`

Preflight before launching a skill compare:
- Verify whether the baseline ref contains the skill file; if not, this is a
  new-skill A/B, not a normal revision loop.
- Decide whether repo tests are decision signal. If not, avoid `tests_gated`
  custom rubrics and prefer `quality_only`/existing-details quality-only
  evidence before launching fresh Harbor work.
- Check `.agents/skills` and `.claude/skills` precedence, and watch for symlinked
  skills roots that point outside the repo.
- Inspect `--plan` output for arms, task count, grader IDs, and whether the
  wrapper will build a fresh replay dataset. If the repo already has a reusable
  dataset but lacks `.stet/stet.harness.yaml`, use a hand-authored
  manifest-backed `stet eval rules` flow against that dataset instead of forcing
  the wrapper.
- After a `START stet-eval-rules` line or CLI timeout, do not relaunch blindly.
  Use `stet eval status --change-manifest <stet.change.yaml> --json` or inspect
  the printed log/output root.

After the report materializes, read `evidence.skill_loop_path` and the linked
`skill_loop.v1.json`. It persists the loop goal, task source, skill path, cycle,
baseline/latest/best scores, weakest skill dimension, diagnosis, recommendation,
and next recommended change. Re-running `stet eval report --change-manifest`
over unchanged evidence is a read path: it must not advance the loop cycle.

For harness-bundle guards, keep the public/private boundary straight:
- `stet.harness/v1` is still the minimal public input manifest.
- The richer executed evidence lives below that boundary as `harness_surface` inside `rules_runtime.v1.json`, `stet eval report --change-manifest --json`, and `release.v1.json`. Harness-bundle runs use `kind: harness_bundle`; ordinary `agents_md` / `claude_md` runs use `kind: instruction_surface` unless the suite uses the repo default `.stet/stet.harness.yaml` or supplies `eval.harness`, which records `kind: runtime_harness`.
- If the rules launch also declares `change.rules.search_space: ./stet.search_space.yaml`, the public `stet.search_space/v1` manifest stays requested-contract only while runtime and rules reports project the executed `search_space` object plus `search_space_path` and `search_space_digest` with `source=requested_manifest`. Without that manifest, rules runtime still emits `search_space` with `source=runtime_default` so the effective bounded context is always present. `release.v1.json` carries the same nested `search_space` object and tracks the digest under freshness.
- `manifest resolve` does not emit `harness_surface`, `search_space`, staged manifest paths, or other runtime-only provenance.

## Receipt

```text
STET :: RULES REPORT

answer      safe
confidence  medium
phase       report
compare     candidate vs baseline
sample      32 tasks
delta       pass +1pp  equiv +5pp  cost -8%
driver      candidate improves equivalence and cost without failing guardrails
evidence    .stet/rules/stet.change.yaml
why         Promote is next because this is already the formal rollout
            decision surface, and promotion persists that state.

next        > [p] promote   record this decision as the current release state
then        [i] inspect     review deeper evidence before rollout mutation
then        [s] stop        keep the verdict without changing rollout state
```

Flow-specific action:
- `[p] promote`: `stet promote --change-manifest .stet/rules/stet.change.yaml --reason "..."`
- `[P] promote override`: `stet promote --change-manifest .stet/rules/stet.change.yaml --reason "..." --allow-inspect` when trust remains `inspect` and the operator is intentionally overriding the gate
- `[c] resume compare`: `stet eval rules resume --change-manifest .stet/rules/stet.change.yaml --json` when the persisted rules runtime exists but the canonical Trial Result is incomplete; use this for OOM/rate-limit interruptions before deleting the compare root, because resume reruns only missing/retryable arm tasks and can replay unchanged AGENTS.md/CLAUDE.md overlays from the change manifest
- `[g] retry graders`: use the `repair-ai-coverage` or `regrade-graders` command emitted by report/status; add `--parse-retries N` for saved grader prompts that failed JSON/schema parsing
- `[r] restart`: `stet eval rules --change-manifest .stet/rules/stet.change.yaml --suite-manifest .stet/rules/stet.suite.yaml --restart` only when the operator intentionally discards existing rules evidence for that change manifest

## Running Rules Check-In

When the rules flow is still running, use the same running/check-in contract as
plain `stet eval status`, but include the manifest path and current phase.

## A/B Testing AGENTS.md or CLAUDE.md

The rules flow is the preferred path for A/B testing AGENTS.md or CLAUDE.md.
It provides full provenance, release lifecycle integration, and writes the
treatment content directly to the container filesystem so the agent reads the
correct version from disk at runtime.

If the work is an iterative wording search, run cheap probes only to discard
obviously bad drafts. As soon as one draft becomes the current best candidate,
switch back to this rules flow before reporting that the draft is better or
ready for rollout.

### Change manifest

```yaml
version: 1
schema: stet.change/v1
name: test-agents-md-update
change:
  kind: rules
  rules:
    treatments:
      - kind: agents_md    # or claude_md
```

Context defaults: baseline reads from the default git branch (committed
version), candidate reads from the working tree (uncommitted edits). Override
with explicit `context.baseline` / `context.candidate` blocks if needed.

### Suite manifest

```yaml
version: 1
schema: stet.suite/v1
repo: .
selection:
  mode: rev_range
  rev_range: main~5..main
  task_ids:            # optional targeted rerun slice
    - flux-pr-1234
    - flux-pr-5678
eval:
  dataset: ./dataset
  baseline_model: model:sonnet 4.6
  candidate_model: model:sonnet 4.6
```

Use the same model for both arms when testing instructions, not the model.
Model fields are selectors, so use `model:<name or alias>` rather than a raw
model string.

When Harbor needs runtime settings such as larger pod memory, put them in the
repo's `.stet/stet.harness.yaml`; suite-backed rules runs apply that canonical
manifest automatically. Use `eval.harness` when the suite should point at a
different harness manifest:

```yaml
eval:
  dataset: ./dataset
  baseline_model: model:sonnet 4.6
  candidate_model: model:sonnet 4.6
  harness: .stet/high-memory.harness.yaml
```

Rules reports include each compare arm's effective runner settings when Stet
has them. If a Claude Code compare emits
`harbor_claude_code_concurrent_setup_cache_skew`, treat setup-only arm failures
as infrastructure risk first: Harbor `--force-build` still reuses Docker
layers, so the candidate arm may start installer-heavy containers more
synchronously than the baseline. Lower `--harbor-concurrency` to `2` and use
`runner.harbor_args` memory overrides before rerunning.

This applies the same runner config to both arms. It is runtime config, not the
candidate treatment. Use `change.rules.harness` only with a `harness_bundle`
treatment when the harness itself is the thing being evaluated. Do not add
`runner:` to `.stet/stet.yaml`.

When you already froze the baseline evidence with `stet baseline freeze`, replace
`baseline_model` with the benchmark baseline reference:

```yaml
eval:
  dataset: ./dataset
  baseline: .stet/baselines/my-capability.json
  candidate_model: model:sonnet 4.6
```

`eval.baseline` is mutually exclusive with `eval.baseline_model`. In this mode
`stet eval rules` materializes the frozen benchmark baseline, runs only the
candidate arm fresh, applies candidate-side treatments and overlays, records
`frozen_baseline` provenance, and skips baseline phases.

### Run

```bash
# Edit AGENTS.md or CLAUDE.md (don't commit yet)
stet eval rules \
  --change-manifest .stet/rules/stet.change.yaml \
  --suite-manifest .stet/rules/stet.suite.yaml
stet eval status --change-manifest .stet/rules/stet.change.yaml
stet eval report --change-manifest .stet/rules/stet.change.yaml --json
```

CLI `--baseline .stet/baselines/my-capability.json` may override the suite
baseline and takes precedence over `eval.baseline`, but it cannot be combined
with `--baseline-model`.

### How file overlays work

For `agents_md` and `claude_md` treatments, Stet stages file overlays outside
`/app`, installs them into the Harbor workspace, and avoids Jinja2 prompt
injection. For `skill_diff` treatments under `.agents/skills/...` or
`.claude/skills/...`, Stet stages the baseline/candidate content through the
repo-managed skills filesystem envelope so the agent sees a normal skill file.
`docs_glob` remains prompt-template context for now because filesystem staging
would need explicit add/delete semantics when glob match sets differ by arm.

The same file overlay mechanism applies across all entry points:
- `stet eval rules` (manifest-backed)
- `stet eval config-diff` (when the file is AGENTS.md or CLAUDE.md)
- `stet eval compare --baseline-file/--candidate-file` (when `--logical-path`
  is AGENTS.md or CLAUDE.md)

Symlinks (e.g., `AGENTS.md -> CLAUDE.md`) are followed transparently during
baseline/ref and working-tree resolution. Harbor stages overlay content outside
`/app`, then installs it through the existing symlink target when the destination
is a symlink, so the agent sees `AGENTS.md` as a symlink rather than a regular
file copy. The installed overlay is committed into the task image's treatment
baseline, so captured agent patches should contain only the agent's work, not
the treatment overlay itself.

## Decision Semantics

Rules receipts should always explain:
- what happened
- why the result is `safe`, `not safe`, or `inconclusive`
- what the next keyed action does to rollout state
