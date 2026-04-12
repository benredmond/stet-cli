import asyncio
import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from dataclasses import dataclass
from pathlib import Path


def install_fake_harbor_modules():
    harbor = types.ModuleType("harbor")
    agents = types.ModuleType("harbor.agents")
    installed = types.ModuleType("harbor.agents.installed")
    base = types.ModuleType("harbor.agents.installed.base")
    codex = types.ModuleType("harbor.agents.installed.codex")
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

    class Codex:
        _OUTPUT_FILENAME = "agent.log"

        def __init__(self, model_name=None, *args, **kwargs):
            self.model_name = model_name
            self._extra_env = kwargs.get("extra_env", {})
            self._reasoning_effort = kwargs.get("reasoning_effort")
            self._should_fail_setup = False
            self._should_fail_run = False

        def _build_register_mcp_servers_command(self):
            return ""

        async def setup(self, environment):
            if self._should_fail_setup:
                raise RuntimeError(self._should_fail_setup)
            return None

        async def run(self, instruction: str, environment, context):
            if self._should_fail_run:
                raise RuntimeError("boom")
            return None

    base.ExecInput = ExecInput
    codex.Codex = Codex
    environments_base.BaseEnvironment = BaseEnvironment
    models_agent_context.AgentContext = AgentContext
    models_trial_paths.EnvironmentPaths = EnvironmentPaths

    sys.modules["harbor"] = harbor
    sys.modules["harbor.agents"] = agents
    sys.modules["harbor.agents.installed"] = installed
    sys.modules["harbor.agents.installed.base"] = base
    sys.modules["harbor.agents.installed.codex"] = codex
    sys.modules["harbor.environments"] = environments
    sys.modules["harbor.environments.base"] = environments_base
    sys.modules["harbor.models"] = models
    sys.modules["harbor.models.agent"] = models_agent
    sys.modules["harbor.models.agent.context"] = models_agent_context
    sys.modules["harbor.models.trial"] = models_trial
    sys.modules["harbor.models.trial.paths"] = models_trial_paths


class CodexAuthAgentTests(unittest.TestCase):
    def setUp(self):
        install_fake_harbor_modules()
        sys.modules.pop("stet_harbor_agents.codex_auth", None)
        self.module = importlib.import_module("stet_harbor_agents.codex_auth")
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.module.EnvironmentPaths.agent_dir = Path(self.tmpdir.name) / "agent"
        self.auth_file = Path(self.tmpdir.name) / "auth.json"
        self.auth_file.write_text('{"OPENAI_API_KEY":"test-key"}', encoding="utf-8")

    def tearDown(self):
        for key in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "CODEX_AUTH_FILE"):
            os.environ.pop(key, None)

    def test_create_run_agent_commands_includes_bootstrap_verification_and_markers(self):
        os.environ["OPENAI_BASE_URL"] = "https://example.invalid/v1"
        agent = self.module.CodexAuthAgent(
            model_name="openai/gpt-5.4",
            auth_path=str(self.auth_file),
            reasoning_effort="high",
        )

        commands = agent.create_run_agent_commands("fix the task")

        self.assertEqual(len(commands), 2)
        run_command = commands[1]
        self.assertIn("bootstrap_check=$(mktemp", run_command.command)
        self.assertIn("emit_bootstrap_marker()", run_command.command)
        self.assertIn("codex --version", run_command.command)
        self.assertIn("codex_optional_dependency_missing", run_command.command)
        self.assertIn("mkdir -p \"$(dirname \"$agent_log\")\"", run_command.command)
        self.assertIn("tee -a \"$agent_log\"", run_command.command)
        self.assertIn("--model gpt-5.4", run_command.command)
        self.assertIn("-c model_reasoning_effort=high", run_command.command)
        self.assertEqual(run_command.env["OPENAI_BASE_URL"], "https://example.invalid/v1")
        self.assertIn("CODEX_HOME", run_command.env)

    def test_setup_failure_writes_classified_bootstrap_marker(self):
        agent = self.module.CodexAuthAgent(
            model_name="openai/gpt-5.4",
            auth_path=str(self.auth_file),
        )
        agent._should_fail_setup = (
            "Missing optional dependency @openai/codex-linux-arm64"
        )
        environment = sys.modules["harbor.environments.base"].BaseEnvironment()

        with self.assertRaises(RuntimeError):
            asyncio.run(agent.setup(environment))

        marker_path = self.module.EnvironmentPaths.agent_dir / agent._OUTPUT_FILENAME
        self.assertTrue(marker_path.exists())
        lines = marker_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertGreaterEqual(len(lines), 1)
        marker = json.loads(lines[-1])
        self.assertEqual(marker["type"], "stet.bootstrap")
        self.assertEqual(marker["status"], "failed")
        self.assertEqual(
            marker["failure_class"], "codex_optional_dependency_missing"
        )


if __name__ == "__main__":
    unittest.main()
