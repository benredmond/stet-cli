# Stet CLI

Stet is change control for AI coding behavior. It replays real work from your
repo and scores the output so you can decide whether a model, instruction file,
skill, or tool-policy change is safe to keep.

Stet is designed to be operated by your coding agent. Give these docs to Claude
Code, Codex, Cursor, or the agent you use day to day, then ask it to run the
setup and first repo onboarding for you.

Stet is installed in two parts:

- the `stet` CLI, which runs evaluations and manages artifacts
- the Stet agent skill, which teaches your agent which workflow to use and how
  to read the evidence

For beta use, install both. The CLI gives the agent the tool; the skill gives it
the operating contract.

## Start here

- New beta user: [BETA_QUICKSTART.md](BETA_QUICKSTART.md)
- Prompt examples: [PROMPT_COOKBOOK.md](PROMPT_COOKBOOK.md)
- How Stet works: [ONBOARDING.md](ONBOARDING.md)
- Problems during setup or a run: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

## What you can ask your agent

Once the CLI and the `stet` skill are installed, you can drive Stet in natural
language. For example:

- "Use the Stet skill to onboard this repo for Stet evals."
- "Use the Stet skill to check whether this `AGENTS.md` change is helping."
- "Use the Stet skill to compare these two models on my repo and tell me which
  one I should use."
- "Use the Stet skill to test whether this skill actually improves agent
  behavior."
- "Use the Stet skill to check the current Stet run and tell me whether it is running, stalled,
  repairable, or complete."
- "Use the Stet skill, and before recommending promotion, verify the evidence is
  decision-grade."

Your agent should choose the right Stet surface for the question. Quick probes
are useful for cheap directional reads. Manifest-backed rules runs are the
default for rollout decisions about `AGENTS.md`, `CLAUDE.md`, shared skills,
model changes, or harness policy.

## Requirements

- macOS or Linux, x86_64 or arm64
- Access to the beta CLI repo, `benredmond/stet-cli`
- [GitHub CLI](https://cli.github.com/) authenticated with that access
- Node.js and `npx` for installing the Stet agent skill
- Docker, either Docker Desktop on macOS or Docker Engine on Linux
- Python 3.12+
- A model-provider auth path for the agent you plan to evaluate

## Setup

### 1. Verify GitHub access

```sh
gh auth status || gh auth login
gh repo view benredmond/stet-cli --json visibility,url
```

### 2. Install the Stet CLI

The beta installer and release assets live in `benredmond/stet-cli`.

```sh
gh api repos/benredmond/stet-cli/contents/install.sh --header "Accept: application/vnd.github.raw" | sh
```

Install a specific version:

```sh
gh api repos/benredmond/stet-cli/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --version v0.1.0
```

The default install directory is `$HOME/.local/bin`. To use a different
directory:

```sh
gh api repos/benredmond/stet-cli/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --bin-dir "$HOME/bin"
```

Verify:

```sh
stet --version
```

### 3. Sign in to Stet

Commercial beta workflows require local Stet auth before eval execution starts.

```sh
stet auth login
stet auth status
```

### 4. Install the Stet agent skill

This is a first-class part of setup. Agents need the skill to route questions to
the right Stet workflow, preserve decision semantics, read canonical artifacts,
and avoid treating directional checks as rollout evidence.

```sh
npx skills add git@github.com:benredmond/stet-cli.git --skill stet
```

To inspect the available skills before installing:

```sh
npx skills add git@github.com:benredmond/stet-cli.git --list
```

Verify the skill is visible to the agent you will use for Stet work:

```sh
npx skills list
```

### 5. Install Docker

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

To run Docker without `sudo`, add yourself to the `docker` group and start a new
login shell:

```sh
sudo usermod -aG docker "$USER"
```

### 6. Install Harbor

Harbor is Stet's default harness. It requires Python 3.12+ and Docker.

```sh
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install harbor
harbor --version
```

If `harbor` is not found after install, add the `uv` tool bin directory to
`PATH`, usually `$HOME/.local/bin`.

### 7. Set up model-provider auth

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

Stet also accepts `CLAUDE_CODE_CREDENTIALS_JSON_B64`,
`CLAUDE_CODE_CREDENTIALS_JSON`, `ANTHROPIC_API_KEY`, or
`ANTHROPIC_AUTH_TOKEN`. Stet does not read Claude credentials from the macOS
Keychain by default. If Claude is selected and none are present, Stet fails
before launching the run.

### 8. Final setup check

```sh
gh auth status
stet --version
stet auth status
npx skills list
docker info
harbor --version
```

## First prompt

In the repo you want to onboard, ask your agent:

```text
Use the Stet skill. Onboard this repo for Stet evals. Read CI first, choose the real test command, create the Harbor setup, build a starter dataset, and stop with a receipt before launching expensive evals.
```

Your agent should:

1. Read CI and build files to choose the real repo-level test command.
2. Author `.stet/harbor.Dockerfile` and `.stet/stet.harness.yaml`.
3. Run `stet init`, `stet suite discover`, and `stet suite build`.
4. Return an onboarding receipt with the candidate-task funnel, selected starter
   slice, confidence, and recommended next step.

After that, use [PROMPT_COOKBOOK.md](PROMPT_COOKBOOK.md) to run a first smoke,
probe, model comparison, instruction rollout, or skill evaluation.

## Update and roll back

```sh
stet update                        # latest stable
stet update --prerelease           # latest release candidate
stet update --version v0.1.0       # pin or roll back
```

`stet update` verifies checksums and refreshes local Harbor support agents.
Updates are pull-based only. Stet does not auto-update.

## Troubleshooting

Start with [TROUBLESHOOTING.md](TROUBLESHOOTING.md). The fastest checks are:

```sh
gh auth status
stet auth status
docker info
harbor --version
```

If a rules run is already in progress or has partial evidence, check status
before relaunching:

```sh
stet eval status --change-manifest .stet/rules/stet.change.yaml --json
```

Use repair for incomplete rules evidence. Use `--restart` only when you
intentionally want to discard existing evidence.

## License

The install script and agent skill files in this repository are licensed under
the [MIT License](LICENSE).

The Stet binary distributed via release assets is proprietary software. Use of
the binary is governed by the [Stet Binary Terms](TERMS.md).
