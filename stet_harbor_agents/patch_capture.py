from __future__ import annotations

import asyncio
import fnmatch
import shlex
from pathlib import Path

from harbor.environments.base import BaseEnvironment
from harbor.models.trial.paths import EnvironmentPaths


_DEFAULT_DENY_PATTERNS = (
    "AGENTS.md",
    "CLAUDE.md",
    ".stet/**",
    "**/.stet/**",
    "node_modules/**",
    "**/node_modules/**",
    ".pnpm-store/**",
    "**/.pnpm-store/**",
    ".yarn/**",
    "**/.yarn/**",
    "dist/**",
    "**/dist/**",
    "build/**",
    "**/build/**",
    ".next/**",
    "**/.next/**",
    ".nuxt/**",
    "**/.nuxt/**",
    ".turbo/**",
    "**/.turbo/**",
    ".cache/**",
    "**/.cache/**",
    "coverage/**",
    "**/coverage/**",
    ".parcel-cache/**",
    "**/.parcel-cache/**",
    "__pycache__/**",
    "**/__pycache__/**",
    ".venv/**",
    "**/.venv/**",
    "venv/**",
    "**/venv/**",
    ".tox/**",
    "**/.tox/**",
    ".mypy_cache/**",
    "**/.mypy_cache/**",
    ".pytest_cache/**",
    "**/.pytest_cache/**",
    ".ruff_cache/**",
    "**/.ruff_cache/**",
    "target/**",
    "**/target/**",
    ".gradle/**",
    "**/.gradle/**",
    "vendor/bundle/**",
    "**/vendor/bundle/**",
    ".bundle/**",
    "**/.bundle/**",
    "tmp/**",
    "**/tmp/**",
    ".tmp/**",
    "**/.tmp/**",
    "*.pyc",
    "*.pyo",
    "*.tsbuildinfo",
    "*.class",
    "*.log",
    ".DS_Store",
)

_LOCKFILE_PATTERNS = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "Gemfile.lock",
    "*.lock",
)


def filter_patch_text(text: str) -> str:
    sections = _split_patch_sections(text)
    if not sections:
        return text
    keepable_source_paths = {
        path
        for section in sections
        for path in _section_paths(section)
        if path and not _is_denied_path(path) and not _is_lockfile_path(path)
    }
    kept = []
    for section in sections:
        paths = [path for path in _section_paths(section) if path]
        if any(_is_denied_path(path) for path in paths):
            continue
        if paths and all(_is_lockfile_path(path) for path in paths):
            if not keepable_source_paths:
                continue
        kept.append(section)
    return "".join("".join(section) for section in kept)


def _split_patch_sections(text: str) -> list[list[str]]:
    lines = text.splitlines(keepends=True)
    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("diff --git ") or line.startswith("diff -ruN "):
            if current:
                sections.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
    if current:
        sections.append(current)
    return sections


def _section_paths(section: list[str]) -> list[str]:
    if not section:
        return []
    header = section[0].strip()
    fields = header.split()
    paths: list[str] = []
    if header.startswith("diff --git ") and len(fields) >= 4:
        paths.extend((_normalize_patch_path(fields[2]), _normalize_patch_path(fields[3])))
    elif header.startswith("diff -ruN ") and len(fields) >= 4:
        paths.extend((_normalize_patch_path(fields[-2]), _normalize_patch_path(fields[-1])))
    return [path for path in paths if path and path != "/dev/null"]


def _normalize_patch_path(path: str) -> str:
    path = path.strip()
    for prefix in ("a/", "b/", "/app/"):
        if path.startswith(prefix):
            return path[len(prefix) :]
    marker = "/agent-patch-snapshot/app/"
    if marker in path:
        return path.split(marker, 1)[1]
    return path


def _is_denied_path(path: str) -> bool:
    return _matches_any(path, _DEFAULT_DENY_PATTERNS)


def _is_lockfile_path(path: str) -> bool:
    return _matches_any(path, _LOCKFILE_PATTERNS)


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    normalized = path.strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


class AgentPatchCaptureMixin:
    """Shared Harbor helper for capturing agent.patch from /app mutations."""

    _PATCH_SNAPSHOT_DIR = Path("/tmp/agent-patch-snapshot")
    _APP_DIR = Path("/app")
    _PATCH_FILENAME = "agent.patch"
    _PATCH_OPERATION_TIMEOUT_SEC = 1800
    _AGENT_RUN_TIMEOUT_SEC = 1800

    @staticmethod
    def _quote(path: Path) -> str:
        return shlex.quote(path.as_posix())

    def _extended_agent_timeout(self, timeout_sec: int | None) -> int:
        if timeout_sec is None:
            return self._AGENT_RUN_TIMEOUT_SEC
        return max(timeout_sec, self._AGENT_RUN_TIMEOUT_SEC)

    @property
    def _snapshot_root(self) -> Path:
        return self._PATCH_SNAPSHOT_DIR / self._APP_DIR.name

    @property
    def _agent_patch_path(self) -> Path:
        return EnvironmentPaths.agent_dir / self._PATCH_FILENAME

    def _snapshot_command(self) -> str:
        app_dir = self._quote(self._APP_DIR)
        snapshot_root = self._quote(self._snapshot_root)
        return (
            f"rm -rf {self._quote(self._PATCH_SNAPSHOT_DIR)} && "
            f"mkdir -p {snapshot_root} && "
            f"(cd {app_dir} && tar --exclude=.git -cf - .) | "
            f"(cd {snapshot_root} && tar -xf -)"
        )

    def _capture_patch_command(self) -> str:
        snapshot = self._quote(self._snapshot_root)
        app_dir = self._quote(self._APP_DIR)
        patch_path = self._quote(self._agent_patch_path)
        snapshot_dir = self._quote(self._PATCH_SNAPSHOT_DIR)
        return f"""
mkdir -p {self._quote(EnvironmentPaths.agent_dir)}
set +e
if git -C {app_dir} rev-parse --verify HEAD >/dev/null 2>&1; then
  git -C {app_dir} diff --binary --no-color HEAD -- > {patch_path}
  status=$?
  if [ "$status" -gt 1 ]; then
    rm -rf {snapshot_dir}
    exit "$status"
  fi

  untracked_list=$(mktemp)
  git -C {app_dir} ls-files --others --exclude-standard > "$untracked_list"
  while IFS= read -r relpath; do
    [ -z "$relpath" ] && continue
    git -C {app_dir} diff --no-index --binary --no-color -- /dev/null "$relpath" >> {patch_path}
    status=$?
    if [ "$status" -gt 1 ]; then
      rm -f "$untracked_list"
      rm -rf {snapshot_dir}
      exit "$status"
    fi
  done < "$untracked_list"
  rm -f "$untracked_list"
  rm -rf {snapshot_dir}
  exit 0
fi

ignore_repo=$(mktemp -d)
path_list=$(mktemp)
status=0
if command -v git >/dev/null 2>&1 && git init -q "$ignore_repo" >/dev/null 2>&1; then
  git --git-dir="$ignore_repo/.git" --work-tree={app_dir} ls-files --others --exclude-standard > "$path_list"
  (cd {snapshot} && find . -path './.git' -prune -o -type f -print | sed 's#^./##') >> "$path_list"
else
  (cd {app_dir} && find . -path './.git' -prune -o -type f -print | sed 's#^./##') > "$path_list"
  (cd {snapshot} && find . -path './.git' -prune -o -type f -print | sed 's#^./##') >> "$path_list"
fi
sort -u "$path_list" > "$path_list.sorted"
: > {patch_path}
is_denied_relpath() {{
  case "$1" in
    .git/*|.stet/*|*/.stet/*|node_modules/*|*/node_modules/*|.pnpm-store/*|*/.pnpm-store/*|.yarn/*|*/.yarn/*|dist/*|*/dist/*|build/*|*/build/*|.next/*|*/.next/*|.nuxt/*|*/.nuxt/*|.turbo/*|*/.turbo/*|.cache/*|*/.cache/*|coverage/*|*/coverage/*|.parcel-cache/*|*/.parcel-cache/*|__pycache__/*|*/__pycache__/*|.venv/*|*/.venv/*|venv/*|*/venv/*|.tox/*|*/.tox/*|.mypy_cache/*|*/.mypy_cache/*|.pytest_cache/*|*/.pytest_cache/*|.ruff_cache/*|*/.ruff_cache/*|target/*|*/target/*|.gradle/*|*/.gradle/*|vendor/bundle/*|*/vendor/bundle/*|.bundle/*|*/.bundle/*|tmp/*|*/tmp/*|.tmp/*|*/.tmp/*|*.pyc|*.pyo|*.tsbuildinfo|*.class|*.log|.DS_Store)
      return 0
      ;;
  esac
  return 1
}}
is_lockfile_relpath() {{
  case "$1" in
    package-lock.json|*/package-lock.json|pnpm-lock.yaml|*/pnpm-lock.yaml|yarn.lock|*/yarn.lock|Cargo.lock|*/Cargo.lock|Gemfile.lock|*/Gemfile.lock|*.lock)
      return 0
      ;;
  esac
  return 1
}}
has_relpath_change() {{
  old_path={snapshot}/"$1"
  new_path={app_dir}/"$1"
  if [ -e "$old_path" ] && [ -e "$new_path" ] && cmp -s "$old_path" "$new_path"; then
    return 1
  fi
  return 0
}}
source_seen=0
while IFS= read -r relpath; do
  [ -z "$relpath" ] && continue
  if is_denied_relpath "$relpath" || is_lockfile_relpath "$relpath"; then
    continue
  fi
  if has_relpath_change "$relpath"; then
    source_seen=1
    break
  fi
done < "$path_list.sorted"
while IFS= read -r relpath; do
  [ -z "$relpath" ] && continue
  if is_denied_relpath "$relpath"; then
    continue
  fi
  if is_lockfile_relpath "$relpath" && [ "$source_seen" -ne 1 ]; then
    continue
  fi
  old_path={snapshot}/"$relpath"
  new_path={app_dir}/"$relpath"
  if [ -e "$old_path" ] && [ -e "$new_path" ] && cmp -s "$old_path" "$new_path"; then
    continue
  fi
  printf 'diff -ruN %s %s\n' "$old_path" "$new_path" >> {patch_path}
  diff -ruN "$old_path" "$new_path" >> {patch_path}
  diff_status=$?
  if [ "$diff_status" -gt 1 ]; then
    status="$diff_status"
    break
  fi
done < "$path_list.sorted"
rm -f "$path_list" "$path_list.sorted"
rm -rf "$ignore_repo" {snapshot_dir}
if [ "$status" -gt 1 ]; then
  exit "$status"
fi
exit 0
""".strip()

    async def _await_preserving_cancellation(self, coro: object) -> None:
        task = asyncio.create_task(coro)
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise

    async def snapshot_agent_patch(self, environment: BaseEnvironment) -> None:
        await environment.exec(
            command=self._snapshot_command(),
            timeout_sec=self._PATCH_OPERATION_TIMEOUT_SEC,
        )

    async def capture_agent_patch(self, environment: BaseEnvironment) -> None:
        await self._await_preserving_cancellation(
            environment.exec(
                command=self._capture_patch_command(),
                timeout_sec=self._PATCH_OPERATION_TIMEOUT_SEC,
            )
        )
