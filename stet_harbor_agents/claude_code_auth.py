from __future__ import annotations

import base64
import os
from pathlib import Path

from harbor.agents.installed.base import ExecInput
from harbor.agents.installed.claude_code import ClaudeCode
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

from stet_harbor_agents.patch_capture import AgentPatchCaptureMixin


class ClaudeCodeAuthAgent(AgentPatchCaptureMixin, ClaudeCode):
    """Harbor Claude Code agent with local credential bootstrap support."""

    @property
    def _install_agent_template_path(self) -> Path:
        return Path(__file__).parent / "install-claude-code-auth.sh.j2"

    def _setup_env(self) -> dict[str, str]:
        env = super()._setup_env()

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

    def create_run_agent_commands(self, instruction: str) -> list[ExecInput]:
        commands = super().create_run_agent_commands(instruction)
        credential_env = self._credential_env()
        if not commands or not credential_env:
            return commands

        setup_bootstrap = """
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

        updated_commands: list[ExecInput] = []
        for index, command in enumerate(commands):
            merged_env = dict(command.env or {})
            merged_env.update(credential_env)
            updated_command = command.command
            if index == 0:
                updated_command = f"{setup_bootstrap} && {updated_command}"
            updated_commands.append(
                ExecInput(
                    command=updated_command,
                    cwd=command.cwd,
                    env=merged_env,
                    timeout_sec=command.timeout_sec,
                )
            )

        return updated_commands

    async def setup(self, environment: BaseEnvironment) -> None:
        await super().setup(environment)
        await self.snapshot_agent_patch(environment)

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        try:
            await super().run(instruction=instruction, environment=environment, context=context)
        finally:
            await self.capture_agent_patch(environment)
