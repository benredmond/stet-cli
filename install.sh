#!/bin/sh
set -eu

DEFAULT_REPO="${STET_DIST_REPO:-benredmond/stet-dist}"
DEFAULT_BIN_DIR="${STET_INSTALL_DIR:-$HOME/.local/bin}"

repo="$DEFAULT_REPO"
bin_dir="$DEFAULT_BIN_DIR"
version=""

die() {
  printf '%s\n' "stet install: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
usage: install.sh [--version <tag>] [--repo <owner/repo>] [--bin-dir <path>]

Install the latest stable Stet binary release from the private dist repo.
Use --version to pin or roll back to an exact release tag.
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --version)
      [ "$#" -ge 2 ] || die "--version requires a value"
      version="$2"
      shift 2
      ;;
    --repo)
      [ "$#" -ge 2 ] || die "--repo requires a value"
      repo="$2"
      shift 2
      ;;
    --bin-dir)
      [ "$#" -ge 2 ] || die "--bin-dir requires a value"
      bin_dir="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unexpected argument: $1"
      ;;
  esac
done

command -v gh >/dev/null 2>&1 || die "gh is required; run: gh auth login"
command -v tar >/dev/null 2>&1 || die "tar is required"

if command -v sha256sum >/dev/null 2>&1; then
  sha256_file() { sha256sum "$1" | awk '{print $1}'; }
elif command -v shasum >/dev/null 2>&1; then
  sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }
else
  die "sha256sum or shasum is required"
fi

case "$(uname -s)" in
  Darwin) os_name="Darwin" ;;
  Linux) os_name="Linux" ;;
  *) die "unsupported OS: $(uname -s)" ;;
esac

case "$(uname -m)" in
  arm64|aarch64)
    arch_name="arm64"
    ;;
  x86_64|amd64)
    arch_name="x86_64"
    ;;
  *)
    die "unsupported architecture: $(uname -m)"
    ;;
esac

case "$os_name/$arch_name" in
  Darwin/arm64|Darwin/x86_64|Linux/x86_64) ;;
  *) die "unsupported platform: $os_name/$arch_name" ;;
esac

asset_name="stet_${os_name}_${arch_name}.tar.gz"

if [ -z "$version" ]; then
  version="$(gh api "repos/$repo/releases" --jq '.[] | select((.draft | not) and (.prerelease | not)) | .tag_name' | sed -n '1p')"
  [ -n "$version" ] || die "no stable release found in $repo"
fi

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/stet-install.XXXXXX")"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT INT TERM

asset_url="$(gh api "repos/$repo/releases/tags/$version" --jq ".assets[] | select(.name == \"$asset_name\") | .url")"
[ -n "$asset_url" ] || die "release $version is missing $asset_name"
checksums_url="$(gh api "repos/$repo/releases/tags/$version" --jq '.assets[] | select(.name == "checksums.txt") | .url')"
[ -n "$checksums_url" ] || die "release $version is missing checksums.txt"

archive="$tmp_dir/$asset_name"
checksums="$tmp_dir/checksums.txt"

gh api "$asset_url" -H "Accept: application/octet-stream" > "$archive"
gh api "$checksums_url" -H "Accept: application/octet-stream" > "$checksums"

expected="$(awk -v name="$asset_name" '($2 == name || $2 == "*" name) { print $1; exit }' "$checksums")"
[ -n "$expected" ] || die "checksums.txt has no entry for $asset_name"
actual="$(sha256_file "$archive")"
[ "$actual" = "$expected" ] || die "checksum mismatch for $asset_name: expected $expected, got $actual"

member_list="$tmp_dir/members.txt"
tar -tzf "$archive" > "$member_list"
[ "$(wc -l < "$member_list" | tr -d ' ')" = "1" ] || die "archive must contain exactly one member named stet"
[ "$(cat "$member_list")" = "stet" ] || die "archive contains unsafe member: $(cat "$member_list")"

type_char="$(tar -tzvf "$archive" | awk 'NR == 1 { print substr($0, 1, 1) }')"
[ "$type_char" = "-" ] || die "archive member stet must be a regular file"

extract_dir="$tmp_dir/extract"
mkdir -p "$extract_dir"
tar -xzf "$archive" -C "$extract_dir"
[ ! -L "$extract_dir/stet" ] || die "archive member stet must not be a symlink"
[ -f "$extract_dir/stet" ] || die "archive member stet must be a regular file"
[ -x "$extract_dir/stet" ] || die "archive member stet must be executable"

support_root="$HOME/.local/share/stet/harbor-agents"
case "$support_root" in
  ""|"/"|"$HOME"|"$HOME/")
    die "unsafe Stet support install directory: $support_root"
    ;;
esac
support_tmp="$tmp_dir/harbor-agents"
mkdir -p "$support_tmp/stet_harbor_agents"

for support_file in \
  stet_harbor_agents/__init__.py \
  stet_harbor_agents/compat.py \
  stet_harbor_agents/claude_code_auth.py \
  stet_harbor_agents/codex_auth.py \
  stet_harbor_agents/install_cache.py \
  stet_harbor_agents/patch_capture.py \
  stet_harbor_agents/install-claude-code-auth.sh.j2
do
  support_dest="$support_tmp/$support_file"
  mkdir -p "$(dirname "$support_dest")"
  gh api "repos/$repo/contents/$support_file?ref=$version" --header "Accept: application/vnd.github.raw" > "$support_dest"
done

mkdir -p "$bin_dir"
bin_dir_abs="$(cd "$bin_dir" && pwd -P)"
target="$bin_dir_abs/stet"
if [ -L "$target" ]; then
  link_target="$(readlink "$target")"
  case "$link_target" in
    /*)
      resolved="$link_target"
      ;;
    *)
      resolved="$(cd "$(dirname "$target")" && cd "$(dirname "$link_target")" && pwd -P)/$(basename "$link_target")"
      ;;
  esac
  case "$resolved" in
    "$bin_dir_abs"/*) target="$resolved" ;;
    *) die "$target is a symlink outside $bin_dir_abs; rerun with --bin-dir pointing at the real install directory" ;;
  esac
fi

mkdir -p "$(dirname "$support_root")"
rm -rf "$support_root"
mv "$support_tmp" "$support_root"

tmp_target="$(mktemp "$bin_dir_abs/.stet-update.XXXXXX")"
cp "$extract_dir/stet" "$tmp_target"
chmod 0755 "$tmp_target"
mv -f "$tmp_target" "$target"

printf 'installed %s to %s\n' "$version" "$target"
