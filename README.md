# Stet Binary Distribution

This private repository distributes Stet CLI binaries and the Stet agent skill for MVP users. It does not contain Stet source code. Users need read access to this repository, but they do not need access to the private Stet source repository.

Homebrew and `go install` are intentionally not used for MVP Stet distribution. Install Stet from the binary release assets in this private repository.

## Setup Stet

When a human says "go to `stet-dist` and set up Stet", follow these steps. Ask before making system-level changes such as installing Docker, changing shell profile files, or adding the user to the `docker` group.

### 1. Verify GitHub Access

Install and authenticate the GitHub CLI if needed:

```sh
gh auth status || gh auth login
gh repo view benredmond/stet-dist --json visibility,url
```

The user must have read access to `benredmond/stet-dist`.

### 2. Install Stet

Install the latest stable Stet binary release:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh
```

Install a specific version or release candidate:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --version v0.1.0
```

The default install directory is `$HOME/.local/bin`. If that is not on `PATH`, either add it to `PATH` or install into an existing user-writable bin directory:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --bin-dir "$HOME/bin"
```

Verify the binary:

```sh
stet --version
```

`stet --version` should print the Stet version, source commit, and build date.

### 3. Install The Stet Agent Skill

The repo includes the Stet skill under `skills/stet`, following the Agent Skills `SKILL.md` directory format. Install it with the `npx skills` CLI:

```sh
npx skills add git@github.com:benredmond/stet-dist.git --skill stet
```

To install globally for Codex:

```sh
npx skills add git@github.com:benredmond/stet-dist.git --skill stet --global --agent codex --yes
```

To inspect the skill before installing:

```sh
npx skills add git@github.com:benredmond/stet-dist.git --list
```

If your environment has HTTPS git credentials configured for private GitHub repos, the GitHub shorthand also works:

```sh
npx skills add benredmond/stet-dist --skill stet
```

### 4. Install Docker

Stet uses Docker-backed task environments for validation and benchmark runs. First check whether Docker is already installed and running:

```sh
docker info
```

On macOS, install Docker Desktop if Docker is missing:

```sh
brew install --cask docker
open -a Docker
```

Wait until Docker Desktop finishes starting, then rerun:

```sh
docker info
```

On Ubuntu Linux, install Docker Engine from Docker's official apt repository:

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo docker run hello-world
```

If the user wants to run Docker without `sudo`, add them to the `docker` group and start a new login shell:

```sh
sudo usermod -aG docker "$USER"
```

### 5. Install Harbor

Stet's default harness command is Harbor. Harbor requires Python 3.12+ and Docker.

Install `uv` if it is missing:

```sh
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install Harbor:

```sh
uv tool install harbor
harbor --version
```

If `harbor` is not found after install, add the `uv` tool bin directory to `PATH`. On many systems this is `$HOME/.local/bin`.

### 6. Final Setup Check

Run these checks and fix any failure before starting real Stet work:

```sh
gh auth status
stet --version
npx skills list
docker info
harbor --version
```

If you plan to run Claude Code models, authenticate Claude Code on the host
before running Stet. The preferred setup for non-interactive Stet runs is a
Claude OAuth token:

```sh
claude setup-token
export CLAUDE_CODE_OAUTH_TOKEN=<printed token>
```

Stet's installer places its Harbor auth bridge under
`$HOME/.local/share/stet/harbor-agents`. Stet also accepts
`CLAUDE_CODE_CREDENTIALS_JSON_B64`, `CLAUDE_CODE_CREDENTIALS_JSON`,
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, or the macOS Keychain item named
`Claude Code-credentials`. If Claude is selected and none of those are present,
Stet fails before launching the run.

If a Harbor run still prints that Claude needs `/login`, first rerun the Stet
installer for the current version so the Harbor auth bridge is present, then
rerun the auth setup above.

Optional, but useful when the user approves downloading benchmark tasks and containers:

```sh
harbor run -d terminal-bench@2.0 -a oracle -n 1
```

## Update And Roll Back

Install the latest stable release:

```sh
stet update
```

Pin or roll back to an exact version:

```sh
stet update --version v0.1.0
```

Use a custom install directory when needed:

```sh
stet update --bin-dir "$HOME/.local/bin"
```

`stet update` and `install.sh` verify `checksums.txt` before replacing the local binary. They also refresh Stet's local Harbor support agents under `$HOME/.local/share/stet/harbor-agents`. Updates are pull-based only; Stet does not perform background or silent auto-updates.

## Troubleshooting

If installation cannot read releases, verify GitHub authentication and repository access:

```sh
gh auth status
gh repo view benredmond/stet-dist
```

If `stet` is not found after install, add the install directory to `PATH`.

If Docker is installed but unavailable, start Docker Desktop on macOS or the Docker service on Linux, then rerun `docker info`.

If Harbor is not found after install, add the `uv` tool bin directory to `PATH` and rerun `harbor --version`.

If Claude Code runs fail with missing-auth guidance, run `claude setup-token`,
export `CLAUDE_CODE_OAUTH_TOKEN`, and rerun Stet. For container-backed Stet
runs, Stet can also use Claude credential JSON env vars, Anthropic API/auth
token env vars, or the macOS Keychain item named `Claude Code-credentials`.

If no stable Stet release exists yet, install or update to an explicit prerelease version:

```sh
stet update --version v0.1.0-rc.3
```
