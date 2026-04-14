# Rubric Authoring

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

```
design rubric ──► calibrate ──► discriminates?
                     ▲          ├─ yes ──► [p] probe (live eval)
                     │          └─ no ──► tighten anchors ──► ↺
                     └──────────────────────────────────────┘
```

Use this when writing, splitting, or calibrating custom Stet rubric graders,
especially when the user needs dimension-specific feedback on skills,
research, plans, or other non-code outputs.

## When To Use

- "Help me write a rubric for this research skill."
- "The output still is not good enough, but the current grader is too broad."
- "Which dimensions should we grade separately?"
- "This rubric is noisy. How do we calibrate it?"

Do not use this for model benchmarks or repo-file safety checks. Use the main
routing table for those.

## Reporting

```text
STET :: RUBRIC

answer      needs calibration
confidence  low
step        rubric -> calibrate
dimension   research_specificity
data        good=4 bad=2 overlap=yes
driver      weak discrimination — grader cannot separate good from bad
evidence    rubrics/research_specificity.yaml
why         Calibrate is next because the grader overlaps on good and bad
            anchors, so scores are not trustworthy yet.

next        > [c] calibrate   tighten the rubric against known anchors
then        [p] probe         run a live eval after calibration
then        [s] stop          keep the current rubric draft only
```

## Workflow

1. Define the artifact kind and reader.
2. Split quality into orthogonal dimensions.
3. Write one rubric file per dimension.
4. Calibrate each rubric before trusting it.
5. Run multi-grader probes and inspect weakest dimensions.

## Design Rules

- One rubric, one dimension.
- Describe observable evidence, not vibes.
- Write pass and fail so two reasonable graders would usually agree.
- Use `unsure` only for genuine middle cases.
- Prefer scored `0`-`4` rubrics when the user needs discrimination, not just a
  gate.

## Templates

Binary:

```yaml
id: research_specificity
rubric:
  pass: >-
    Names concrete files, functions, types, or line ranges and ties each claim
    to evidence a reader can verify.
  fail: >-
    Uses vague references or generic summaries without concrete code-level
    grounding.
  unsure: >-
    Some findings are grounded but specificity is inconsistent across the
    artifact.
```

Scored:

```yaml
id: plan_architecture_quality
rubric:
  "4": "3 genuinely different architectures with evidence-backed tradeoffs"
  "3": "3 options, but one is thinner or less evidenced"
  "2": "2 solid options plus one shallow variant"
  "1": "options differ mostly in naming or packaging"
  "0": "missing or effectively one-option thinking"
```

## Calibration

```bash
stet eval calibrate \
  --rubric rubrics/research_specificity.yaml \
  --known-good good.md \
  --known-bad bad.md \
  --artifact-kind research \
  --grader-cmd "scripts/claude_ai_cmd.sh"
```

Use anchors instead of `known-good` / `known-bad` for scored rubrics.

Flow-specific actions:
- `[c] calibrate`: `stet eval calibrate --rubric <path> ...`
- `[p] probe`: `stet eval workbench probe ... --grader <path>`

Path preservation rule:
- Treat the rubric file path as the stable operator handle. When a custom
  rubric is used in `probe`, `config-diff`, `compare`, or
  `stet runs regrade-graders`, keep the original `--grader /path/to/rubric.yaml`
  argument on follow-up commands instead of replacing it with the resolved
  grader ID.

Task-detail grader context:
- Custom task-detail graders receive bounded `task_detail.json.grader_context`
  when available: inline agent patch evidence, instruction/policy treatment
  metadata with logical paths, normalized task intent, and deterministic
  repo-fit excerpts. Write rubrics so they use this structured evidence rather
  than expecting the evaluator to grep or inspect the repo live.

## Run It

```bash
stet eval workbench probe \
  --intent artifact_quality \
  --repo . \
  --out ./stet-skill-eval \
  --baseline-artifacts-dir /path/to/baseline \
  --candidate-artifacts-dir /path/to/candidate \
  --artifact-kind research \
  --grader rubrics/research_specificity.yaml \
  --grader rubrics/research_actionability.yaml \
  --grader-cmd "scripts/claude_ai_cmd.sh"
```

Then inspect the weakest dimension:

```bash
stet eval workbench risks --grades-dir ./stet-skill-eval/graded/candidate --weakest --json
```

Artifact batch-grade directories must be flat and use filenames of the form
`<task-id>.md`; the derived task ID must be non-empty and must not traverse out
of the task output directory.

## Existing Examples

Start from checked-in rubrics instead of inventing format from scratch:

- `rubrics/research_specificity.yaml`
- `rubrics/research_completeness.yaml`
- `rubrics/research_actionability.yaml`
- `rubrics/plan_architecture_quality.yaml`
- `rubrics/plan_scope_discipline.yaml`

## Common Mistakes

- Combining specificity, completeness, and actionability in one rubric.
- Writing criteria that only say "good", "clear", or "thorough".
- Skipping calibration and then trusting noisy scores.
- Replaying a custom rubric workflow with the grader ID only instead of the
  original rubric file path.
- Using artifact graders to answer code-correctness questions.
- Reporting a rubric result without saying what the operator should do next.
