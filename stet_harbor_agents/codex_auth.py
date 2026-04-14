from __future__ import annotations

import json
import os
import shlex
from base64 import b64encode
from pathlib import Path

from harbor.agents.installed.codex import Codex
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trial.paths import EnvironmentPaths

from stet_harbor_agents.compat import ExecInput, HARBOR_HAS_EXEC_INPUT
from stet_harbor_agents.patch_capture import AgentPatchCaptureMixin


class CodexAuthAgent(AgentPatchCaptureMixin, Codex):
    """Harbor Codex agent with auth-file support for local eval runs."""

    _BOOTSTRAP_MARKER_TYPE = "stet.bootstrap"
    _BOOTSTRAP_STATUS_OK = "ok"
    _BOOTSTRAP_STATUS_FAILED = "failed"
    _BOOTSTRAP_FAILURE_CLASS_OPTIONAL_DEP = "codex_optional_dependency_missing"
    _BOOTSTRAP_FAILURE_CLASS_SETUP = "agent_setup_failed"
    _OPTIONAL_DEPENDENCY_SIGNATURE = "Missing optional dependency @openai/codex-linux-"

    def __init__(
        self,
        model_name: str | None = None,
        *args,
        auth_path: str | None = None,
        **kwargs,
    ):
        super().__init__(model_name=model_name, *args, **kwargs)
        default_auth_path = os.environ.get("CODEX_AUTH_FILE") or "~/.codex/auth.json"
        self._auth_path = Path(auth_path or default_auth_path).expanduser()

    def _build_auth_env(self) -> dict[str, str]:
        env: dict[str, str] = {
            "CODEX_HOME": EnvironmentPaths.agent_dir.as_posix(),
        }
        if self._auth_path.exists():
            env["CODEX_AUTH_JSON_B64"] = b64encode(self._auth_path.read_bytes()).decode(
                "utf-8"
            )
            return env

        api_key = self._extra_env.get("OPENAI_API_KEY") or os.environ.get(
            "OPENAI_API_KEY"
        )
        if api_key:
            env["OPENAI_API_KEY"] = api_key
            return env

        raise ValueError(
            f"Codex auth file not found at {self._auth_path} and OPENAI_API_KEY is not set."
        )

    async def setup(self, environment: BaseEnvironment) -> None:
        try:
            await super().setup(environment)
        except Exception as exc:
            self._append_bootstrap_marker(
                self._BOOTSTRAP_STATUS_FAILED,
                self._bootstrap_failure_class(str(exc)),
                str(exc),
            )
            raise
        await self.snapshot_agent_patch(environment)

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        if HARBOR_HAS_EXEC_INPUT:
            try:
                await super().run(
                    instruction=instruction,
                    environment=environment,
                    context=context,
                )
            finally:
                await self.capture_agent_patch(environment)
            return

        if hasattr(self, "render_instruction"):
            instruction = self.render_instruction(instruction)

        try:
            try:
                for exec_input in self.create_run_agent_commands(instruction):
                    await self.exec_as_agent(
                        environment,
                        command=exec_input.command,
                        cwd=exec_input.cwd,
                        env=exec_input.env,
                        timeout_sec=exec_input.timeout_sec,
                    )
                self.populate_context_post_run(context)
            finally:
                try:
                    await self.exec_as_agent(
                        environment,
                        command='rm -rf /tmp/codex-secrets "$CODEX_HOME/auth.json" "$CODEX_HOME/tmp"',
                        env={"CODEX_HOME": EnvironmentPaths.agent_dir.as_posix()},
                    )
                except Exception:
                    pass
        finally:
            await self.capture_agent_patch(environment)

    def create_run_agent_commands(self, instruction: str) -> list[ExecInput]:
        escaped_instruction = shlex.quote(instruction)

        if not self.model_name:
            raise ValueError("Model name is required")

        model = self.model_name.split("/")[-1]
        env = self._build_auth_env()

        if openai_base_url := (
            self._extra_env.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
        ):
            env["OPENAI_BASE_URL"] = openai_base_url

        cli_flags = self.build_cli_flags() if hasattr(self, "build_cli_flags") else ""
        if cli_flags:
            reasoning_flag = f"{cli_flags} "
        else:
            reasoning_effort = getattr(self, "_reasoning_effort", None)
            reasoning_flag = (
                f"-c model_reasoning_effort={reasoning_effort} "
                if reasoning_effort
                else ""
            )

        setup_command = """
mkdir -p /tmp/codex-secrets "$CODEX_HOME"
if [ -n "${CODEX_AUTH_JSON_B64:-}" ]; then
  printf '%s' "$CODEX_AUTH_JSON_B64" | base64 -d > /tmp/codex-secrets/auth.json
elif [ -n "${OPENAI_API_KEY:-}" ]; then
  cat >/tmp/codex-secrets/auth.json <<EOF
{
  "OPENAI_API_KEY": "${OPENAI_API_KEY}"
}
EOF
else
  echo "Missing Codex auth" >&2
  exit 1
fi
ln -sf /tmp/codex-secrets/auth.json "$CODEX_HOME/auth.json"
                """

        mcp_command = self._build_register_mcp_servers_command()
        if mcp_command:
            setup_command += f"\n{mcp_command}"

        agent_log_path = EnvironmentPaths.agent_dir / self._OUTPUT_FILENAME

        return [
            ExecInput(
                command=setup_command,
                env=env,
            ),
            ExecInput(
                command=(
                    "trap 'rm -rf /tmp/codex-secrets \"$CODEX_HOME/auth.json\" \"$bootstrap_check\"' EXIT TERM INT; "
                    ". ~/.nvm/nvm.sh; "
                    f"agent_log={shlex.quote(agent_log_path.as_posix())}; "
                    "mkdir -p \"$(dirname \"$agent_log\")\"; "
                    "bootstrap_check=$(mktemp /tmp/codex-bootstrap-XXXXXX.log); "
                    "emit_bootstrap_marker() { "
                    "status=\"$1\"; "
                    "failure_class=\"$2\"; "
                    "if [ -n \"$failure_class\" ]; then "
                    "printf '{\"type\":\"stet.bootstrap\",\"status\":\"%s\",\"failure_class\":\"%s\"}\\n' \"$status\" \"$failure_class\" | tee -a \"$agent_log\"; "
                    "else "
                    "printf '{\"type\":\"stet.bootstrap\",\"status\":\"%s\"}\\n' \"$status\" | tee -a \"$agent_log\"; "
                    "fi; "
                    "}; "
                    "if ! codex --version >\"$bootstrap_check\" 2>&1; then "
                    f"failure_class={self._BOOTSTRAP_FAILURE_CLASS_SETUP}; "
                    f"if grep -Fq {shlex.quote(self._OPTIONAL_DEPENDENCY_SIGNATURE)} \"$bootstrap_check\"; then "
                    f"failure_class={self._BOOTSTRAP_FAILURE_CLASS_OPTIONAL_DEP}; "
                    "fi; "
                    "emit_bootstrap_marker failed \"$failure_class\"; "
                    "cat \"$bootstrap_check\" | tee -a \"$agent_log\"; "
                    "exit 1; "
                    "fi; "
                    "emit_bootstrap_marker ok ''; "
                    "codex exec "
                    "--dangerously-bypass-approvals-and-sandbox "
                    "--skip-git-repo-check "
                    f"--model {model} "
                    "--json "
                    "--enable unified_exec "
                    f"{reasoning_flag}"
                    "-- "
                    f"{escaped_instruction} "
                    "2>&1 </dev/null | stdbuf -oL tee -a \"$agent_log\""
                ),
                env=env,
                timeout_sec=self._extended_agent_timeout(None),
            ),
        ]

    def _bootstrap_failure_class(self, message: str) -> str:
        if self._OPTIONAL_DEPENDENCY_SIGNATURE in message:
            return self._BOOTSTRAP_FAILURE_CLASS_OPTIONAL_DEP
        return self._BOOTSTRAP_FAILURE_CLASS_SETUP

    def _append_bootstrap_marker(
        self,
        status: str,
        failure_class: str | None = None,
        message: str | None = None,
    ) -> None:
        payload = {
            "type": self._BOOTSTRAP_MARKER_TYPE,
            "status": status,
        }
        if failure_class:
            payload["failure_class"] = failure_class
        if message:
            payload["message"] = message
        marker_path = EnvironmentPaths.agent_dir / self._OUTPUT_FILENAME
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        with marker_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
