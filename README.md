# Stet Binary Distribution

This private repository distributes Stet CLI binaries for MVP users. It does not contain Stet source code. You need read access to this repository, but you do not need access to the private source repository.

## Prerequisites

Install and authenticate the GitHub CLI:

```sh
gh auth login
```

Your GitHub account must have read access to `benredmond/stet-dist`.

## Install

Use `gh api` to fetch the installer from the private repository:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh
```

Install a specific version:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --version v0.1.0
```

The default install directory is `$HOME/.local/bin`. Use `--bin-dir` to choose a different directory:

```sh
gh api repos/benredmond/stet-dist/contents/install.sh --header "Accept: application/vnd.github.raw" | sh -s -- --bin-dir "$HOME/bin"
```

Make sure the install directory is on `PATH`.

## Update And Roll Back

Install the latest stable release:

```sh
stet update
```

Pin or roll back to an exact version:

```sh
stet update --version v0.1.0
```

Check the installed binary:

```sh
stet --version
```

`stet update` and `install.sh` verify `checksums.txt` before replacing the local binary. Updates are pull-based only; Stet does not perform background or silent auto-updates.

## Troubleshooting

If installation cannot read releases, run:

```sh
gh auth status
```

If the install directory is not writable, choose a user-writable directory:

```sh
stet update --bin-dir "$HOME/.local/bin"
```

If `stet` is not found after install, add the install directory to `PATH`.

Homebrew and `go install` are intentionally not used for MVP distribution. MVP users install binary release assets from this private distribution repository.
