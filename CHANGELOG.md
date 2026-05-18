# Changelog

All notable changes to Stet are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and Stet
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [v0.4.1] - 2026-05-18

Prevents Harbor patch capture from retaining harness and gold artifacts as agent output. Operators get cleaner trial results: `.stet/gold.patch`, guidance files, generated directories, and lockfile-only churn no longer leak into captured agent patches, while real source edits and deletions remain visible.

### Fixed
- Prevent gold patch and other harness-generated paths from leaking into captured agent patches; rewrite legacy Harbor artifact sources to the sanitized canonical patch while preserving real source edits and deletions ([4d68d6a])

[v0.4.1]: https://github.com/benredmond/stet/releases/tag/v0.4.1
[4d68d6a]: https://github.com/benredmond/stet/commit/4d68d6a75349992f5e2743601f20b76dc1247f81

## [v0.4.0] - 2026-05-18

Hardens the correctness of cached evidence with a frozen-baseline harness-surface digest gate, adds a `stet eval rules repair` recovery command for interrupted compares, attaches paired-bootstrap confidence intervals and a headline-uncertainty envelope to compare receipts, and reports impl-vs-test-fixture patch surface composition on `footprint_risk`. The CLI gains `--grader` on `stet eval run`, deterministic `--task-order-seed` propagation through `stet eval rules` and monitor reruns, and judge-noise regrade seeding; replay-validity output surfaces typed gold-failure summaries. Adds a Claude Code hook harness surface so hook treatments are first-class compare variants, a `validation_failure.kind` subtype taxonomy that prevents setup blockers from reading as model no-patch behavior, and Linux ARM64 release assets. Returns `stet eval status` in ~2s on finalized compares, restores `--out` dataset reuse in the `stet eval rules` skill wrapper, and corrects the shipped skill docs around `decision_receipt.recommendation` and the `--grader-ai-cmd` / `--grader-ai-model-id` fallback.

### Added
- Publish Linux ARM64 (`linux/arm64`, including aarch64 hosts) CLI release assets and support them in install/update ([9866fe4])
- Accept repeatable `--grader <id|bundle|rubric.yaml>` on `stet eval run` with explicit-wins-merge over repo quality config, mirroring the flag on `stet eval compare` and `stet runs regrade-graders` ([de6c0bc])
- Add `stet eval rules repair` to reuse validation artifacts and resume an interrupted compare or rerun missing/partial arms; `stet eval rules resume` remains accepted as a compatibility alias ([c64393c])
- Plumb `--task-order-seed` through `stet eval rules` and the rules `skill` wrapper so dispatch order replays deterministically against a sorted task selection ([f3e9ee5])
- Honor suite-manifest `eval.task_order_seed` end-to-end through the `stet eval rules` compare path ([6870494])
- Persist `task_order_seed` in monitor rerun config so `stet monitor` reproduces the original dispatch order ([6e07411])
- Add a paired-bootstrap post-pass to `stet eval compare` with `--bootstrap-iterations`, `--bootstrap-seed`, `--ci-level`, and `--no-bootstrap`; receipts gain `aggregate.<metric>.uncertainty` blocks (`baseline_ci`, `candidate_ci`, `delta_ci`, `win_loss_tie`, `bootstrap`) and an `Uncertainty:` text section ([3449973])
- Carry per-metric uncertainty intervals into `decision_receipt`, including `decision_receipt.headline_uncertainty` for the headline metric's CI envelope ([f72da01])
- Report patch surface composition on `footprint_risk` results with a new `surface_breakdown` block (agent vs gold, `implementation` vs `test_fixture` sides, `test`/`fixture`/`expected_output` subkinds, and `test_fixture_added_share`); per-task summaries expose `footprint_surface_breakdown` ([5c5a181])
- Add `--seeds N` to `stet runs regrade-graders` so the operator can bound judge-noise variance during regrades ([ece1165])
- Add a durable arm identity contract so frozen-baseline reuse and arm-level evidence stay bound to a stable identifier across replays ([5f671b3])
- Print typed gold-failure summaries (category/reason plus `harbor_log` path and scrubbed excerpt) in replay-validity terminal output so it matches the JSON diagnostic ([a731873])
- Add a Claude Code hook harness surface — propagate hook-derived signals end-to-end through the rules-runtime artifact, eval-rules check-in, resume, status, runner runtime, and experiment spec so hook treatments are first-class h2h compare variants ([174a94e6])
- Add a no-patch `validation_failure.kind` subtype taxonomy (`empty_patch`, `setup`, `pre_agent`, `verifier`, `sanitized_patch`); propagate counts through h2h task summaries, reports, eval status, smoke preflight, and run validity; classify Harbor no-agent-start artifacts as setup blockers; prefer invalidating subtypes on smoke-preflight tie-breaks while preserving legacy `matrix_status` values for existing consumers ([4939dd3f])

### Changed
- Update the shipped Stet skill docs to point at `decision_receipt.recommendation` as the verdict field (mirrored by `lifecycle.decision`); `decision_receipt` has no top-level `decision` field ([d1374a76])
- Document `--grader-ai-cmd` / `--grader-ai-model-id` as the read-only fixture fallback for LLM-backed graders on `stet eval rules plan` / `launch` / `skill`, and warn that `--no-quality` only drops auto-bundled craft/discipline graders — the default `equivalence` and `code_review` graders remain LLM-backed and still require an evaluator ([d1374a76])

### Fixed
- Gate frozen-baseline reuse on a `harness_surface.baseline_digest`; cache hits whose surface no longer matches the active harness fall back to `cache_status=unknown` rather than replaying stale evidence ([9776d82])
- Include the implicit task list in the `stet eval rules` cache key so cache hits/misses match the realized task set ([36ec2c3])
- Majority-vote non-scored regrade samples when computing aggregate regrade outcomes ([cb77959])
- Harden replay-validity task identity so per-task gold-replay records bind to a stable identity ([4028f8a])
- Close arm identity QA gaps surfaced against the durable-identity contract ([c5caca6])
- Make frozen-baseline trial materialization selective and per-task, preserving trajectory artifacts and avoiding unnecessary copies ([e0d20b9], [f29a6db], [5f0a2fc])
- Document the new compare bootstrap flags in `stet eval compare --help` ([246ee48])
- Honor `--out` dataset reuse in the `stet eval rules` skill wrapper by short-circuiting the `rev_range_buildability` preflight when `dataset/build-summary.json` already exists and `--restart` is not set; the reuse decision is logged to stderr so `--plan` does not silently mask a divergent `--rev-range` ([d1374a76])
- Return `stet eval status` in ~2s on finalized compares by reading the persisted `eval_report.v1.json` sample-adequacy instead of walking `.stet/{eval-rules,leaderboard,archive,baselines}`; the cache binds to the requested compare root and rechecks adequacy inputs for freshness so fail-closed behavior is preserved (STET-387) ([8f439d49])

[v0.4.0]: https://github.com/benredmond/stet/releases/tag/v0.4.0
[de6c0bc]: https://github.com/benredmond/stet/commit/de6c0bc71f8cd69275e9caa9efa9b442e2de0fb5
[c64393c]: https://github.com/benredmond/stet/commit/c64393c6
[f3e9ee5]: https://github.com/benredmond/stet/commit/f3e9ee5f
[6870494]: https://github.com/benredmond/stet/commit/68704944
[6e07411]: https://github.com/benredmond/stet/commit/6e07411b
[3449973]: https://github.com/benredmond/stet/commit/344a9997
[f72da01]: https://github.com/benredmond/stet/commit/f72da01a
[5c5a181]: https://github.com/benredmond/stet/commit/5c5a1812
[ece1165]: https://github.com/benredmond/stet/commit/ece1165e
[5f671b3]: https://github.com/benredmond/stet/commit/5f671b3c
[a731873]: https://github.com/benredmond/stet/commit/a7187351
[9776d82]: https://github.com/benredmond/stet/commit/9776d820
[36ec2c3]: https://github.com/benredmond/stet/commit/36ec2c3c
[cb77959]: https://github.com/benredmond/stet/commit/cb77959a
[4028f8a]: https://github.com/benredmond/stet/commit/4028f8a7
[c5caca6]: https://github.com/benredmond/stet/commit/c5caca63
[e0d20b9]: https://github.com/benredmond/stet/commit/e0d20b96
[f29a6db]: https://github.com/benredmond/stet/commit/f29a6db1
[5f0a2fc]: https://github.com/benredmond/stet/commit/5f0a2fc7
[246ee48]: https://github.com/benredmond/stet/commit/246ee48e
[174a94e6]: https://github.com/benredmond/stet/commit/174a94e6
[4939dd3f]: https://github.com/benredmond/stet/commit/4939dd3f
[d1374a76]: https://github.com/benredmond/stet/commit/d1374a76
[8f439d49]: https://github.com/benredmond/stet/commit/8f439d49
[9866fe4]: https://github.com/benredmond/stet/commit/9866fe4

## [v0.3.1] - 2026-05-15

Enrichment runs natively in Go end-to-end; the Python `enrich_dataset.py` scaffolding is gone and prompts ship without XML fences.

### Changed
- Port `enrich_dataset.py` to Go and drop XML scaffolding from enrichment prompts ([5bb132b])

[v0.3.1]: https://github.com/benredmond/stet/releases/tag/v0.3.1
[5bb132b]: https://github.com/benredmond/stet/commit/5bb132bc872c858889714601c75aff7c93d9b310

## [v0.3.0] - 2026-05-15

Adds operator launch receipts, opus reasoning-curve evidence on the leaderboard, and tightens prompt-shape provenance with fail-closed enforcement when `ai_task` is missing. Smoke preflight is now bypassable for fast iteration, eval status terses on completion, and h2h gains typed grader-failure counters and small-sample directional reads.

### Added
- Surface opus reasoning-curve evidence on the leaderboard ([5e691ba])
- Shift `ai_task` prose to imperative goal-first phrasing during enrichment ([8812b1f])
- Record prompt-shape provenance during build and fail closed when `ai_task` is missing ([7c941bd])
- Add `--prompt-shape` to `stet build` with `self-contained-natural` as the default ([2ef2130])
- Expose `--skip-smoke-preflight` on `stet eval run` for fast candidate iteration ([84214b2])
- Terse `stet eval` status on complete and add `eval report --paths` ([4ae50c7])
- Recognize smoke-preflight runs in the frozen-baseline compare flow ([98df234])
- Polish plan JSON shape and emit an `rc!=0` next-step hint from `stet eval rules` ([b7d3eed])
- Persist smoke-seeded task provenance on the runner runtime artifact ([64653d1])
- Add rules study holdout lanes ([cbccb27])
- Add operator launch receipts to the CLI ([210ee15])
- Add Mandarin blog translations to the leaderboard ([dc16c7d])
- Publish the opus reasoning-curve writeup on the leaderboard ([16f961d])
- Surface typed grader-failure counters on `stet eval` report, status, and the decision receipt (STET-312) ([6e03355])

### Changed
- Reframe the stet-dist README as agent-first and add an onboarding quickstart ([2c02fa7])
- Collapse `TaskMetaConfig` literals and unify prompt-shape resolution across build paths ([b77f10c])
- Unify task-instruction assembly across all build paths ([4b1dcb6])

### Fixed
- Hoist grader-evaluator preflight and gate `activity_state` on resolved backend ([bebf8e1])
- Account for smoke preflight provenance in compare math ([c9711e7])
- Preserve tracked `.stet` contents after repo-bundle bootstrap ([5c8499c])
- Expose limited directional reads for small-sample h2h comparisons ([f217cb0])
- Preflight rules replay validity ([9ef099c])

### Internal
- Refresh dist collateral for v0.3.0 ([cbcab16])
- Drop the tessl MCP server config from codex ([5645ee8])
- Polish ONBOARDING.md voice and content for stet-dist ([20751fa])
- Include ONBOARDING.md in the dist sync CI step ([7cd553c])
- Add ONBOARDING.md explainer for human readers in stet-dist ([1e3eab9])
- Document why terse eval status points at the decision report instead of `--paths` ([8bbd214])
- Reframe the AGENTS guide and refresh design-stet plus QA scenario coverage ([a1e5557])
- Polish opus post presentation and sync copy from the vault ([e49a181], [445d8e7])
- Explain replay-invalid rules slices in the Stet skill docs ([8c624e7])

[v0.3.0]: https://github.com/benredmond/stet/releases/tag/v0.3.0
[cbcab16]: https://github.com/benredmond/stet/commit/cbcab16fcb1aa9af5d24baa4e4fe2e204df86ce8
[5e691ba]: https://github.com/benredmond/stet/commit/5e691bac457b6ca038721ecf20834a0f639be644
[8812b1f]: https://github.com/benredmond/stet/commit/8812b1f152adc533a1cee48df2c0bab449a3fe0d
[7c941bd]: https://github.com/benredmond/stet/commit/7c941bda2a838adec2ced203164a28b008619642
[5645ee8]: https://github.com/benredmond/stet/commit/5645ee8083db3aa8afe3c921905c619bd8d06f5c
[2ef2130]: https://github.com/benredmond/stet/commit/2ef21307d40347f9673e27b03839bdb0bc3f2477
[20751fa]: https://github.com/benredmond/stet/commit/20751fa3c7bdf276e982dd684b1bfc3645df9883
[7cd553c]: https://github.com/benredmond/stet/commit/7cd553cf4c27ce6a1e08cb4ba4f703831510be56
[bebf8e1]: https://github.com/benredmond/stet/commit/bebf8e1c69b1cfe600975b081b9de8e50697866f
[1e3eab9]: https://github.com/benredmond/stet/commit/1e3eab96097ebbd85b799893b147094ff9b2c862
[98df234]: https://github.com/benredmond/stet/commit/98df2349b3621ab179dcd6c6537801f07dfd4e13
[2c02fa7]: https://github.com/benredmond/stet/commit/2c02fa764c19e89b67070547d1d18b016b6347d9
[84214b2]: https://github.com/benredmond/stet/commit/84214b28f08c5f327ec434c99546d973698d8b66
[8bbd214]: https://github.com/benredmond/stet/commit/8bbd2143646dd6fc3684d8164135a90541a29509
[4ae50c7]: https://github.com/benredmond/stet/commit/4ae50c7432cd2d327acb7a25276a616cd0431334
[b77f10c]: https://github.com/benredmond/stet/commit/b77f10cfb5a41c2d7edb38f09313968b7658ad16
[4b1dcb6]: https://github.com/benredmond/stet/commit/4b1dcb690780e7ae9104e25fd77f5a669ce55ec8
[a1e5557]: https://github.com/benredmond/stet/commit/a1e55579cea07f87ecabc4336e78aa7ba9d60590
[5c8499c]: https://github.com/benredmond/stet/commit/5c8499cf4c2ed05eab8e336ab5fc99beb867e007
[b7d3eed]: https://github.com/benredmond/stet/commit/b7d3eedb98c7db80c6767acd96802c3650c7823c
[64653d1]: https://github.com/benredmond/stet/commit/64653d18af0769e8aff18fd83912022254bdd628
[cbccb27]: https://github.com/benredmond/stet/commit/cbccb27408315f9a3e3d6827d08ff865eca547d4
[c9711e7]: https://github.com/benredmond/stet/commit/c9711e7e1a38da3bc6a037e8f28dbb9855dbed9d
[210ee15]: https://github.com/benredmond/stet/commit/210ee1538449a9ccb0fa2f904d3c68e9c0ae0318
[dc16c7d]: https://github.com/benredmond/stet/commit/dc16c7dda56057eadc471dae44d1018ce811d97b
[e49a181]: https://github.com/benredmond/stet/commit/e49a18114a8b96ad79802f3e21f9eba8b06a5b6d
[445d8e7]: https://github.com/benredmond/stet/commit/445d8e75bf423175921d28f559d286ac4116d8e1
[16f961d]: https://github.com/benredmond/stet/commit/16f961d65c75b41f34c695319e6c4317d0bc8495
[f217cb0]: https://github.com/benredmond/stet/commit/f217cb06b02a93333d5dafae55ec767292d3241e
[9ef099c]: https://github.com/benredmond/stet/commit/9ef099cbc0def945bf8ea298705d5d0bf6ed2f41
[8c624e7]: https://github.com/benredmond/stet/commit/8c624e74d966c399735a7e255fe3c2c6fce606b2
[6e03355]: https://github.com/benredmond/stet/commit/6e033556f067387818d7522ec81f7c0b90f7bf65

## [v0.2.0] - 2026-05-11

Hardens the `stet eval rules` flow end-to-end with grader-profile persistence, preflight checks, and surfaced provenance; introduces the GPT-5.5 reasoning-curve leaderboard post and pairwise order-swap judging for custom-grader compares; adds activity-state disambiguation, sample-adequacy reporting, and a stet-qa skill harness for black-box testing the shipped Stet docs. Many small fixes tighten artifact integrity (non-regular file rejection, symlink-escape guards) across the harness.

### Added
- Add `--grader-ai-cmd` / `--grader-ai-model-id` wrapper flags to the eval-rules skill (STET-338) ([9b8c370])
- Surface agent-side exceptions in the `last_error` receipt (STET-332) ([f96da10])
- Improve Stet SEO surfaces on the leaderboard ([7a18f7f])
- Add sticky TOC to the GPT-5.5 reasoning-curve post ([540dcc4])
- Publish the GPT-5.5 reasoning-curve post and add it to model comparisons ([5f890e5], [91c8fa4])
- Preserve explicit `--mode` through stitch and repair ([9cda0af])
- Support optional requested graders and explicit repair evaluators ([9ee0208])
- Centralize structured custom-grader calls ([b9ced48])
- Persist and reuse eval-rules grader profiles, with planning and reported provenance ([893a8df], [dec49c3], [8b377af], [ac48552])
- Add safe stale Docker cleanup to harbor ([fdfc2f5])
- Add eval-rules grading controls ([2a5ee65])
- Persist task outcome history across runs ([8fc26e1])
- Surface eval sample adequacy ([ecd2b60])
- Add order-swap pairwise per-task judging for custom-grader compares ([1d6cbdb])
- Add the stet-linear-tpm skill for Symphony-ready ticket shaping ([d31901f])
- Add `max` as a first-class reasoning-effort tier ([7d47898])
- Make evals quota-aware ([7309948])
- Accept an explicit agent for `stet eval smoke` ([37a7c19])
- Add a default randomized H2H task order ([f9e8320])
- Bake `claude-code` and `codex` into the harbor image ([e766928])
- Route Harbor Codex through `codex-lb` ([498a132])
- Register `gpt-5.5` with pricing and alias ([97bbfbf])
- Add stet-qa scenarios for `claude_md`, `docs_glob`, `model_update`, and `skill_diff` ([98bd7cb])
- Migrate leaderboard datasets to Stet v1 and rewrite ingestion ([1a06b2a])
- Bake `install_config` into per-task Dockerfile and skip node lifecycle scripts during baked install ([1af7972], [8d86967])
- Surface trajectory-derived behavior metrics in eval reports ([0b08059])
- Add artifact-retention compaction ([6d2cb0e])
- Add `--skip-smoke-preflight` to bypass the candidate smoke gate (eval-rules) ([0d446c8])
- Add Opus 4.7 vs 4.6 zod blog item to the leaderboard RSS feed ([b8478f8])
- Add the agents-md-preflight QA scenario and shared 1-task fixture ([fdc0f61], [4819136])
- Add the validate-change-manifest QA scenario and fixture ([b6c477d], [daaddce])
- Add stet-qa SKILL.md scaffolding (skeleton, preamble, report template, fixtures reference, design spec) ([20f7980], [83d0517], [4314d57], [7b29eb8], [8ebc50d])
- Add the stet-qa implementation plan ([ccea8fb])
- Register `eval_rules_plan` as a commercial command ([1e7f44e])
- Publish the Opus 4.7 vs Opus 4.6 Zod writeup with cost and token detail ([cf26998], [77fc7d0])
- Add the GPT-5.5 vs Opus 4.7 blog post and blog SEO scaffolding ([2d9e7da])
- Add an agent setup snippet to `/private` ([cf925a1])

### Changed
- Surface artifact-discrimination diagnostic for any custom-grader compare ([36b923f])
- Honor model-specific AI agents ([d4f33a7])
- Refine GitHub doc-only path classification ([277508b])
- Bound `GRADE_CUSTOM` rubric grader calls with a per-call timeout ([0471faa])
- Stabilize custom-grader no-patch scoring ([8276a9d])
- Update site navigation links and refresh the homepage funnel ([67d401a], [a9ab39c])
- Update the GPT-5.5 vs Opus blog post and methodology data ([8b8d276], [dbe4cf4])
- Overlay current conventions in materialized tasks ([33d8150])
- Improve SEO pages for model comparisons ([a6c36e8])
- Separate grader AI config in eval flows ([a45858f])
- Sort custom-rubric prompt criteria deterministically ([3900957])
- Convert cramped Opus 4.7 tables to bar charts and merge review/discipline into one rubric chart ([1bab40e], [54d58ed])
- Refresh validate-change-manifest dogfood with post-fix run ([8a40b88])
- Stop default Claude Keychain auth lookup ([36eaadc])
- Reduce Vercel compute for inspect routes ([b50c773])

### Fixed
- Add `activity_state` to disambiguate in-flight versus terminal eval status (STET-333) ([83b7ba9])
- Tighten plan/manifest receipts and skill text (rules) (STET-329) ([709295f])
- Reject non-regular pinned dependencies, repo tarballs, validation agent patches, config files, test inference files, score patches, and unsafe cost-usage artifacts and output-root manifests; block git-internals context paths ([ef30ea8], [4c35c65], [bedad3a], [7202b8a], [c812fc2], [a59e904], [e79efe0], [186e25a], [160263b])
- Refresh stale grader coverage from arm summaries ([3611c8c])
- Repair short/non-hex citations, lift nested findings, and add skip-reason-specific refusal text (eval-rules) ([f0e01bc])
- Repair rules QA follow-up flows ([d756cb5])
- Treat nested smoke evidence as pending-compare arm evidence ([d5781c8])
- Share Claude envelope unwrap and refuse empty skill datasets (eval-rules) ([826668f])
- Unwrap Claude `--output-format json` envelope before grader parse ([165f5eb])
- Classify wrong-repo as `repo_not_a_git_repository` and fix QA fixture repo paths ([ed1d4fc])
- Wire grader-ai flags, classify default-branch `launch_error`, and document `--tasks` coupling ([3ae2acb])
- Surface pre-arm failures via `launch_error` and fix baseline path lookup ([400959e])
- Preflight rev-range buildability and document `--rev-range` (STET-331) ([4b9611c])
- Preflight grader provenance in `eval-rules-plan` (STET-330) ([20a1c9c])
- Preflight `--out` dataset and surface build errors in the eval-rules skill ([ab85acf])
- Preflight repo-managed skills root symlinks (STET-327) ([b90aac8])
- Refuse `eval rules` launch when LLM grader credentials are missing (STET-324) ([99fc652])
- Stop recommending resume on terminal rules-arm failure (STET-325) ([5c37fb4])
- Resume resolves treatment paths against the suite repo root ([01433d1])
- Preserve grader and cost evidence on stitch ([55c0cbb])
- Recover rules resume evidence ([9370f05])
- Preserve regrade economics in summaries ([25f5edb])
- Bound frozen-baseline materialization ([cc44270])
- Expose eval report reasoning effort ([896df69])
- Recover trailing custom-grader JSON ([8785d0e])
- Resolve nested sample-adequacy history roots ([dab87b6])
- Detect mixed arm provenance ([c813057])
- Surface rules compare arm status ([73cfd44])
- Preserve frozen-baseline custom graders ([ab5c0b7])
- Reclaim `artifacts/agent.patch` duplicates left by harbor ([fc8cba9])
- Avoid bare 429 quota classification ([9b9b467])
- Copied-patch path classification ([d6688b0])
- Surface repairable custom-grader parse failures ([778891f])
- Enforce grader-evaluator provenance ([db0d690])
- Classify executor failure tail output ([c32f3f8])
- Enforce clean guidance overlays ([c3c8de7])
- Target-pass commit overscan ([0759526])
- Improve blog text contrast ([ee1772e])
- Remove visible SEO duplication from blog posts ([512e9b7])
- Harden review-retry prompt parse errors ([62045c5])
- Repair embedded prompt source loading ([577ecea])
- Reject weekly doctor reports symlink escapes ([966ea35])
- Fix unsafe run-ID artifact lookup ([5fc50b8])
- Fix markdown-bold kv value parsing ([38bd4e3])
- Reject non-executable generated test commands ([08737b5])
- Fix Codex assistant trajectory capture ([ab00275])
- Reject symlinked validation roots ([a19a4a1])
- Reject non-regular gate prompt sources ([6419f9a])
- Validate manifest build numeric flags ([1410ac1])
- Ignore external diff for split patches ([c2f2beb])
- Exclude failed tasks from the weekly denominator gate ([d25e61a])
- Preserve UTF-8 in review-retry prompt ([6e4a324])
- Preserve eval-rules plan launch flags ([f6db705])
- Use per-task cost and time in the GPT-5.5 post ([00b470c])
- Fix frontend audit and Turbopack warnings ([00164b2])
- Prevent convention overlays from polluting agent patches ([96d4090])
- Fix eval-rules runtime evidence locator ([f87d834])
- Fix grader coverage reporting ([53079cd])
- Recover cache tokens when rollup omits them and sum Claude assistant turns ([489ab31])
- Merge experiment report when arms record different dataset paths but identical task slices ([423d581])
- Smoke-preflight liveness classification ([0ba1f41])
- Smoke-gate canonical harbor pass ([9cd6a4b])
- Honor gitignore in harbor patch capture ([edc58f0])
- Preserve evaluator model provenance in grader artifacts ([8a0d747])
- Avoid copying run artifacts during compare staging ([e12bcfb])
- Improve rules-skill wrapper recovery ([a43d462])
- Gate Vercel tracing config so local dev resolves tailwindcss ([5f9f977])

### Internal
- Forbid bespoke leaderboard eval shortcuts in agent docs ([942ac71])
- Refine smoke-preflight provenance and terminal no-patch coverage ([5f07a75])
- Assert h2h repo root by source marker, not basename ([f56a5a6])
- Stabilize stet qa grader preflight ([5006a18])
- Migrate `agents-md-preflight` from sonnet-4.6 to gpt-5.4 (stet-qa) ([32131fe])
- Pin `rev-range-buildability` seeded_from to STET-331 fix SHA ([316efae])
- Sync dist skill snapshot ([718a961], [2520373], [54c1383])
- Roll up failure-path skill drift findings (STET-337) ([8180be2])
- Sync GPT-5.5 reasoning-curve post copy with vault edits ([5aa49ab])
- Ignore claude worktrees, generated leaderboard typings, local launchers, and scheduler lock ([da09121], [fcf22a1])
- Reuse command normalization for task defaults ([e9a1c19])
- Share config value resolution ([7cb5f5d])
- Centralize relevance sorted unique strings ([068040c])
- Centralize Claude auth env lists ([b3952ac])
- Share workbench baseline record loading ([7de8135])
- Centralize path containment checks ([8017b74])
- Share safe path joining ([f0537a0])
- Filter weekly denominator membership ([6d5f68c])
- Preserve task grader rubric scores ([608a249])
- Share local-inspect file traversal ([547133e])
- Clarify leaderboard dogfood eval policy ([5200eb4])
- Refactor leaderboard navigation links ([219ac3e])
- Refactor aicmd explicit option handling ([79809a0])
- Simplify diff path marker parsing ([81d33ac])
- Cover Next config env behavior ([9c5c168])
- Trigger Vercel deployment ([823b32c])
- Record stet-qa dogfood-03 gap-closure verification ([7d133fe])
- Address stet-qa dogfood-02 unclear-receipt gap ([c7eadd9])
- Link the stet-qa skill from the Progressive Disclosure Index ([22dbd82])
- Record stet-qa dogfood: parallel dispatch synthesis ([f338599])
- Record stet-qa dogfood: validate-change-manifest ([61bf64f])
- Rename stet-qa report file to `qa-report.md` ([033f03d])
- Cover `--pairwise` cap and document flags in compare help ([9b5991d])
- Update archived zod evidence paths ([274f59c])
- Add the flu82 graphql xhigh launcher ([778f3b9])
- Merge origin/main and merge the GPT-5.5 reasoning-curve blog ([18b7614], [903f126], [2c12471])

[v0.2.0]: https://github.com/benredmond/stet/releases/tag/v0.2.0
[d5781c8]: https://github.com/benredmond/stet/commit/d5781c841fe0f79b69afe5403d5251064e8be700
[d756cb5]: https://github.com/benredmond/stet/commit/d756cb581b780e1fc1c260c6940182aa0b5bd07d
[5006a18]: https://github.com/benredmond/stet/commit/5006a185fcb88bb6ee4cee84d644e4541a013376
[718a961]: https://github.com/benredmond/stet/commit/718a96182dc8de452a3bffdf2ac8cee1a253d6c7
[da09121]: https://github.com/benredmond/stet/commit/da09121160b569b33e379e2da749a5c013181c3b
[3611c8c]: https://github.com/benredmond/stet/commit/3611c8c04c8f84fdafe483136543a945603cf562
[f0e01bc]: https://github.com/benredmond/stet/commit/f0e01bc16e373acddf4c29b8b2df9e5d271b0632
[498a132]: https://github.com/benredmond/stet/commit/498a13284ef4370dbf5d631d4cfc22dc9b5011ae
[826668f]: https://github.com/benredmond/stet/commit/826668f0be3188e849d5b1e0e171c31fbfcecf21
[2520373]: https://github.com/benredmond/stet/commit/2520373d25bec1866021f6cacc592b956f5127f4
[165f5eb]: https://github.com/benredmond/stet/commit/165f5eb92362e83008bb13855dd75ac47d4744a1
[ed1d4fc]: https://github.com/benredmond/stet/commit/ed1d4fce21b043616b505260f95da00a3a091cf2
[3ae2acb]: https://github.com/benredmond/stet/commit/3ae2acb7b2e9f53a9b184e9921e04a69f35f2c40
[400959e]: https://github.com/benredmond/stet/commit/400959eed17b8e18c0689dbc56297606b82e32cc
[f56a5a6]: https://github.com/benredmond/stet/commit/f56a5a664f94a485c248d5b398f77cdae39706a0
[9b8c370]: https://github.com/benredmond/stet/commit/9b8c370834dc6611c0da6a116e41cbc1d189a25f
[316efae]: https://github.com/benredmond/stet/commit/316efae445d452b4314925af9108c03223d437d7
[4b9611c]: https://github.com/benredmond/stet/commit/4b9611c1f169eb0f710604f884b37362dcc01fbc
[f96da10]: https://github.com/benredmond/stet/commit/f96da10d22407367833b914c5b1232b81a67a5f9
[20a1c9c]: https://github.com/benredmond/stet/commit/20a1c9cd936e51ab30b9f4bbf171b9e666ec2943
[83b7ba9]: https://github.com/benredmond/stet/commit/83b7ba961da3279d6fad0669e2c81c92b2206a45
[8180be2]: https://github.com/benredmond/stet/commit/8180be2778cbcc8056ad60c0174bd24983bf6fcb
[709295f]: https://github.com/benredmond/stet/commit/709295f5b7ce67e28861cc0b56ca88984cc680be
[ab85acf]: https://github.com/benredmond/stet/commit/ab85acf973dc2f09e8f81f14efa955a31b1b7753
[01433d1]: https://github.com/benredmond/stet/commit/01433d139045df51ae169b95ea94d15e9f849588
[b90aac8]: https://github.com/benredmond/stet/commit/b90aac8ee2140fca0d8624847d757c2ddbfcb65b
[99fc652]: https://github.com/benredmond/stet/commit/99fc65246bfaa2d7b713f19616915970b99e6e9a
[5c37fb4]: https://github.com/benredmond/stet/commit/5c37fb479cbb0d19e6cc25a0d12d5e702d009fb8
[2c12471]: https://github.com/benredmond/stet/commit/2c1247190603bd3e78aa7997b1a39b9c01f1b397
[7a18f7f]: https://github.com/benredmond/stet/commit/7a18f7fa01dc294b07b3e4ed9bf471a646c17f70
[55c0cbb]: https://github.com/benredmond/stet/commit/55c0cbbb7cd0ffe5da28579aa653a3e41f0f7432
[9370f05]: https://github.com/benredmond/stet/commit/9370f05a0841beb8df25922c8f655ad0d9236e98
[540dcc4]: https://github.com/benredmond/stet/commit/540dcc48f74aef5c9d587a1c4e75e894e1dd49ab
[91c8fa4]: https://github.com/benredmond/stet/commit/91c8fa4a0487bd39da1133b45bec9516faa63cf5
[5aa49ab]: https://github.com/benredmond/stet/commit/5aa49ab15a27f426b6541fa523d3dfe94c472358
[5f07a75]: https://github.com/benredmond/stet/commit/5f07a7559f2931bffdb1d48b3b2abc5144b71984
[9cda0af]: https://github.com/benredmond/stet/commit/9cda0af27ad4e3b95fc9a5cf1d75e151b2f80ea0
[9ee0208]: https://github.com/benredmond/stet/commit/9ee02089ea341d68196502cec38436abb1ef41ad
[942ac71]: https://github.com/benredmond/stet/commit/942ac711d07322169a08990c3323edf792ecf0d3
[b9ced48]: https://github.com/benredmond/stet/commit/b9ced48a2bed9e9c03fd7d2fd9543ec255f4597e
[18b7614]: https://github.com/benredmond/stet/commit/18b76145759a2f1dfe66da96b258604603d47c02
[903f126]: https://github.com/benredmond/stet/commit/903f1262999c799bdf2ef3f1d84cceb73585c69f
[5f890e5]: https://github.com/benredmond/stet/commit/5f890e5840abd6159373b99ebac6eb3eab6e4dc8
[25f5edb]: https://github.com/benredmond/stet/commit/25f5edb41faf8311cf54041085cf5771570b8a7b
[ac48552]: https://github.com/benredmond/stet/commit/ac485520516eaa06def7905f985e4d5a36613ca6
[8b377af]: https://github.com/benredmond/stet/commit/8b377afc50b67cc7670a24f8d5a97e80ba2df536
[893a8df]: https://github.com/benredmond/stet/commit/893a8dfa54e776f6e37d7d9d7787fc077fef3098
[dec49c3]: https://github.com/benredmond/stet/commit/dec49c3fdf7576442db2fd2e04580113483fb2ff
[cc44270]: https://github.com/benredmond/stet/commit/cc44270f6da92d6c195663281907af444149ff09
[fdfc2f5]: https://github.com/benredmond/stet/commit/fdfc2f5a73a6f1210c870412c920d124c8ab8c91
[778f3b9]: https://github.com/benredmond/stet/commit/778f3b9d6759b90b02904c9ba0df8aa3ca299f28
[274f59c]: https://github.com/benredmond/stet/commit/274f59cbb8e6d4c64fece5a86903836c14be80c3
[2a5ee65]: https://github.com/benredmond/stet/commit/2a5ee659524df4f5d2068f9c49442a0a1b2d0541
[896df69]: https://github.com/benredmond/stet/commit/896df6937952ec938a65754589eefea6504cb3fd
[8785d0e]: https://github.com/benredmond/stet/commit/8785d0ebf2835674cee6f2e3a2f4cffe45cde0fd
[dab87b6]: https://github.com/benredmond/stet/commit/dab87b6d6ed66fcdf4648b9d6e688b0e9f839b1d
[c813057]: https://github.com/benredmond/stet/commit/c8130577e01c792d2375863c9ce2919cd634a09d
[8fc26e1]: https://github.com/benredmond/stet/commit/8fc26e12e8e2bbc71c333c878493e81ff3050d65
[ecd2b60]: https://github.com/benredmond/stet/commit/ecd2b60f0ada535a4332aa22bab13cbdf0d76642
[73cfd44]: https://github.com/benredmond/stet/commit/73cfd44b65237ce896472923ae5f70ec30d29f7b
[36b923f]: https://github.com/benredmond/stet/commit/36b923f022976564c7b0c6333a25f8ffec76db47
[ab5c0b7]: https://github.com/benredmond/stet/commit/ab5c0b71df32a79d40dd02799a7a7fbe4f2469c3
[0471faa]: https://github.com/benredmond/stet/commit/0471faacf2e3ab3ab0acf9e4dece6c14bc11d0d5
[e766928]: https://github.com/benredmond/stet/commit/e766928c75010455d8ebcdfa62de95c2fc51a214
[fc8cba9]: https://github.com/benredmond/stet/commit/fc8cba98053be82a25e8130a13a8a9d5f2dc1da4
[9b5991d]: https://github.com/benredmond/stet/commit/9b5991d56d459652364ef14a82f5cdce3584adb9
[1d6cbdb]: https://github.com/benredmond/stet/commit/1d6cbdb540f63c5be92d5363d77dfffcb542d270
[d31901f]: https://github.com/benredmond/stet/commit/d31901ff60b086e003b9806125b588e04299d84b
[7d47898]: https://github.com/benredmond/stet/commit/7d47898cef069013bce42083b6f8bd265062663a
[8276a9d]: https://github.com/benredmond/stet/commit/8276a9d7fa5864de8bc1baa1440cf6c068816171
[ef30ea8]: https://github.com/benredmond/stet/commit/ef30ea838e3e91f1bce21fae4a3f147863e0ae92
[e9a1c19]: https://github.com/benredmond/stet/commit/e9a1c194e1dd9a9186962c55a4cc699fbdc5c943
[9b9b467]: https://github.com/benredmond/stet/commit/9b9b4676c7625cd9467cc00a4a28c5679a0a5b9f
[e79efe0]: https://github.com/benredmond/stet/commit/e79efe0e5131e06f6c8e6a36c45ad388174500d4
[d6688b0]: https://github.com/benredmond/stet/commit/d6688b0e8d981b6ffc2ddb0aadfbb275170f6a5c
[3900957]: https://github.com/benredmond/stet/commit/39009575b838d1453af8780b61baa3c78f7f8470
[7cb5f5d]: https://github.com/benredmond/stet/commit/7cb5f5d67a6d91be55339d18ecdf650e25177983
[186e25a]: https://github.com/benredmond/stet/commit/186e25a17d64f8ff52cac1bc54274442841a56ad
[277508b]: https://github.com/benredmond/stet/commit/277508ba4f6c173690e37d20a88c372a228e5ee1
[068040c]: https://github.com/benredmond/stet/commit/068040c55a1198a1013e22e1dd19e9d547bb3c4e
[4c35c65]: https://github.com/benredmond/stet/commit/4c35c6565ce42a6fb038df796fe92138e03546a8
[d4f33a7]: https://github.com/benredmond/stet/commit/d4f33a7cd3d1085b5af41cb29a87a2201ac04624
[778891f]: https://github.com/benredmond/stet/commit/778891fa6f8b73b630d7658e5f384ffe53317800
[bedad3a]: https://github.com/benredmond/stet/commit/bedad3a1d3df97b0c7e6f24f9a6d9ddf29961fcd
[db0d690]: https://github.com/benredmond/stet/commit/db0d6900de68a4bf14cd0369fadeca2cbe94fb64
[7202b8a]: https://github.com/benredmond/stet/commit/7202b8a26d66782005489ac74f9163c6f4895749
[b3952ac]: https://github.com/benredmond/stet/commit/b3952ac5af63aa21cf199d2d80bb06c63cea4858
[c32f3f8]: https://github.com/benredmond/stet/commit/c32f3f8ded284573c6e8e0962e4fdf639ca811dc
[c812fc2]: https://github.com/benredmond/stet/commit/c812fc247d5bd4d6441e5686f17c8b07affce413
[a59e904]: https://github.com/benredmond/stet/commit/a59e904f0960a974dea618dbca91ddc261843063
[7de8135]: https://github.com/benredmond/stet/commit/7de81355abb234d71cc4d35630135ff171de4ea3
[160263b]: https://github.com/benredmond/stet/commit/160263b1450d0852af5e04e62adc7b8f1e39cbc1
[6d5f68c]: https://github.com/benredmond/stet/commit/6d5f68cb61cc7fba2d32ea124d80ce37444430b1
[608a249]: https://github.com/benredmond/stet/commit/608a249ad15499f9b951a7cbcf87edf405d2c6dc
[c3c8de7]: https://github.com/benredmond/stet/commit/c3c8de7870324c6ec96ab6b0fb9187d93ee9b9b7
[0759526]: https://github.com/benredmond/stet/commit/0759526a352dbc682c356152cd2a17349a7d7dc6
[547133e]: https://github.com/benredmond/stet/commit/547133e09211641a15716c0da005450e45a25bc1
[5200eb4]: https://github.com/benredmond/stet/commit/5200eb400c20d9b8d1805d39f3372389d6401704
[ee1772e]: https://github.com/benredmond/stet/commit/ee1772ee5fafe1179f209bb430276f17cdc240ea
[512e9b7]: https://github.com/benredmond/stet/commit/512e9b7baa02e0cbe33d8aa9e5ed842bac23c825
[62045c5]: https://github.com/benredmond/stet/commit/62045c5b8e1073c067debf9ab0b404a0d8fa007e
[7309948]: https://github.com/benredmond/stet/commit/730994826c74e9b81b398a165dd6571dad972854
[577ecea]: https://github.com/benredmond/stet/commit/577eceaf36e5d9d9b928ee4b051605cc4539737c
[8017b74]: https://github.com/benredmond/stet/commit/8017b747a0fc5dcf8028fddc98281f721328b3ac
[966ea35]: https://github.com/benredmond/stet/commit/966ea3576e6f3d30ca6c857f9aefa3e5b4bbd74e
[37a7c19]: https://github.com/benredmond/stet/commit/37a7c196c318ec7d2da24702d53e99d344a0f225
[5fc50b8]: https://github.com/benredmond/stet/commit/5fc50b8948db6d8f1b9de87d2247ad83c3e27921
[219ac3e]: https://github.com/benredmond/stet/commit/219ac3e5c74e4aa774b9fecbaa2b7a5a354190e3
[38bd4e3]: https://github.com/benredmond/stet/commit/38bd4e37d5f55c686ba36419d65b1d0ced0fd014
[08737b5]: https://github.com/benredmond/stet/commit/08737b522321e9e3e4dc53d999414422d85a9faf
[ab00275]: https://github.com/benredmond/stet/commit/ab0027509572b35649751ee4b5f44b61c26e4b4c
[a19a4a1]: https://github.com/benredmond/stet/commit/a19a4a14ed76ece8193a0dbc796fbb60d66527f4
[79809a0]: https://github.com/benredmond/stet/commit/79809a0c0200e65f21610ed39bd857f5715d31d6
[6419f9a]: https://github.com/benredmond/stet/commit/6419f9a1b405dba38f1453df2d1bef633160c13f
[a6c36e8]: https://github.com/benredmond/stet/commit/a6c36e860ac852767f6e480fd98b1dd1b84cf062
[1410ac1]: https://github.com/benredmond/stet/commit/1410ac131e80b6ab69759254e299c623746e8e1e
[c2f2beb]: https://github.com/benredmond/stet/commit/c2f2bebafc915e095ddb682e89892e16debd74d7
[d25e61a]: https://github.com/benredmond/stet/commit/d25e61a7e44e570ab05aa915fcf0b6a8a25dacad
[81d33ac]: https://github.com/benredmond/stet/commit/81d33ac3c6bf1a8c6f5e3fa4acfeb5771de8dbec
[6e4a324]: https://github.com/benredmond/stet/commit/6e4a324966604609ad0ea6e86b67d52166931c97
[f9e8320]: https://github.com/benredmond/stet/commit/f9e832075b9b4651bf745ff5fbceade61e99c734
[f0537a0]: https://github.com/benredmond/stet/commit/f0537a01810bd49b1dce4c1099c389040d7478fb
[f6db705]: https://github.com/benredmond/stet/commit/f6db705609cdb333778ad120e7c40b726fb4088d
[00b470c]: https://github.com/benredmond/stet/commit/00b470c00affc460993e27a3c40aff164235f056
[823b32c]: https://github.com/benredmond/stet/commit/823b32c2f7de4fe640566b88690edf5fde54ff30
[a9ab39c]: https://github.com/benredmond/stet/commit/a9ab39c603970a21c5a0d0abf4dbf452cada3d28
[67d401a]: https://github.com/benredmond/stet/commit/67d401ad078d2ca6f1f652f8ba9d8d9e47b294f8
[8b8d276]: https://github.com/benredmond/stet/commit/8b8d276aa4b83761c6ff1e0463220ef92d0da45d
[dbe4cf4]: https://github.com/benredmond/stet/commit/dbe4cf489d28a09c4f22c6490397cc9751e5293f
[00164b2]: https://github.com/benredmond/stet/commit/00164b247b30bf0406ae037b8c4b39c5f671eb06
[2d9e7da]: https://github.com/benredmond/stet/commit/2d9e7da7a4d6a20cf133e2286a984eb7dbaf8ff8
[b50c773]: https://github.com/benredmond/stet/commit/b50c77370fff7113000bb8bbb6ec692b1425974c
[54c1383]: https://github.com/benredmond/stet/commit/54c13832c65e62ede952dd7bf064128641bc9f2b
[cf925a1]: https://github.com/benredmond/stet/commit/cf925a18f11cfb5cb82ca5f32bdfd1e7c64a7d5d
[96d4090]: https://github.com/benredmond/stet/commit/96d4090034d0fa86c39d1a189609157ed62e5432
[f87d834]: https://github.com/benredmond/stet/commit/f87d834a4f4c8ad2475a9752e901ae0fac2832de
[33d8150]: https://github.com/benredmond/stet/commit/33d8150b2146a2f52e6cbdf831e73ee6bb40bd0e
[53079cd]: https://github.com/benredmond/stet/commit/53079cdfcf3fb444db7dd035d53bab0d4a7e6d75
[489ab31]: https://github.com/benredmond/stet/commit/489ab3170dddc65ecc1928fc245aab035f4da04a
[423d581]: https://github.com/benredmond/stet/commit/423d58119db71bbbbd50ac9a822bee6f76fd9045
[0d446c8]: https://github.com/benredmond/stet/commit/0d446c8721ca3da7129dc03b03c59c69af90eb49
[0ba1f41]: https://github.com/benredmond/stet/commit/0ba1f414e8b8670353fff1e8e93b2d05c92dcfc6
[fcf22a1]: https://github.com/benredmond/stet/commit/fcf22a1c28d8befa73c9503303bfc3e2bb934bbb
[8d86967]: https://github.com/benredmond/stet/commit/8d869675932698f01f19054152b743c60e0c8d59
[a45858f]: https://github.com/benredmond/stet/commit/a45858f3342599f96ccaa5ca339f8b29cf6f7481
[9cd6a4b]: https://github.com/benredmond/stet/commit/9cd6a4bf22e7eece42f58e235aa38dc5bc2735e9
[0b08059]: https://github.com/benredmond/stet/commit/0b0805925489e1012fae52d5b743ec16b7b366ac
[6d2cb0e]: https://github.com/benredmond/stet/commit/6d2cb0e584e26c088efc533f1b34a4f674f17f31
[edc58f0]: https://github.com/benredmond/stet/commit/edc58f0533c8df2f7221d806e5d874bb5bfef24d
[1af7972]: https://github.com/benredmond/stet/commit/1af7972f3d2b162ff6bf30c11595a052864e12d9
[8a0d747]: https://github.com/benredmond/stet/commit/8a0d747435bfc0480323548182bc694d270631fd
[e12bcfb]: https://github.com/benredmond/stet/commit/e12bcfbf776a2951b87655733574645143b9f824
[a43d462]: https://github.com/benredmond/stet/commit/a43d462e28856755a2cf726af0f66a2b222cce17
[b8478f8]: https://github.com/benredmond/stet/commit/b8478f81cac67ff4a5864c8d30d9137a35319857
[97bbfbf]: https://github.com/benredmond/stet/commit/97bbfbf6025fb806ebebd9437dcf3ba42c34b204
[32131fe]: https://github.com/benredmond/stet/commit/32131fe3849ba3a56c460a41bc7f560e71eee0f2
[98bd7cb]: https://github.com/benredmond/stet/commit/98bd7cbd2b281aadbf92c80068cd2b24b2d1344d
[1a06b2a]: https://github.com/benredmond/stet/commit/1a06b2adb4b15b232c16e83d2d9b30a942d81138
[9c5c168]: https://github.com/benredmond/stet/commit/9c5c168de815a7bbfae342da52aa3236d0342bba
[7d133fe]: https://github.com/benredmond/stet/commit/7d133fed2cf51dcf963a9acadf854c2c4d96cecd
[c7eadd9]: https://github.com/benredmond/stet/commit/c7eadd9d63644f2873a4846e9b7d1362d14e5a6e
[22dbd82]: https://github.com/benredmond/stet/commit/22dbd82004aa2d018592eaa198f06bc6d6a71e88
[f338599]: https://github.com/benredmond/stet/commit/f338599fd35b899b84929b7b9f21d6482400a8c7
[fdc0f61]: https://github.com/benredmond/stet/commit/fdc0f613e0a7d7cc76e4f88359506d72e7cae920
[4819136]: https://github.com/benredmond/stet/commit/481913697e87c37860ef1bc0a49da6a972ee7596
[8a40b88]: https://github.com/benredmond/stet/commit/8a40b881528b96ff0220d83f9e706c471f661e06
[033f03d]: https://github.com/benredmond/stet/commit/033f03da5ea7fd203f729c7394467a5f5795c578
[61bf64f]: https://github.com/benredmond/stet/commit/61bf64fe154e06d760d80fea37948e05acb82108
[b6c477d]: https://github.com/benredmond/stet/commit/b6c477d563d96239322b16ebcc4d41bf18e63b84
[daaddce]: https://github.com/benredmond/stet/commit/daaddce587e66d3e4634f31acda56d4a1565749d
[36eaadc]: https://github.com/benredmond/stet/commit/36eaadc2fcabf4f29a690295b4a0384fddf8179f
[1e7f44e]: https://github.com/benredmond/stet/commit/1e7f44ec94025b61a53b147a7a35bde0c9d8cc42
[77fc7d0]: https://github.com/benredmond/stet/commit/77fc7d020fe1a378082e9a4950f3bdbe19888458
[7b29eb8]: https://github.com/benredmond/stet/commit/7b29eb84d8b8c8fe60d4396ae97ec2056a923a4f
[4314d57]: https://github.com/benredmond/stet/commit/4314d575cfc3f3b0dd4852d6f2a1664123ba3be1
[83d0517]: https://github.com/benredmond/stet/commit/83d05170c727248e140dd6aebaf062205f2c29a8
[20f7980]: https://github.com/benredmond/stet/commit/20f7980d89ec19bec622e7007105333e9861f7cf
[54d58ed]: https://github.com/benredmond/stet/commit/54d58ed86795a2a610d557b782c402c7416c570a
[ccea8fb]: https://github.com/benredmond/stet/commit/ccea8fb86e23c3ea449da1fd50d7894391108ec4
[1bab40e]: https://github.com/benredmond/stet/commit/1bab40ef0e1df78545d684f8156c4530b219596b
[5f9f977]: https://github.com/benredmond/stet/commit/5f9f977a8a652f5a2371e5b8e48888e025334d99
[cf26998]: https://github.com/benredmond/stet/commit/cf269982658e7667a9cf9594b6f3b5e9c21fa48a
[8ebc50d]: https://github.com/benredmond/stet/commit/8ebc50d7b2cd8babb0d7c9830bc694c509d49020

## [v0.1.0] - 2026-04-17

Initial productized release of the Stet CLI. Stet measures whether an AI coding change is safe to ship, covering the full capability lifecycle: probe and workbench for iterative improvement, gate for promote/hold/rollback, and monitor for scheduled regression detection. v0.1.0 lands the public command surface (`stet build`, `stet eval`, `stet eval rules`, `stet baseline`, `stet monitor`, `stet workbench`, `stet auth`), the canonical `eval_report.v1.json` trial result, a working harbor-backed Docker harness for replayable real-repo task corpora, the Next.js leaderboard frontend, and the stet-cli distribution channel for `pip`-style install.

### Added
- Public, productized CLI surface (`stet build`, `stet eval`, `stet eval rules`, `stet eval workbench`, `stet eval batch-grade`, `stet eval calibrate`, `stet baseline`, `stet monitor`, `stet workbench`, `stet auth`) with versioned model names, gauge-style help output, and a public manifest contract ([e7eef57], [8047f55], [7f7dcef], [11c8b74], [c3a26a4], [8fbd054], [251f33d], [086b59b], [932d07f], [bbe1764], [066e700], [f3e243b])
- Replayable task corpus pipeline: rev-range discovery, materialization, schema-aligned task bundles, repo-managed install configs, and harbor-backed per-task Docker harness for real-repo evaluation ([30d26fe], [0d3cdd4], [5a8763e], [29f4bea], [0ff45d1], [5ef34df])
- `stet eval` validation pipeline with AI-powered offline scoring, equivalence obligations, gate pipeline, and footprint-risk classification ([ab4471a], [3cc728e], [d4b65b0])
- Canonical `eval_report.v1.json` trial result and HTML report rendered alongside it as a sibling artifact (STET-244) ([7685e31], [c59037f])
- Custom YAML rubric graders, scored rubrics on a 0-4 scale (and float-scored 0.0-4.0), compare-gate lifecycle, and `stet eval calibrate` for adversarial rubric calibration ([786cbdd], [b742af7], [d4d0c4d], [1feb8ee], [066e700])
- Head-to-head (h2h) flow with native cutover, instruction treatments, frozen-baseline compare, suite-driven runs, eval-rules skill loop, and capability release tracking via `stet eval batch-grade` (STET-187, STET-166) ([d4b65b0], [2389f34], [c057f69], [1525697], [79773c1], [f3e243b])
- Stet skill packaged in dist and made install-first-class, with hypothesis-driven iteration guidance, comparison workflows, baseline-freeze teaching, and stet-cli (`benredmond/stet-cli`) as the public distribution channel ([ce5840a], [9e004ae], [15d6d7a], [4fa2394], [723a8f6], [a7706a4])
- Leaderboard Next.js frontend with model comparisons, blog posts (Opus 4.7 vs 4.6 Zod), inspect evidence preview, and editorial copy ([280efb6], [d7eb93c], [4033439])
- Reasoning-effort eval arms and Claude Opus 4.7 support with priced model registration ([7ed6f77], [3daf2cb], [feb6691])
- `stet monitor status` and `stet monitor run` for scheduled regression detection (STET-176, STET-178) ([086b59b], [932d07f])
- Workbench mutation-command gating and risk surfacing for the candidate iteration loop (STET-171) ([b14df5f], [bbe1764])

### Changed
- Rename project from Flux to Stet across the codebase, CLI surface, dist artifacts, and public copy ([160c91b])
- Make decision-quality graders the default for `stet eval rules` ([77cde43])
- Gate commercial Stet workflows by entitlement ([9bcf523])
- Reorient the Stet skill to be optimizer-facing (agent-first) ([4e317f6])

### Fixed
- Numerous harness, gate-parsing, grader, leaderboard, baseline, and credential fixes accumulated over the v0.1.0 rcs (auth scoping, OAuth, Harbor harness install skew, smoke preflight, grader repair retry, baseline subset filtering, h2h credential env leaks, decision report wiring)

### Internal
- Migrate task plans into `apex/tasks/` domain layout, add the dist skill mirror sync flow, repo-managed pre-commit hooks, and the QMD-backed task corpus ([af6b5d9], [7c7b197])
- Cache Harbor harness CLI setup, expire stale caches, and rename `tb` args to `harbor` args during the harbor cutover ([915d87a], [e2dfc3a], [af91737])

[v0.1.0]: https://github.com/benredmond/stet/releases/tag/v0.1.0
[30d26fe]: https://github.com/benredmond/stet/commit/30d26fecf816abf5497511b4cd2bb282cc652174
[0d3cdd4]: https://github.com/benredmond/stet/commit/0d3cdd42a58bfeffec51b9ffb8a8e77c379a003d
[5a8763e]: https://github.com/benredmond/stet/commit/5a8763e074ea98ec97662f4bfda6dced8be6406d
[29f4bea]: https://github.com/benredmond/stet/commit/29f4bea3b77f508d3eb3279d636b27d0d9aaee22
[ab4471a]: https://github.com/benredmond/stet/commit/ab4471a056ec272425cde1509079305a19135d4b
[3cc728e]: https://github.com/benredmond/stet/commit/3cc728e5f2ed09d31d32ebdf500b1c0dfc6866c2
[d4b65b0]: https://github.com/benredmond/stet/commit/d4b65b0d21de68331104acd6fa3b15e8e055133e
[160c91b]: https://github.com/benredmond/stet/commit/160c91bf740f37c4b7f6dae256d71fc08b68dc3b
[5ef34df]: https://github.com/benredmond/stet/commit/5ef34dfea318c851c2ca55b0fe1410dfe5bcbf55
[af6b5d9]: https://github.com/benredmond/stet/commit/af6b5d927695a51c0436d7e6abbf867fffe2d5db
[7c7b197]: https://github.com/benredmond/stet/commit/7c7b197478ab138cb6ecc3032146d0662ec8b34c
[2389f34]: https://github.com/benredmond/stet/commit/2389f34cc2a209443f07d45df21564244b0a9550
[c057f69]: https://github.com/benredmond/stet/commit/c057f691a28d886c14bd7e9abf4ba446b5c11d3c
[1525697]: https://github.com/benredmond/stet/commit/1525697678e53d1d2f22d4bbf24c465f07faccff
[79773c1]: https://github.com/benredmond/stet/commit/79773c1048d8871780108bba0b20efaf34c348a9
[7685e31]: https://github.com/benredmond/stet/commit/7685e3131f41499f5d78234890a4db56a04deea8
[c59037f]: https://github.com/benredmond/stet/commit/c59037fab783bca45a2df442f9c13f1e24401b95
[786cbdd]: https://github.com/benredmond/stet/commit/786cbdd555118915aa352e2341ff0b88e207f6e7
[b742af7]: https://github.com/benredmond/stet/commit/b742af789b65ccfe90c9739fffcc1405e23735dc
[d4d0c4d]: https://github.com/benredmond/stet/commit/d4d0c4dbb877fec14c578d2761aef96e0ab83554
[1feb8ee]: https://github.com/benredmond/stet/commit/1feb8eea6f7fa92709961d8625e490101b631d53
[066e700]: https://github.com/benredmond/stet/commit/066e700bbe6afc5f644604ca287ba29c933fab7d
[f3e243b]: https://github.com/benredmond/stet/commit/f3e243b5a8d325ce6d9a7f031c2c6d8e913c3e2d
[e7eef57]: https://github.com/benredmond/stet/commit/e7eef571f395a53aba8d38b81d04b7bfceb414da
[8047f55]: https://github.com/benredmond/stet/commit/8047f55ba8c4db60b5023dbc05101ae49d4b72ed
[7f7dcef]: https://github.com/benredmond/stet/commit/7f7dcef0d83caf0f53f9a2eb093aa8387595a330
[11c8b74]: https://github.com/benredmond/stet/commit/11c8b747ed41f0bcf8484adbadd8d9b615c7facc
[c3a26a4]: https://github.com/benredmond/stet/commit/c3a26a42f2da542f8fc41837296104efed018451
[8fbd054]: https://github.com/benredmond/stet/commit/8fbd05424a130a08b3c75b4c5b32036b3d18c9e5
[251f33d]: https://github.com/benredmond/stet/commit/251f33dd3950e367d7925489aff799bc51083603
[086b59b]: https://github.com/benredmond/stet/commit/086b59b346fa837caa2519f8f1aa3b1f93c50dec
[932d07f]: https://github.com/benredmond/stet/commit/932d07fe688e289344693d68f78e3ff55fbbb81b
[bbe1764]: https://github.com/benredmond/stet/commit/bbe17644b6444ea2f61d53b86cf2e7f91900ea84
[7ed6f77]: https://github.com/benredmond/stet/commit/7ed6f7767ba5bd3c32747fb576b372825a22987f
[3daf2cb]: https://github.com/benredmond/stet/commit/3daf2cb06568d92d23ebe8d3254a2deea16ea923
[feb6691]: https://github.com/benredmond/stet/commit/feb6691eb9ab01c97e050fd45412ab096551d825
[915d87a]: https://github.com/benredmond/stet/commit/915d87aafb3889074bf2220374d23384417f4d93
[e2dfc3a]: https://github.com/benredmond/stet/commit/e2dfc3a24d6b8421f5a1a04ef49af4bb96605728
[af91737]: https://github.com/benredmond/stet/commit/af9173746337f75d486897dc26f9f72d93562686
[ce5840a]: https://github.com/benredmond/stet/commit/ce5840ab8d87bd1d6406e3d2523c0bdc01d9aa3d
[9e004ae]: https://github.com/benredmond/stet/commit/9e004aec3b4a01575d96301a03758ce0d0b35e72
[15d6d7a]: https://github.com/benredmond/stet/commit/15d6d7acf7190c0f3fa45cefec24974b3aabd36e
[4fa2394]: https://github.com/benredmond/stet/commit/4fa2394894f43976d86f4d95c2fe1d1c67f64802
[723a8f6]: https://github.com/benredmond/stet/commit/723a8f6ddf18c706fc86ab5cc5b8e44d02331b2a
[a7706a4]: https://github.com/benredmond/stet/commit/a7706a4a230356cbbc46b584b723164d50afff8e
[280efb6]: https://github.com/benredmond/stet/commit/280efb68dd0bcb7be8bb96e07f3932ddca288757
[d7eb93c]: https://github.com/benredmond/stet/commit/d7eb93c7eb01b3e4afedf422ad42522f273b87a3
[4033439]: https://github.com/benredmond/stet/commit/40334398a97f238e07af457dca28ac8ce8e20ebd
[0ff45d1]: https://github.com/benredmond/stet/commit/0ff45d1daf08837f706e5c5c82d151e48f88f5bc
[9bcf523]: https://github.com/benredmond/stet/commit/9bcf523503fd9678622ea985bc11fe71fe377e2f
[4e317f6]: https://github.com/benredmond/stet/commit/4e317f66e586aea2233fca44f7034921731c332a
[77cde43]: https://github.com/benredmond/stet/commit/77cde4366cdd784221a1c9bc9eb3b1ca0b8de029
[b14df5f]: https://github.com/benredmond/stet/commit/b14df5fc2b1f3363c40743c539080c946dcd4b76
