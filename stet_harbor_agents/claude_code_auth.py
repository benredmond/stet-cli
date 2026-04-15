from __future__ import annotations

import base64
import os
from pathlib import Path

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from stet_harbor_agents.compat import ExecInput
from stet_harbor_agents.patch_capture import AgentPatchCaptureMixin


class ClaudeCodeAuthAgent(AgentPatchCaptureMixin, ClaudeCode):
    """Harbor Claude Code agent with local credential bootstrap support."""

    _REASONING_EFFORT_LEVELS = {
        "low": "low",
        "medium": "medium",
        "high": "high",
        # Stet exposes xhigh as the cross-harness top reasoning level. Claude
        # Code's native equivalent is max.
        "xhigh": "max",
    }

    def __init__(self, *args, **kwargs):
        self._reasoning_effort = kwargs.get("reasoning_effort")
        super().__init__(*args, **kwargs)

    @property
    def _install_agent_template_path(self) -> Path:
        return Path(__file__).parent / "install-claude-code-auth.sh.j2"

    def _setup_env(self) -> dict[str, str]:
        env = super()._setup_env()
        env.update(self._reasoning_env())

        credentials_json_b64 = self._credentials_json_b64()
        if credentials_json_b64:
            env["CLAUDE_CODE_CREDENTIALS_JSON_B64"] = credentials_json_b64

        for key in (
            "CLAUDE_AUTH_JSON_B64",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        ):
            value = os.environ.get(key, "").strip()
            if value:
                env[key] = value

        return env

    def _reasoning_env(self) -> dict[str, str]:
        effort = (self._reasoning_effort or "").strip().lower()
        if not effort:
            return {}
        effort_level = self._REASONING_EFFORT_LEVELS.get(effort)
        if not effort_level:
            allowed = ", ".join(sorted(self._REASONING_EFFORT_LEVELS))
            raise ValueError(f"unsupported reasoning_effort {effort!r}; expected one of {allowed}")
        return {"CLAUDE_CODE_EFFORT_LEVEL": effort_level}

    def _credentials_json_b64(self) -> str:
        value = (
            self._extra_env.get("CLAUDE_CODE_CREDENTIALS_JSON_B64")
            or os.environ.get("CLAUDE_CODE_CREDENTIALS_JSON_B64", "")
        )
        if value.strip():
            return value.strip()

        raw = self._extra_env.get("CLAUDE_CODE_CREDENTIALS_JSON") or os.environ.get(
            "CLAUDE_CODE_CREDENTIALS_JSON", ""
        )
        if raw.strip():
            return base64.b64encode(raw.encode("utf-8")).decode("ascii")

        return ""

    def _credential_env(self) -> dict[str, str]:
        env: dict[str, str] = {}
        credentials_json_b64 = self._credentials_json_b64()
        if credentials_json_b64:
            env["CLAUDE_CODE_CREDENTIALS_JSON_B64"] = credentials_json_b64
        env.update(self._reasoning_env())

        for key in (
            "CLAUDE_AUTH_JSON_B64",
            "CLAUDE_CODE_OAUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        ):
            value = self._extra_env.get(key) or os.environ.get(key, "")
            if value.strip():
                env[key] = value

        return env

    def _credential_bootstrap_command(self) -> str:
        return """
mkdir -p "$CLAUDE_CONFIG_DIR" "$HOME/.claude"
if [ -n "${CLAUDE_CODE_CREDENTIALS_JSON_B64:-}" ]; then
  printf '%s' "$CLAUDE_CODE_CREDENTIALS_JSON_B64" | base64 -d > "$CLAUDE_CONFIG_DIR/.credentials.json"
  printf '%s' "$CLAUDE_CODE_CREDENTIALS_JSON_B64" | base64 -d > "$HOME/.claude/.credentials.json"
  chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json" "$HOME/.claude/.credentials.json"
elif [ -n "${CLAUDE_CODE_CREDENTIALS_JSON:-}" ]; then
  printf '%s' "$CLAUDE_CODE_CREDENTIALS_JSON" > "$CLAUDE_CONFIG_DIR/.credentials.json"
  printf '%s' "$CLAUDE_CODE_CREDENTIALS_JSON" > "$HOME/.claude/.credentials.json"
  chmod 600 "$CLAUDE_CONFIG_DIR/.credentials.json" "$HOME/.claude/.credentials.json"
fi
""".strip()

    def create_run_agent_commands(self, instruction: str) -> list[ExecInput]:
        commands = super().create_run_agent_commands(instruction)
        credential_env = self._credential_env()
        reasoning_env = self._reasoning_env()
        if not commands:
            return commands

        updated_commands: list[ExecInput] = []
        for index, command in enumerate(commands):
            merged_env = dict(command.env or {})
            if credential_env:
                merged_env.update(credential_env)
            if reasoning_env:
                merged_env.update(reasoning_env)
            final_env = merged_env if command.env is not None or credential_env or reasoning_env else None
            updated_command = command.command
            if index == 0 and credential_env:
                updated_command = f"{self._credential_bootstrap_command()} && {updated_command}"
            updated_commands.append(
                ExecInput(
                    command=updated_command,
                    cwd=command.cwd,
                    env=final_env,
                    timeout_sec=self._extended_agent_timeout(command.timeout_sec),
                )
            )

        return updated_commands

    async def exec_as_agent(
        self,
        environment: BaseEnvironment,
        command: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        timeout_sec: int | None = None,
    ):
        credential_env = self._credential_env()
        reasoning_env = self._reasoning_env()
        if credential_env or reasoning_env:
            merged_env = dict(env or {})
            if credential_env:
                merged_env.update(credential_env)
            if reasoning_env:
                merged_env.update(reasoning_env)
            env = merged_env
            if getattr(self, "_stet_claude_bootstrap_pending", False):
                command = f"{command} && {self._credential_bootstrap_command()}"
                self._stet_claude_bootstrap_pending = False

        return await super().exec_as_agent(
            environment,
            command=command,
            env=env,
            cwd=cwd,
            timeout_sec=self._extended_agent_timeout(timeout_sec),
        )

    async def setup(self, environment: BaseEnvironment) -> None:
        await super().setup(environment)
        await self.snapshot_agent_patch(environment)

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        previous_bootstrap_pending = getattr(
            self, "_stet_claude_bootstrap_pending", False
        )
        self._stet_claude_bootstrap_pending = True
        try:
            await super().run(instruction=instruction, environment=environment, context=context)
        finally:
            self._stet_claude_bootstrap_pending = previous_bootstrap_pending
            await self.capture_agent_patch(environment)
