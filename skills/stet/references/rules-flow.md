# Rules Flow

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
manifest resolve ──► eval rules plan ──► eval rules ──► status ──► report
                                                        │          │
                                                    [w] wait   [p] promote  [i] inspect  [s] stop
                                                        │
                                                    [c] repair compare
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
stet eval rules repair --change-manifest .stet/rules/stet.change.yaml --json
stet eval report --change-manifest .stet/rules/stet.change.yaml --json
```

Roles:
- `manifest resolve`: inspect normalized inputs before launch. Prints the canonical resolved change manifest as YAML (or JSON with `--json`); injected defaults (e.g. `context.baseline.source`, `context.candidate.source`, `policy.version`, `treatments[*].path`) are inlined silently — there is no separate validation verdict. On a malformed manifest, `manifest resolve` exits non-zero; without `--json` it emits a plain-text stderr line, and with `--json` it emits a structured `{"error": {"code", "message", "field"}}` envelope on stdout. A non-zero exit is the validation contract — treat it as "malformed manifest" and read `error.code` / `error.field` (or the stderr line) for the field-precise reason.
- `eval rules plan`: preflight tasks, arms, graders, frozen-baseline reuse, cost confidence, missing pricing/cost data, and cheaper alternatives without writing runtime artifacts. It does not launch the charged compare, but it is not free: plan runs the Harbor `oracle`-agent gold-replay validation containers to populate `replay_validity` and runs the LLM-grader preflight, so under contention it routinely takes 8–10+ minutes. A future `--quick-plan` that skips replay validation does not exist yet; when an operator needs a sub-minute readiness check, reach for `stet manifest resolve` instead. The next command, `stet eval rules` without `--plan`, is the charged launch. The plan output's `task_selection_adequacy.verdict` is informational; values such as `insufficient_history` describe historical sample size for confidence calibration and do not block launch.
- `eval rules`: launch the bounded rules-backed run
- `eval status`: explain the current phase or health
- `eval rules repair`: recover an incomplete rules compare from the persisted runtime; when the surface is replayable, it can resume a baseline-phase compare or rerun a missing/partial candidate arm while preserving completed evidence, then repair/regrade missing coverage. `eval rules resume` remains accepted for compatibility. Pass `--parse-retries N` to forward grader JSON parse-repair attempts during regrade recovery. Pass `--report-mode separate_axes|strict_publishable_pass` to pin the reporting mode when the baseline and candidate arms were produced by Stet binaries whose default drifted; baseline mode is used automatically otherwise.
- `eval report`: read the finished rollout decision

`eval status --change-manifest --json` reports three axes. `rules_runtime`
means metadata is `resolved`, `unresolved`, or `stale`; `arm_evidence` means
compare arm artifacts are `none`, `partial`, `running`, `complete`, or `failed`;
`compare_decision` means the decision is `reportable`, `missing_experiment`,
`inconsistent`, or `blocked_until_report`. If arm evidence exists but
`experiment.json` is missing, the decision remains inspect-only. Repair with
`stet eval rules repair --change-manifest ... --json` when the launch exited or
stalled; use `--restart` only to discard evidence.

The envelope also carries a top-level `activity_state` of `running`, `stalled`,
or `exited` so a polled receipt can disambiguate "no evidence yet because still
running" from "no evidence yet because the run died." `activity_state` is
authoritative: an embedded `report.execution.status` of `inspect` is provisional
unless `activity_state == "exited"`. While `activity_state` is `running` or
`stalled`, treat any embedded `report` as in-flight scaffolding rather than a
terminal verdict, and re-poll instead of acting on it. Note that this top-level
field is distinct from the per-arm `run_status.activity_state` (values
`active`/`waiting_on_*`/`no_progress`), which describes one resolved arm's
internal phase rather than the launcher process as a whole.

When the agent harness records an exception on any per-task run (e.g. codex
crashing during `agent_setup`), `eval status` surfaces the most recent failure
in a top-level `last_error` field with `type`, `message`, `agent`, `task_id`,
`phase`, and `occurred_at`. The text renderer prints a `Last error:` line. Use
this to tell whether the agent itself or the Stet wiring is broken before
chasing downstream grader errors. The field is omitted on happy-path receipts.

Pre-arm launcher failures (baseline/candidate context resolution, skills-root
staging, harness resolve, frozen-baseline load, rev-range buildability) are
surfaced separately as a top-level `launch_error` field on the
`eval_rules_runtime.v1.json` artifact, on `eval status --change-manifest --json`
when launch is blocked, and on `eval report --change-manifest --json`
(where `decision.reasons` and `decision.next_action` are also overridden so
the receipt names the launch failure). The skill wrapper preflight
(`eval rules skill --plan --json`) emits the same struct via the
`evalRulesSkillPreflightFailureV1` envelope on stdout. The shape is
`{phase, message, target, code, remediation, occurred_at}`; `phase` is one of
`resolve_baseline_context`, `resolve_candidate_context`, `stage_skills_root`,
`harness_resolve`, `frozen_baseline_load`, or `rev_range_buildability`.
`launch_error` and `last_error` can coexist when the launcher fails after a
partial runtime already saw per-task crashes. Read `launch_error` first when
`stet eval rules` exits before any per-task arm runs; the per-task agent
crash path is `last_error`.

The `code` field disambiguates structurally similar phases. Within
`resolve_baseline_context` / `resolve_candidate_context` you may see:

- `code=context_path_unresolved` — the requested AGENTS.md / CLAUDE.md /
  docs path does not exist at the configured baseline ref. Remediation
  points at the manifest path or the `context.baseline` pin.
- `code=default_branch_unresolved` — the repo's default branch could not
  be resolved (origin/HEAD not set, HEAD detached, or the same-named
  remote ref missing). `target=default_branch`. Remediation names the
  git-config fix (`git remote set-head origin -a`) or the
  `context.baseline.source` pin. Common in worktrees and freshly-cloned
  repos where origin/HEAD has not been set.
- `code=repo_not_a_git_repository` — the configured `repo:` path does
  not point at a git working tree. `target=repo`. Almost always a
  manifest-authoring bug: relative `repo:` values in `stet.suite.yaml`
  are resolved against the **`.stet` ancestor's parent (the repo root)**,
  not against the suite file's own directory. For a suite that lives at
  `<repo>/.stet/<somewhere>/stet.suite.yaml`, the canonical form is
  `repo: .`; writing `repo: ../../..` over-traverses out of the repo.
  Remediation points at the `repo:` field of the suite manifest.

`--ai-cmd` is a launch-only override for `stet eval rules`; use an absolute
script path when launching from scratch directories. `eval.grader_ai_cmd` and
`eval.grader_ai_model_id` in `stet.suite.yaml` are required whenever the run
will bundle LLM-backed graders (see Default Quality Graders below) and serve
double duty as the independent evaluator for validation graders so the model
under test does not grade its own work. `--grader-ai-cmd` plus
`--grader-ai-model-id` are equivalent CLI overrides; both `plan` and the
charged launch refuse pre-flight when neither the suite nor the CLI supplies
them and the resolved grader set includes any LLM-backed grader.

To iterate on a high-signal slice from an existing dataset, pass repeatable
`--task-id <id>` to `eval rules plan` and `eval rules`, or put the stable slice
in the suite manifest as `selection.task_ids`. Task IDs must match ready task
directories in `eval.dataset`.

Put stable variance controls in the suite manifest under `eval:`:
`task_order_seed`, `workers`, `model_workers`, `harbor_concurrency`, and
`harness_cli_cache`. `stet eval rules` accepts matching CLI flags for temporary
overrides; CLI values take precedence over suite YAML. `stet eval rules skill`
also accepts `--task-order-seed` and writes it into its synthesized iteration
suite; omit the flag for fresh per-run randomness.

`stet eval rules` is non-destructive by default when a matching rules runtime
already exists. It reuses completed evidence, auto-resumes candidate-phase
partial evidence when Stet can prove the replay is safe, and refuses to discard
partial arm evidence. Use `stet eval status --change-manifest ...` before any
recovery decision, then `stet eval rules repair --change-manifest ... --json`
when the active process has exited or status is stalled. Use `--restart` only
when intentionally discarding existing evidence and starting over.

Fresh rules runs use the same bounded preflight policy as `stet eval run`: one
representative smoke pre-pass before canonical work, not one smoke run per arm.
Candidate arms are preferred over baseline arms for that single smoke. Successful
smoke artifacts are seeded into the canonical root so smoked tasks count toward
the full run.

## Replay-Invalid Smoke

If smoke fails before `compare/experiment.json` with
`no_gold_pass_commands`, `all_commands_ignored_gold_failure_mode_unset`, or
`tests_unknown_all_commands_ignored_gold_failure_mode_unset`, the selected
slice is not gold-valid evidence yet. Do not treat that as model quality, a
rollout decision, or proof that current-checkout tests are broken.

First diagnose the verifier failure. Read `stet eval status
--change-manifest ... --json`, `stet eval report --change-manifest ... --json`,
the failed arm root, and per-task `validation.json` / `task_detail.json`
artifacts. Identify the task IDs, verifier commands, `gold_outcome`,
`gold_failure_mode`, `partial_score_reason`, and stdout/stderr hints. Explain
the likely cause before choosing an action: for example a path-sensitive test,
stale command, missing selector, container-only failure, archived dependency
drift, too-narrow slice, bad generated task, or another concrete replay issue.

Choose a bounded next action from that diagnosis. It may be a different task
slice, adjusted task selection, an already-known gold-valid test command, or an
inspect-only stop when no safe recovery is justified. Relaunch only after the
evidence input changes, or after you can explain why the same input is now
plausibly gold-valid. STET-340 tracks a product-supported gold-replay preflight;
until that exists, preserve inspect-only caveats and avoid rollout claims until
a gold-valid compare completes.

## Default Quality Graders

For non-skill treatments (AGENTS.md, CLAUDE.md, model_update, harness_bundle,
docs_glob), `eval rules` automatically includes the repo's quality graders from
`stet.yaml` `quality:` config, or the recommended default (`discipline` bundle +
`intentionality`) when no quality config exists. This ensures decision-grade
evidence on the first run without requiring post-hoc `regrade-graders`.

The rules-default profile bundles **7 graders total**: the coding-quality trio
(`equivalence`, `code_review`, `footprint_risk`) plus 4 quality graders — the
`discipline` bundle (`clarity`, `simplicity`, `coherence`) and `intentionality`.
If the repo pins a `quality:` profile in `.stet/stet.yaml` (e.g.,
`craft+discipline`), the rules-default seven are REPLACED by the pinned set
(typically 10–11 graders, adding `robustness`, `instruction_adherence`,
`scope_discipline`, `diff_minimality`, and the craft graders) — see
`quality_profile.source` in plan output to confirm which path resolved.
This is distinct from the **leaderboard** profile used for model-comparison
runs, which bundles the full **8 craft + discipline graders** (`clarity`,
`simplicity`, `coherence`, `intentionality`, `robustness`,
`instruction_adherence`, `scope_discipline`, `diff_minimality`). Operators
moving between the rules and leaderboard flows should expect that difference;
neither profile is a strict superset of the other and they grade different
surfaces.

In plan and runtime output, `graders.grader_profile.source` records how the
profile was chosen: `derived` means it was inferred from defaults (the
recommended bundle plus any `stet.yaml` `quality:` config) because the change
manifest did not pin a profile, and `explicit` means `change.rules.grader_profile`
in the manifest set the graders, evaluator model, or command. Treat `derived`
as the normal first-run posture; `explicit` is the steady state once a repo
pins its grader contract. A third value, `legacy`, may appear on older
manifests that predate the explicit `grader_profile` contract — treat it as
"profile carried forward from a pre-contract manifest" and migrate to
`explicit` when the repo refreshes its rules manifests.

The default quality bundle is LLM-backed (the `discipline` bundle covers
`instruction_adherence`, `scope_discipline`, `diff_minimality`, and the
recommended default adds `intentionality` alongside it), so
`eval.grader_ai_cmd` and `eval.grader_ai_model_id` must be set in
`stet.suite.yaml` (or supplied as `--grader-ai-cmd` / `--grader-ai-model-id`)
for any non-skill treatment that auto-bundles them.
`stet eval rules plan` and `stet eval rules` both refuse pre-flight when those
fields are missing and any LLM-backed grader is bundled. Worked stanza:

    eval:
      grader_ai_cmd: "claude --output-format json --print"
      grader_ai_model_id: claude-sonnet-4-6

Pick an evaluator distinct from the candidate model so the grader is not
grading its own work. Pass `--no-quality` (or set `no_quality: true` on
`eval`) when you intentionally want to drop the auto-bundled craft and
discipline graders. Note that validation-backed runs still bundle
`equivalence` and `code_review` (both LLM-backed), so `--no-quality` alone
does not bypass the preflight; supplying the evaluator stanza is the
straightforward path.

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
`change.rules.grader_profile.graders`; legacy `change.rules.graders` still
works. `stet eval rules` does not accept `--grader` launch flags. For
`stet eval rules skill`, repeated `--grader` flags are wrapper inputs and
replace the default grader set.

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
stet eval rules skill --plan \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --grader-ai-cmd "claude --output-format json --print" \
  --grader-ai-model-id claude-sonnet-4-6 \
  --json

stet eval rules skill \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --test "go test ./..." \
  --grader-ai-cmd "claude --output-format json --print" \
  --grader-ai-model-id claude-sonnet-4-6 \
  --json

stet eval status --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
stet eval report --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
```

Use the `--plan` form before launch when the operator needs a budget decision;
it does not write the wrapper bundle, build the replay dataset, or launch
`eval rules`. `--plan` runs a buildability preflight against the resolved
rev-range and surfaces it as `tasks.rev_range` in the JSON output; if 0 PRs
match, it exits non-zero with an error naming the rev-range and the
fetched / not-in-range / missing-merge counts so the operator can pass
`--rev-range` to widen the slice before charging the launch.
For wrapper runs, put any `--ai-cmd` on the non-plan launch; the wrapper
forwards it to delegated `stet eval rules`.
If `stet eval rules plan` is blocked by commercial entitlement, treat that as an
access/preflight limitation rather than evidence that the manifest is invalid.

Replay-task discovery defaults to rev-range `main~25..main` against `--repo`.
On a checkout whose recent history is squash-merged, rebased, or otherwise not
standard merge-commits-into-main (e.g. a fresh worktree branched off a recent
tag), that default can yield 0 buildable PRs. Override with `--rev-range` to
widen or shift the slice — the wrapper passes the override through to the
generated `stet.suite.yaml` so the delegated `stet eval rules` consumes the
same range:

```bash
stet eval rules skill \
  --skill .agents/skills/planner/SKILL.md \
  --repo . \
  --model claude-sonnet-4-20250514 \
  --goal "improve planning specificity without increasing scope risk" \
  --out .stet/skill-loops/planner \
  --tasks 12 \
  --rev-range main~75..main \
  --plan \
  --json
```

Rule of thumb: pick a range whose merge-commit count is at least `--tasks`
plus headroom for PRs that resolve to skipped/non-buildable. The buildability
preflight samples up to 50 PRs from the resolved rev-range and refuses the
launch (and the bundle write) when **none** of the sampled PRs are
buildable; on that failure no half-set-up runtime is committed. The
preflight does **not** protect against the narrower failure where buildable
PRs exist in the rev-range but are outside the dataset build's `--tasks`
fetch window — see the next paragraph and the empty-dataset note further
below.

`--tasks N` is currently both the task target *and* the upper bound on how
many merged PRs the dataset build fetches from the remote. The buildability
preflight applies its own minimum-fetch floor (50) so a small `--tasks` value
does not silently mask a buildable range, but the downstream dataset build
honors `--tasks` as a hard cap. If the most recent N merged PRs in your
rev-range are not buildable (e.g. the most recent merge resolved to a
documentation-only commit outside `main~N..main`), bump `--tasks` along with
`--rev-range` so the fetch budget reaches the buildable PRs. An eventual
release will plumb fetch and task-count separately so `--tasks 1` can fetch
many PRs and keep one — until then, treat `--tasks` as the fetch budget too.

The wrapper writes:
- `.stet/skill-loops/<name>/stet.change.yaml` with a single `skill_diff` treatment
- `stet.search_space.yaml` with treatments as the only mutable lever
- `stet.suite.yaml` and a replay dataset under `dataset/`

Two things to know about that bundle:
- `stet.change.yaml` records the `skill_workbench` grader pack as a single
  bundle id. `--plan` and the runtime expand that bundle into the six
  `skill_*` dimensions listed below at launch time; the bundle id in the
  manifest and the six dimensions in plan output are the same coverage,
  not a discrepancy.
- The `dataset/` directory is allowed to be empty when the **dataset
  build** (post-preflight) yields zero buildable replay tasks. This is
  distinct from the preflight refusal above: the preflight samples 50
  PRs and proves the rev-range *can* produce at least one buildable
  task, but the dataset build then honors `--tasks` as a hard fetch cap
  and may not reach those PRs (e.g. `--tasks 1` against a rev-range
  whose first sampled PR is doc-only or out-of-range). When that
  happens the wrapper writes the bundle (change/search-space/suite
  manifests + `dataset/build-summary.json` with `ready: 0`) and the
  subsequent `eval rules` exits non-zero on `no ready tasks`. Read
  `build-summary.json` before retrying with a larger `--tasks` and/or a
  tighter `--rev-range`. (Operator-facing rev-range / task slice
  overrides for the wrapper itself land separately.)

Re-running the wrapper against a populated `--out` directory:
- If `dataset/build-summary.json` is present (clean prior build), the wrapper
  reuses the dataset and proceeds directly to `stet eval rules`. This is the
  recovery path after an `eval rules` failure that left the dataset intact.
- If task directories exist but no `build-summary.json` (partial build), the
  wrapper exits non-zero with a remediation pointing at `--restart` or a fresh
  `--out` dir; it does not silently re-enter the build.
- `--restart` discards `<out>/dataset` before rebuilding **and** forwards
  `--restart` to the delegated `stet eval rules`, which clears prior rules
  evidence under the same `--out`. Treat this as a destructive reset of both
  the replay dataset and any compare evidence; if you only want to rebuild
  the dataset and preserve evidence from a parallel run, use a fresh `--out`
  directory instead.
- If the underlying suite build fails with `build completed with N errors`, the
  wrapper surfaces that error wrapped with the failing step (`build replay
  dataset at <path>`) and the same `--restart` remediation; it never proceeds
  to launch `eval rules` on a failed build.

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

All wrapper default graders except `footprint_risk` are LLM-backed (this
includes `equivalence`, `code_review`, and the entire `skill_workbench` pack),
so the same `eval.grader_ai_cmd` / `eval.grader_ai_model_id` requirement
applies. The wrapper writes a suite manifest from the `--model` flag; supply
`--grader-ai-cmd` / `--grader-ai-model-id` on the wrapper invocation
(both must be set together) and the wrapper writes them into the generated
suite stanza and forwards them to the delegated `stet eval rules` invocation.
`--no-quality` drops only the auto-bundled craft/discipline graders; the
wrapper's default bundle still includes `equivalence`, `code_review`, and
`skill_workbench` — all LLM-backed — so `--no-quality` alone does not bypass
the evaluator preflight. To run without an evaluator you must additionally
override the bundle, e.g. `--grader footprint_risk`.

Preflight before launching a skill compare:
- Verify whether the baseline ref contains the skill file; if not, this is a
  new-skill A/B, not a normal revision loop.
- Decide whether repo tests are decision signal. If not, avoid `tests_gated`
  custom rubrics and prefer `quality_only`/existing-details quality-only
  evidence before launching fresh Harbor work.
- Check `.agents/skills` and `.claude/skills` precedence. The wrapper refuses
  **any** symlink under `.agents/skills/` or `.claude/skills/` (even
  intra-repo). Resolve symlinks before launch, or move the affected skill out
  of the staged root.
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
- Claude Code hooks are represented as Claude settings, not as a Stet hook DSL. Put the customer-authored project settings file at `.claude/settings.json` and declare every repo-local hook script or hook directory in the harness manifest:
  ```yaml
  claude_code:
    settings_path: .claude/settings.json
    hook_files:
      - .claude/hooks/
  ```
  Stet resolves those files from the same baseline/candidate source as the harness manifest, rejects unsafe paths/symlinks/URLs and undeclared repo-local command files, stages them for `agent: claude-code`, and hashes the settings plus hook files and executable modes into `harness_surface`.
- The richer executed evidence lives below that boundary as `harness_surface` inside `rules_runtime.v1.json`, `stet eval report --change-manifest --json`, and `release.v1.json`. Harness-bundle runs use `kind: harness_bundle`; ordinary `agents_md` / `claude_md` runs use `kind: instruction_surface` unless the suite uses the repo default `.stet/stet.harness.yaml` or supplies `eval.harness`, which records `kind: runtime_harness`.
- Hook execution observability is currently conservative: `runner_runtime.v1.json` records the configured hook count, settings digest, hook file digests, executable modes, `execution_status: unobserved`, `failure_category: harness_hook_failure`, zero observed failures/timeouts unless stable telemetry is present, and `observability: session_log_only`. Do not claim hooks improved quality without a completed repo eval and a report showing both quality and runtime deltas.
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

Release warning codes carried in receipts include `default_branch_fallback`:
surfaced when the change manifest does not pin an explicit baseline source and
the rules launcher fell back to the repo's default branch. It is informational,
not blocking; pin `context.baseline.source` explicitly in the change manifest
to silence it.

Flow-specific action:
- `[p] promote`: `stet promote --change-manifest .stet/rules/stet.change.yaml --reason "..."`
- `[P] promote override`: `stet promote --change-manifest .stet/rules/stet.change.yaml --reason "..." --allow-inspect` when trust remains `inspect` and the operator is intentionally overriding the gate
- `[c] repair compare`: `stet eval rules repair --change-manifest .stet/rules/stet.change.yaml --json` when the persisted rules runtime exists but the canonical Trial Result is incomplete; use this for OOM/rate-limit interruptions before deleting the compare root, because repair reruns only missing/retryable arm tasks and can replay unchanged AGENTS.md/CLAUDE.md overlays from the change manifest. `resume` remains accepted as a compatibility alias. Repair cannot recover a terminal arm failure: when status/report emit a `repair` block with code `RULES_COMPARE_ARM_FAILED` or `RULES_ACTIVE_ARM_FAILED`, inspect the failed arm root, address the harness failure (auth, config, missing bundle, etc.), then relaunch instead of repairing
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
  grader_ai_cmd: "claude --output-format json --print"
  grader_ai_model_id: claude-sonnet-4-6
```

Use the same model for both arms when testing instructions, not the model.
Model fields are selectors, so use `model:<name or alias>` rather than a raw
model string.

Suite manifest paths: `eval.dataset:` (and other path fields) is resolved
relative to the suite manifest's own directory; the resolver walks up to the
nearest `.stet` ancestor to anchor relative paths. The schema does not support
`${repo}` interpolation. For fixtures, leave the suite manifest in place
rather than copying it, and reference it via
`--suite-manifest /absolute/path/to/fixture/stet.suite.yaml`; copying detaches
the manifest from its repo-anchored baseDir and breaks relative paths.

Selection precedence: when `eval.dataset` points at a pre-built dataset, plan
and `eval rules` take task IDs from that dataset and `selection.mode: rev_range`
(plus `selection.rev_range`) is harmlessly ignored. `selection.mode: rev_range`
only takes effect when no `eval.dataset` is set, in which case Stet uses the
rev range to discover tasks fresh. To narrow a pre-built dataset to a specific
slice, use `selection.task_ids` (or repeated `--task-id` on plan/launch);
changing the rev range in a manifest that also sets `eval.dataset` will not
shift which tasks run.

`eval.grader_ai_cmd` and `eval.grader_ai_model_id` are required for AGENTS.md /
CLAUDE.md (and any other non-skill) rollouts: rules launches auto-bundle the
craft + discipline LLM graders, and `stet eval rules plan` and the launch
refuse pre-flight if those fields are missing. Pick a different model from the candidate so the grader is
not grading its own work. Pass `--no-quality` (or set `no_quality: true` on
`eval`) only when you intentionally want to drop the auto-bundled graders.

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

When evaluating Claude Code hooks, keep the hook files repo-relative and
customer-authored under `.claude/`. Stet stages `.claude/settings.json` and the
declared `hook_files` for Claude Code and invalidates cached evidence when any
declared hook file digest or executable mode changes. Hooks that intentionally
transform patches, validation inputs, or scoring artifacts are outside this
first-cut contract.

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

#### Baseline freshness gate (STET-375)

A frozen benchmark baseline is a snapshot of grader scores against a specific
harness surface (AGENTS.md, CLAUDE.md, skills bundle). When the surrounding
harness changes between freeze time and replay time, the comparison is
measuring harness drift rather than the candidate change. To make that
visible:

- `stet baseline freeze` records the baseline-arm harness surface digest on
  the baseline via `--harness-surface-digest` / `--harness-surface-kind`. The
  digest lives on the rules runtime artifact that produced the run you are
  freezing. The artifact path is content-addressed (under
  `.stet/eval-rules/<hash>/rules_runtime.v1.json`), so discover it from the
  `evidence.rules_runtime_path` field of `stet eval report --json` rather
  than hand-rolling the directory layout. For example:

  ```bash
  CHANGE=.stet/rules/stet.change.yaml
  RUNTIME=$(stet eval report --change-manifest "$CHANGE" --json \
    | jq -r .evidence.rules_runtime_path)
  DIGEST=$(jq -er '.harness_surface.baseline_digest' "$RUNTIME") || {
    echo "error: $RUNTIME has no harness_surface.baseline_digest; rerun stet eval rules to produce a post-STET-375 runtime artifact before freezing" >&2
    exit 1
  }
  KIND=$(jq -er '.harness_surface.kind' "$RUNTIME")
  stet baseline freeze \
    --from "$(dirname "$RUNTIME")/compare/arms/baseline" \
    --name my-baseline \
    --harness-surface-digest "$DIGEST" \
    --harness-surface-kind   "$KIND"
  ```

  `--from` must point at the baseline arm root (`.../compare/arms/baseline`),
  not the compare root: `stet baseline freeze` resolves the benchmark baseline
  from a single arm's `manifest.json` + `reports/summary.json`. Pointing at the
  compare root would fall back to a snapshot freeze that silently drops the
  `--harness-surface-*` flags and leaves the gate at `cache_status=unknown`.

  The `jq -er` guard is load-bearing: with plain `jq -r`, a pre-STET-375
  runtime artifact (`baseline_digest: null`) yields the literal string
  `"null"`, which gets recorded as the digest and produces a nonsensical
  `stale_detected` reason on every subsequent run. `-e` makes `jq` exit
  non-zero on null so the freeze fails cleanly instead.

  Baselines frozen before this gate, or frozen without these flags, replay
  with `cache_status=unknown`.
- Each `stet eval rules` run with `--baseline` recomputes the current harness
  surface's baseline-arm digest, compares it to the recorded one, and labels
  the baseline arm's `cache_status` in `eval_report.v1.json`:
  - `hit` — digests match; frozen replay is sound
  - `stale_detected` — digests diverge; a `WARNING` is logged and a
    `Baseline cache_status` line appears in `stet eval status`
  - `unknown` — recorded or current digest unavailable
- The gate is soft: it never blocks the run. To break out of a stale-baseline
  loop, pass `--force-fresh-baseline` to `stet eval rules`; the flag ignores
  the frozen snapshot and runs the baseline arm fresh against the current
  harness surface.

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

Symlinks (e.g., `AGENTS.md -> CLAUDE.md`, or the reverse `CLAUDE.md -> AGENTS.md`
that many real repos use) are followed transparently during baseline/ref and
working-tree resolution; either direction is supported. Harbor stages overlay
content outside `/app`, then installs it through the existing symlink target
when the destination is a symlink, so the agent sees the convention file as a
symlink rather than a regular file copy. The installed overlay is committed
into the task image's treatment baseline, so captured agent patches should
contain only the agent's work, not the treatment overlay itself.

## Decision Semantics

Rules receipts should always explain:
- what happened
- why the result is `safe`, `not safe`, or `inconclusive`
- what the next keyed action does to rollout state
