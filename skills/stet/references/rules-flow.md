# Rules Flow

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
manifest resolve ──► eval rules ──► status ──► report
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
stet manifest resolve --change-manifest stet.change.yaml
stet eval rules --change-manifest stet.change.yaml --suite-manifest stet.suite.yaml
stet eval status --change-manifest stet.change.yaml --json
stet eval rules resume --change-manifest stet.change.yaml --json
stet eval report --change-manifest stet.change.yaml --json
```

Roles:
- `manifest resolve`: inspect normalized inputs before launch
- `eval rules`: launch the bounded rules-backed run
- `eval status`: explain the current phase or health
- `eval rules resume`: recover an incomplete rules compare from existing arm artifacts
- `eval report`: read the finished rollout decision

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
  --test "go test ./..." \
  --json

stet eval status --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
stet eval report --change-manifest .stet/skill-loops/planner/stet.change.yaml --json
```

The wrapper writes:
- `stet.change.yaml` with a single `skill_diff` treatment
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

After the report materializes, read `evidence.skill_loop_path` and the linked
`skill_loop.v1.json`. It persists the loop goal, task source, skill path, cycle,
baseline/latest/best scores, weakest skill dimension, diagnosis, recommendation,
and next recommended change. Re-running `stet eval report --change-manifest`
over unchanged evidence is a read path: it must not advance the loop cycle.

For harness-bundle guards, keep the public/private boundary straight:
- `stet.harness/v1` is still the minimal public input manifest.
- The richer executed evidence lives below that boundary as `harness_surface` inside `rules_runtime.v1.json`, `stet eval report --change-manifest --json`, and `release.v1.json`. Harness-bundle runs use `kind: harness_bundle`; ordinary `agents_md` / `claude_md` runs use `kind: instruction_surface`.
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
evidence    stet.change.yaml
why         Promote is next because this is already the formal rollout
            decision surface, and promotion persists that state.

next        > [p] promote   record this decision as the current release state
then        [i] inspect     review deeper evidence before rollout mutation
then        [s] stop        keep the verdict without changing rollout state
```

Flow-specific action:
- `[p] promote`: `stet promote --change-manifest stet.change.yaml --reason "..."`
- `[P] promote override`: `stet promote --change-manifest stet.change.yaml --reason "..." --allow-inspect` when trust remains `inspect` and the operator is intentionally overriding the gate
- `[c] resume compare`: `stet eval rules resume --change-manifest stet.change.yaml --json` when the runtime has existing compare arms but the canonical Trial Result is incomplete

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
eval:
  dataset: ./dataset
  baseline_model: claude-sonnet-4-20250514
  candidate_model: claude-sonnet-4-20250514
```

Use the same model for both arms when testing instructions, not the model.

When you already froze the baseline evidence with `stet baseline freeze`, replace
`baseline_model` with the benchmark baseline reference:

```yaml
eval:
  dataset: ./dataset
  baseline: .stet/baselines/my-capability.json
  candidate_model: claude-sonnet-4-20250514
```

`eval.baseline` is mutually exclusive with `eval.baseline_model`. In this mode
`stet eval rules` materializes the frozen benchmark baseline, runs only the
candidate arm fresh, applies candidate-side treatments and overlays, records
`frozen_baseline` provenance, and skips baseline phases.

### Run

```bash
# Edit AGENTS.md or CLAUDE.md (don't commit yet)
stet eval rules \
  --change-manifest stet.change.yaml \
  --suite-manifest stet.suite.yaml
stet eval status --change-manifest stet.change.yaml
stet eval report --change-manifest stet.change.yaml --json
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
