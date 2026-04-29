# Stet CLI

Stet is change control for AI coding behavior. It replays real repo work and scores the output so you can safely ship model, config, and skill changes.

Stet is installed in two parts:

- the `stet` CLI, which runs evaluations and manages artifacts
- the Stet agent skill, which teaches your agent which Stet workflow to use and how to interpret the evidence

For agent-driven use, install both. The CLI gives the agent the tool; the skill gives it the operating contract required to use Stet correctly.

## What you can ask your agent

Once the CLI and the `stet` skill are installed, you can drive evaluations in natural language. A few examples:

- "Is Opus 4.6 or 4.7 better on my codebase, and on which dimensions?" — runs a head-to-head across replayed tasks and reports per-dimension deltas (correctness, code review, footprint, equivalence).
- "Make my `CLAUDE.md` better." — proposes edits, then evaluates the new version against the current one on real tasks before recommending the change.
- "Does this skill actually help? If so, make it better." — A/B tests the skill on/off, then iterates on the skill and re-evaluates until it wins.
- "Has my agent's performance regressed since last week?" — reruns the frozen baseline and flags per-dimension regressions.
- "Which of my skills are pulling their weight, and which should I delete?" — evaluates each skill's marginal contribution across the corpus.
- "Score this PR's diff against our quality rubric before I merge." — runs the evaluator on a single change as a pre-merge gate.

The agent picks the right Stet surface (quick probe, full eval, baseline rerun) based on the question. See `skills/stet/SKILL.md` for the full contract.

## Requirements

- macOS or Linux (x86\_64 or arm64)
- [GitHub CLI](https://cli.github.com/) authenticated with access to this repo
- Node.js / `npx` for installing the Stet agent skill
- Docker ([Desktop](https://www.docker.com/products/docker-desktop/) on macOS, [Engine](https://docs.docker.com/engine/install/) on Linux)
- Python 3.12+

## Setup

### 1. Verify GitHub access

```sh
gh auth status || gh auth login
gh repo view benredmond/stet-dist --json visibility,url
```

### 2. Install the Stet CLI

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh
```

Install a specific version:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --version v0.1.0
```

The default install directory is `$HOME/.local/bin`. To use a different directory:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --bin-dir "$HOME/bin"
```

Verify:

```sh
stet --version
```

### 3. Install the Stet agent skill

This is a first-class part of setup, not an optional add-on. Agents need the skill to route questions to the right Stet surface, preserve decision semantics, read canonical artifacts, and avoid treating directional checks as rollout evidence.

```sh
npx skills add git@github.com:benredmond/stet-dist.git --skill stet
```

To inspect the skill before installing:

```sh
npx skills add git@github.com:benredmond/stet-dist.git --list
```

If your environment has HTTPS git credentials configured for GitHub, the shorthand also works:

```sh
npx skills add benredmond/stet-dist --skill stet
```

If your agent supports separate project-level and global skill installs, prefer the install scope that the agent will actually load during Stet work. Verify the skill is visible before running evaluations:

```sh
npx skills list
```

### 4. Install Docker

Check whether Docker is already running:

```sh
docker info
```

On macOS, install Docker Desktop if missing:

```sh
brew install --cask docker
open -a Docker
```

On Ubuntu Linux:

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

To run Docker without `sudo`, add yourself to the `docker` group and start a new login shell:

```sh
sudo usermod -aG docker "$USER"
```

### 5. Install Harbor

Harbor is Stet's default harness. It requires Python 3.12+ and Docker.

```sh
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install harbor
harbor --version
```

If `harbor` is not found after install, add the `uv` tool bin directory to `PATH` (usually `$HOME/.local/bin`).

### 6. Final check

```sh
gh auth status
stet --version
npx skills list
docker info
harbor --version
```

If you plan to run Claude Code models, authenticate before running Stet:

```sh
claude setup-token
mkdir -p ~/.config/stet
chmod 700 ~/.config/stet
printf '%s\n' '<printed token>' > ~/.config/stet/claude-oauth-token
chmod 600 ~/.config/stet/claude-oauth-token
unset CLAUDE_CODE_OAUTH_TOKEN
```

Stet reads `~/.config/stet/claude-oauth-token` and forwards
`CLAUDE_CODE_OAUTH_TOKEN` only to Stet-managed Claude runs. Do not put the token
in `.zshrc`, `.zprofile`, repo `.env` files, or committed config. For one-off
automation where a file is not appropriate, scope the variable to the command:
`CLAUDE_CODE_OAUTH_TOKEN=<token> stet ...`.

Stet also accepts `CLAUDE_CODE_CREDENTIALS_JSON_B64`, `CLAUDE_CODE_CREDENTIALS_JSON`, `ANTHROPIC_API_KEY`, or `ANTHROPIC_AUTH_TOKEN`. Stet does not read Claude credentials from the macOS Keychain by default. If Claude is selected and none are present, Stet fails before launching the run.

## Update and roll back

```sh
stet update                        # latest stable
stet update --prerelease           # latest release candidate
stet update --version v0.1.0       # pin or roll back
```

`stet update` verifies checksums and refreshes local Harbor support agents. Updates are pull-based only; Stet does not auto-update.

## Troubleshooting

**`stet` not found after install** — add the install directory to `PATH`.

**GitHub auth or access errors** — run `gh auth status` and verify repo access with `gh repo view benredmond/stet-dist`.

**Docker unavailable** — start Docker Desktop on macOS or the Docker service on Linux, then rerun `docker info`.

**Harbor not found** — add the `uv` tool bin directory to `PATH` and rerun `harbor --version`.

**Claude auth failures** — run `claude setup-token`, store the printed token in `~/.config/stet/claude-oauth-token` with `0600` permissions, and rerun Stet. Use command-scoped `CLAUDE_CODE_OAUTH_TOKEN=<token> stet ...` only for one-off automation.

**No stable release found** — install a prerelease: `stet update --prerelease` or `stet update --version v0.1.0-rc.3`.

## License

The install script and agent skill files in this repository are licensed under the [MIT License](LICENSE).

The Stet binary distributed via release assets is proprietary software. Use of the binary is governed by the [Stet Binary Terms](TERMS.md).
