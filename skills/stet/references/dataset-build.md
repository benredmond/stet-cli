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
| `## Config Draft` with Harbor Dockerfile + harness manifest | Phase 2 |
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

Goal: produce a working `.stet/harbor.Dockerfile` plus
`.stet/stet.harness.yaml` by mining the repo's own CI and build files.

Launch 3 parallel subagents:

1. **CI Miner**: Read `.github/workflows/*.yml`. Extract install steps, test
   commands, runtime versions, env vars, services, conditional logic.
2. **Ecosystem Analyzer**: Read package manager configs. Extract language,
   package manager, dependency groups, workspace structure, native deps.
3. **Docs Reader**: Read README, CONTRIBUTING, DEVELOPMENT docs. Extract
   setup instructions, test commands, gotchas, system deps.

Synthesize into:
- `.stet/harbor.Dockerfile` — repo-specific Harbor environment
- `.stet/stet.harness.yaml` — points `environment.dockerfile` at that file
- `stet init --test "<repo test cmd>"` — persist the canonical test command

**The test command must run the repo's actual test suite, not a smoke test.**
Priority: CI workflow > Makefile target > package.json script > README.

Proactive gotcha handling:

| Issue | Prevention |
|---|---|
| Missing system tools | Install them in the Harbor Dockerfile |
| Wrong Node/Python version | Pin to CI matrix version in the Dockerfile |
| Package manager network flakes | Add retry config in the Dockerfile |
| Repo expects setup steps before tests | Encode them in the Dockerfile, keep `stet init --test` focused on test execution |

Minimal harness contract:

```yaml
version: 1
schema: stet.harness/v1
runner:
  tb_cmd:
    - harbor
environment:
  dockerfile: .stet/harbor.Dockerfile
```

If Harbor needs larger pods, keep the same Dockerfile and add Harbor resource
overrides under `runner.tb_args`:

```yaml
runner:
  tb_cmd:
    - harbor
  tb_args:
    - --override-memory-mb
    - "8192"
    - --override-cpus
    - "2"
```

Use this for `ENOMEM` / OOMKilled failures during agent setup, including
Claude Code installation. Prefer `8192` MB first, then `16384` MB if the
install still OOMs. For compare-backed Claude Code runs, also lower
`--tb-concurrency` to `2` when Stet reports
`harbor_claude_code_concurrent_setup_cache_skew`; Docker layer cache reuse can
make the second arm start installer-heavy containers more synchronously than
the first.

Suite-backed rules runs automatically apply `.stet/stet.harness.yaml` when it
exists. Use `eval.harness` in `stet.suite.yaml` only for a non-default harness
manifest (scalar path or `manifest:` object). Do not add `runner:` to
`stet.yaml`; runner settings live in `stet.harness/v1`.

**CHECKPOINT: Show the drafted Harbor Dockerfile, harness manifest, and test command with CI references. Proceed on approval.**

## Phase 2: Iterate to Green

Goal: >= 80% gold pass rate on a smoke batch.

```bash
stet init --repo /path/to/local/repo --yes --test "<repo test cmd>"

stet suite discover --repo owner/repo --rev-range main~30..main --limit 10 \
  --output $MANIFEST_DIR/manifest.yaml

stet suite build --repo /path/to/local/repo --manifest $MANIFEST_DIR/manifest.yaml \
  --out $OUT --workers 2 --require-f2p=false
```

Debug loop (up to 5 attempts). Ordered by frequency:

| Failure pattern | Classification | Fix |
|---|---|---|
| `command not found: make/cmake/gcc` | missing_binary | Add `apt-get install -y {binary}` to `.stet/harbor.Dockerfile` |
| `No such file: python3.X` / `node: not found` | wrong_runtime | Change runtime/toolchain in `.stet/harbor.Dockerfile` |
| `Timeout` / `exceeded time limit` | timeout | Keep the same test command; fix setup/runtime in the Dockerfile first |
| `ModuleNotFoundError` / `Cannot find module` | import_error | Add the missing dependency install to `.stet/harbor.Dockerfile` |
| `ConnectionError` / `fetch failed` | network_flake | Add retry config / package manager setup to the Dockerfile |
| `ENOENT` from setup hacks on old commits | path_drift | Simplify the Dockerfile; avoid commit-fragile file mutations when possible |
| vitest/jest per-test timeout | test_config | Prefer durable repo/env setup; patch configs only if CI already does something similar |
| `ENOMEM` / OOM killed | resource_limit | Increase Harbor memory with `runner.tb_args` / `--tb-arg "--override-memory-mb 8192"`; reduce `--workers` or `--tb-concurrency` if several pods exhaust the node |
| Docker daemon errors | infra_error | Check `docker ps`, kill zombies, retry |
| Lockfile version mismatch | lockfile_drift | Pin package manager version in `.stet/harbor.Dockerfile` |

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
| Repeated package-download flake | Harden the Harbor Dockerfile with retries / mirrors |
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

## Harbor Dockerfile Starting Points

Use these as starting points; pin versions from CI and keep the actual repo
test command in `stet init --test`.

### Python (uv)
```dockerfile
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
RUN apt-get update -qq && apt-get install -y -qq git make curl && rm -rf /var/lib/apt/lists/*
# install Python/uv version that matches CI here
WORKDIR /app
ADD repo.tar.gz /app
RUN uv sync --frozen --all-packages
```

### Node / pnpm
```dockerfile
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
RUN apt-get update -qq && apt-get install -y -qq git curl && rm -rf /var/lib/apt/lists/*
# install Node + pnpm versions that match CI here
WORKDIR /app
ADD repo.tar.gz /app
RUN pnpm install --frozen-lockfile
```

### Go
```dockerfile
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
RUN apt-get update -qq && apt-get install -y -qq git curl build-essential && rm -rf /var/lib/apt/lists/*
# install Go version that matches CI here
WORKDIR /app
ADD repo.tar.gz /app
RUN go mod download
```

### TypeScript (pnpm)
```dockerfile
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
RUN apt-get update -qq && apt-get install -y -qq git curl && rm -rf /var/lib/apt/lists/*
# install Node + corepack/pnpm versions that match CI here
WORKDIR /app
ADD repo.tar.gz /app
RUN corepack enable && corepack prepare pnpm@latest --activate
RUN pnpm install --frozen-lockfile --prefer-offline
```

### TypeScript (npm)
```dockerfile
FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624
RUN apt-get update -qq && apt-get install -y -qq git curl && rm -rf /var/lib/apt/lists/*
# install Node version that matches CI here
WORKDIR /app
ADD repo.tar.gz /app
RUN npm ci
```
