# Dataset Build (Heavy)

Inherits [operator-contract](operator-contract.md) for receipt format and
shared keyed actions.

Use this when the quick onboarding path is insufficient — need 50+ tasks,
complex CI, Docker debug loops, or multi-batch scaling.

```
pre-screen ──► understand + draft ──► iterate to green ──► scale + audit
     │                │                      │                    │
   VIABLE?        CI miner              ≥80% gold?          target count?
   └─ no: stop    ecosystem             └─ no: debug loop    └─ no: expand
                   docs reader           (up to 5×)           (batch discover)
```

## Pipeline Overview

```
discover (fetch PRs -> prefilter -> LLM scoring -> manifest)
  -> build (snapshots -> gold/F2P tests -> task dirs)
    -> harbor run -> validate
```

`discover` is cheap (no Docker). `build` is expensive (Docker containers).

## Resumability

The task .md IS the state. On resume, read it to determine current phase:

| .md contains | Resume from |
|---|---|
| Nothing / just frontmatter | Phase 0 |
| `## Pre-screen` filled | Phase 1 |
| `## Config Draft` with install_config | Phase 2 |
| `## Iteration Log` with gold_pass >= 80% | Phase 3 |
| `## Build Log` with cumulative count >= target | Done — run audit checks |

## Phase 0: Pre-screen

Fast reject before investing time.

Checks:
1. **PR depth**: >= 500 merged PRs
2. **Recent activity**: PRs merged in last 6 months
3. **License**: Permissive (MIT, Apache 2.0, BSD)
4. **Test suite exists**: `tests/`, `test/`, `__tests__/`, `*_test.go`
5. **CI exists**: `.github/workflows/` with test-related workflows
6. **CI is green**: `gh run list --repo {owner}/{repo} --limit 5`
7. **Language supported**: Python, TypeScript/JavaScript, or Go

Run a discover probe to measure pipeline yield:

```bash
# Narrow probe
stet suite discover --repo owner/repo --rev-range main~100..main --limit 50 \
  --min-complexity 3 --json --output $SCRATCH/prescreen-manifest.yaml

# Widen if 0 PASS
stet suite discover --repo owner/repo --rev-range main~500..main --limit 200 \
  --min-complexity 3 --json --output $SCRATCH/prescreen-manifest-wide.yaml

# Deep scan if still 0 PASS
stet suite discover --repo owner/repo --source commits --rev-range main~2000..main \
  --limit 500 --target-pass 5 --min-complexity 2 --json \
  --output $SCRATCH/prescreen-manifest-deep.yaml
```

Yield interpretation:
- >= 5% yield: VIABLE
- 1-4% on deep only: MARGINAL
- 0% on all probes: NOT VIABLE

**CHECKPOINT: Report verdict to user. Proceed to Phase 1 on approval.**

## Phase 1: Understand + Draft

Goal: produce a working `install_config.sh` and `allowlist.json` by mining
the repo's own CI and build files.

Launch 3 parallel subagents:

1. **CI Miner**: Read `.github/workflows/*.yml`. Extract install steps, test
   commands, runtime versions, env vars, services, conditional logic.
2. **Ecosystem Analyzer**: Read package manager configs. Extract language,
   package manager, dependency groups, workspace structure, native deps.
3. **Docs Reader**: Read README, CONTRIBUTING, DEVELOPMENT docs. Extract
   setup instructions, test commands, gotchas, system deps.

Synthesize into:
- `scripts/{repo}-install-config.sh` (deterministic JSON output)
- `scripts/{repo}-install-allowlist.json` (prefix allowlist)

**test_cmd must run the repo's actual test suite, not a smoke test.** Priority:
CI workflow > Makefile target > package.json script > README.

Proactive gotcha handling:

| Issue | Prevention |
|---|---|
| Shell operators in commands | Separate array entries |
| `sed` on files missing in old commits | `find . -name <file> -exec sed ... {} +` |
| Package manager network flakes | Retry config, reduce concurrency |
| Wrong Node/Python version | Pin to CI matrix version |

**CHECKPOINT: Show user the draft config + CI references. Proceed on approval.**

## Phase 2: Iterate to Green

Goal: >= 80% gold pass rate on a smoke batch.

```bash
stet suite discover --repo owner/repo --rev-range main~30..main --limit 10 \
  --output $MANIFEST_DIR/manifest.yaml

stet suite build --repo /path/to/local/repo --manifest $MANIFEST_DIR/manifest.yaml \
  --out $OUT --workers 2 --require-f2p=false --llm-install-config \
  --max-recipe-attempts 1 --install-allowlist scripts/{repo}-install-allowlist.json \
  --ai-cmd scripts/{repo}-install-config.sh
```

Debug loop (up to 5 attempts). Ordered by frequency:

| Failure pattern | Classification | Fix |
|---|---|---|
| `command not found: make/cmake/gcc` | missing_binary | Add `apt-get install -y {binary}` to pre_install |
| `No such file: python3.X` / `node: not found` | wrong_runtime | Change runtime_version to CI matrix |
| `Timeout` / `exceeded time limit` | timeout | Increase test_sec; add `-x` to test runner |
| `ModuleNotFoundError` / `Cannot find module` | import_error | Add missing dep to install commands |
| `ConnectionError` / `fetch failed` | network_flake | Add retry config, reduce concurrency |
| `ENOENT` from sed on old commits | path_drift | Use `find . -name <file> -exec sed ... {} +` |
| vitest/jest per-test timeout | test_config | Patch config: `sed -i 's/test: {/test: { testTimeout: 30000,/'` |
| `ENOMEM` / OOM killed | resource_limit | Reduce `--workers` to 1; reduce test parallelism |
| Docker daemon errors | infra_error | Check `docker ps`, kill zombies, retry |
| Lockfile version mismatch | lockfile_drift | Pin package manager version in pre_install |

After >= 80% gold pass, verify test_cmd relevance: pick a task with test
patch, confirm test_cmd runs those files.

**CHECKPOINT: Report iteration results. Proceed to scale on approval.**

## Phase 3: Scale + Audit

Discover in large batches using non-overlapping rev-ranges. Discover is cheap
(no Docker) — launch parallel discover batches on different ranges.

```bash
# Parallel discover
stet suite discover --rev-range main~200..main --limit 200 --output manifest-batch1.yaml
stet suite discover --rev-range main~400..main~200 --limit 200 --output manifest-batch2.yaml

# Sequential build (Docker is the bottleneck)
stet suite build --manifest manifest-batch1.yaml --out $OUT --workers 2 ...
stet suite build --manifest manifest-batch2.yaml --out $OUT --workers 2 ...
```

Course correction:

| Signal | Action |
|---|---|
| 429 rate limit | Switch `--ai-cmd` |
| Gold pass < 50% | Toolchain drift — fix config or stop |
| Discover pass < 15% | Diminishing returns |
| Docker errors | Kill zombies, reduce workers |

Stop expanding if 3 consecutive batches yield < 5 new tasks.

Inline audit at target count:
1. Empty test patches -> flag for removal
2. Lockfile/CI-only artifacts -> flag
3. Patch size: reject < 80 lines or > 1500 lines
4. Non-test file ratio: flag > 80% test files
5. Spot-check ai_task quality

Update `agent_docs/datasets.md` with the finalized recipe.

## Flow-Specific Actions

Each phase checkpoint maps to keyed actions:

- `[a] approve`: proceed to next phase after reviewing checkpoint results
- `[r] rerun`: retry the current phase after a config or toolchain fix
- `[s] stop`: halt the pipeline at the current phase

## Ecosystem Templates

Use as starting skeleton. Override test_cmd and runtime_version from CI.

### Python (uv)
```json
{
  "language": "python", "runtime_version": "3.12",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git make"],
  "install": ["uv sync --frozen --all-packages"],
  "test_cmd": ["uv run pytest tests/ -x -q --timeout=60"],
  "timeouts": {"install_sec": 600, "test_sec": 1800}
}
```

### Python (poetry)
```json
{
  "language": "python", "runtime_version": "3.12",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git make",
    "pip install poetry"],
  "install": ["poetry install --no-interaction"],
  "test_cmd": ["poetry run pytest tests/ -x -q --timeout=60"],
  "timeouts": {"install_sec": 600, "test_sec": 1800}
}
```

### Python (pip)
```json
{
  "language": "python", "runtime_version": "3.12",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git make"],
  "install": ["pip install -e '.[dev,test]'"],
  "test_cmd": ["python -m pytest tests/ -x -q --timeout=60"],
  "timeouts": {"install_sec": 600, "test_sec": 1800}
}
```

### TypeScript (pnpm)
```json
{
  "language": "typescript", "runtime_version": "20",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git",
    "corepack enable", "corepack prepare pnpm@latest --activate"],
  "install": ["pnpm install --frozen-lockfile --prefer-offline", "pnpm run build"],
  "test_cmd": ["pnpm test"],
  "timeouts": {"install_sec": 600, "test_sec": 1800}
}
```

### TypeScript (npm)
```json
{
  "language": "typescript", "runtime_version": "20",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git"],
  "install": ["npm ci", "npm run build"],
  "test_cmd": ["npm test"],
  "timeouts": {"install_sec": 600, "test_sec": 1800}
}
```

### Go
```json
{
  "language": "go", "runtime_version": "1.24",
  "pre_install": ["apt-get update -qq", "apt-get install -y -qq git make"],
  "install": ["go mod download"],
  "test_cmd": ["go test ./... -count=1 -timeout=300s"],
  "env_vars": {"CGO_ENABLED": "0"},
  "timeouts": {"install_sec": 300, "test_sec": 1800}
}
```
