from __future__ import annotations

import asyncio
import shlex
from pathlib import Path

from harbor.environments.base import BaseEnvironment
from harbor.models.trial.paths import EnvironmentPaths


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

diff -ruN -x .git {snapshot} {app_dir} > {patch_path}
status=$?
rm -rf {snapshot_dir}
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
