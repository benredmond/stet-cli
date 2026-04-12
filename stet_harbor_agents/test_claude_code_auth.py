import importlib
import asyncio
import base64
import json
import os
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


def install_fake_harbor_modules():
    harbor = types.ModuleType("harbor")
    agents = types.ModuleType("harbor.agents")
    installed = types.ModuleType("harbor.agents.installed")
    base = types.ModuleType("harbor.agents.installed.base")
    claude_code = types.ModuleType("harbor.agents.installed.claude_code")
    environments = types.ModuleType("harbor.environments")
    environments_base = types.ModuleType("harbor.environments.base")
    models = types.ModuleType("harbor.models")
    models_agent = types.ModuleType("harbor.models.agent")
    models_agent_context = types.ModuleType("harbor.models.agent.context")
    models_trial = types.ModuleType("harbor.models.trial")
    models_trial_paths = types.ModuleType("harbor.models.trial.paths")

    @dataclass
    class ExecInput:
        command: str
        cwd: str | None = None
        env: dict | None = None
        timeout_sec: int | None = None

    class BaseEnvironment:
        def __init__(self):
            self.commands = []

        async def exec(self, command: str):
            self.commands.append(command)

    class AgentContext:
        pass

    class EnvironmentPaths:
        agent_dir = Path("/logs/agent")

    class ClaudeCode:
        def __init__(self, *args, **kwargs):
            self._extra_env = kwargs.get("extra_env", {})
            self._should_fail_run = False

        def _setup_env(self):
            return {}

        def create_run_agent_commands(self, instruction: str):
            return [ExecInput(command=f"claude run {instruction}", cwd="/app", env={}, timeout_sec=60)]

        async def setup(self, environment):
            return None

        async def run(self, instruction: str, environment, context):
            if self._should_fail_run:
                raise RuntimeError("boom")
            return None

    base.ExecInput = ExecInput
    claude_code.ClaudeCode = ClaudeCode
    environments_base.BaseEnvironment = BaseEnvironment
    models_agent_context.AgentContext = AgentContext
    models_trial_paths.EnvironmentPaths = EnvironmentPaths

    sys.modules["harbor"] = harbor
    sys.modules["harbor.agents"] = agents
    sys.modules["harbor.agents.installed"] = installed
    sys.modules["harbor.agents.installed.base"] = base
    sys.modules["harbor.agents.installed.claude_code"] = claude_code
    sys.modules["harbor.environments"] = environments
    sys.modules["harbor.environments.base"] = environments_base
    sys.modules["harbor.models"] = models
    sys.modules["harbor.models.agent"] = models_agent
    sys.modules["harbor.models.agent.context"] = models_agent_context
    sys.modules["harbor.models.trial"] = models_trial
    sys.modules["harbor.models.trial.paths"] = models_trial_paths


class ClaudeCodeAuthAgentTests(unittest.TestCase):
    def setUp(self):
        install_fake_harbor_modules()
        sys.modules.pop("stet_harbor_agents.claude_code_auth", None)
        self.module = importlib.import_module("stet_harbor_agents.claude_code_auth")

    def tearDown(self):
        for key in (
            "CLAUDE_CODE_CREDENTIALS_JSON",
            "CLAUDE_CODE_CREDENTIALS_JSON_B64",
            "CLAUDE_CODE_OAUTH_TOKEN",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
        ):
            os.environ.pop(key, None)

    def test_credentials_json_does_not_force_access_token_env(self):
        os.environ["CLAUDE_CODE_CREDENTIALS_JSON"] = json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": "stale-access-token",
                    "refreshToken": "refresh-token",
                }
            }
        )

        agent = self.module.ClaudeCodeAuthAgent()
        credential_env = agent._credential_env()

        self.assertNotIn("CLAUDE_CODE_CREDENTIALS_JSON", credential_env)
        self.assertIn("CLAUDE_CODE_CREDENTIALS_JSON_B64", credential_env)
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", credential_env)
        decoded = base64.b64decode(
            credential_env["CLAUDE_CODE_CREDENTIALS_JSON_B64"]
        ).decode()
        self.assertEqual(decoded, os.environ["CLAUDE_CODE_CREDENTIALS_JSON"])

    def test_explicit_oauth_token_is_preserved(self):
        os.environ["CLAUDE_CODE_CREDENTIALS_JSON"] = json.dumps(
            {"claudeAiOauth": {"accessToken": "stale-access-token"}}
        )
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = "explicit-token"

        agent = self.module.ClaudeCodeAuthAgent()
        credential_env = agent._credential_env()

        self.assertEqual(credential_env["CLAUDE_CODE_OAUTH_TOKEN"], "explicit-token")

    def test_preencoded_credentials_json_is_preserved(self):
        os.environ["CLAUDE_CODE_CREDENTIALS_JSON_B64"] = base64.b64encode(
            b'{"claudeAiOauth":{"accessToken":"token"}}'
        ).decode()

        agent = self.module.ClaudeCodeAuthAgent()
        credential_env = agent._credential_env()

        self.assertEqual(
            credential_env["CLAUDE_CODE_CREDENTIALS_JSON_B64"],
            os.environ["CLAUDE_CODE_CREDENTIALS_JSON_B64"],
        )

    def test_snapshot_command_uses_app_dot_copy(self):
        agent = self.module.ClaudeCodeAuthAgent()
        command = agent._snapshot_command()

        self.assertIn("tar --exclude=.git -cf - .", command)
        self.assertIn("tar -xf -", command)

    def test_capture_command_writes_agent_patch_to_agent_logs(self):
        agent = self.module.ClaudeCodeAuthAgent()
        command = agent._capture_patch_command()

        self.assertIn("/logs/agent/agent.patch", command)
        self.assertIn("git -C /app diff --binary --no-color HEAD --", command)
        self.assertIn("git -C /app ls-files --others --exclude-standard", command)
        self.assertIn("git -C /app diff --no-index --binary --no-color -- /dev/null", command)
        self.assertIn("diff -ruN -x .git", command)

    def test_setup_snapshots_app_tree_before_run(self):
        agent = self.module.ClaudeCodeAuthAgent()
        environment = sys.modules["harbor.environments.base"].BaseEnvironment()

        asyncio.run(agent.setup(environment))

        self.assertEqual(len(environment.commands), 1)
        self.assertIn("tar --exclude=.git -cf - .", environment.commands[0])

    def test_run_captures_patch_even_when_agent_run_fails(self):
        agent = self.module.ClaudeCodeAuthAgent()
        agent._should_fail_run = True
        environment = sys.modules["harbor.environments.base"].BaseEnvironment()
        context = sys.modules["harbor.models.agent.context"].AgentContext()

        with self.assertRaises(RuntimeError):
            asyncio.run(agent.run("fix it", environment, context))

        self.assertEqual(len(environment.commands), 1)
        self.assertIn("/logs/agent/agent.patch", environment.commands[0])


if __name__ == "__main__":
    unittest.main()
