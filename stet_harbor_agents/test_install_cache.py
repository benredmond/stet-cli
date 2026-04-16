import json
import os
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from stet_harbor_agents.install_cache import (
    HarnessCLICacheDescriptor,
    build_cache_key,
    setup_with_cli_cache,
    validate_cache_tree_for_credentials,
)


class HarnessCLIInstallCacheTests(unittest.TestCase):
    def test_cache_key_is_generic_and_excludes_credentials(self):
        descriptor = HarnessCLICacheDescriptor(
            harness_name="codex",
            harness_version="0.52.0",
            install_method="npm-global",
            os_release_id="debian",
            os_release_version_id="12",
            arch="x86_64",
            runtime_abi="node20-glibc",
            extra={
                "OPENAI_API_KEY": "sk-secret",
                "package": "@openai/codex",
            },
        )

        key = build_cache_key(descriptor)

        encoded = json.dumps(key, sort_keys=True)
        self.assertIn("codex", encoded)
        self.assertIn("0.52.0", encoded)
        self.assertIn("node20-glibc", encoded)
        self.assertIn("@openai/codex", encoded)
        self.assertNotIn("sk-secret", encoded)
        self.assertNotIn("OPENAI_API_KEY", encoded)

    def test_cache_tree_rejects_credential_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "bin").mkdir()
            (root / "bin" / "codex").write_text("#!/bin/sh\n", encoding="utf-8")
            (root / ".codex").mkdir()
            (root / ".codex" / "auth.json").write_text(
                '{"OPENAI_API_KEY":"sk-secret"}',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "credential material"):
                validate_cache_tree_for_credentials(root)

    def test_cache_key_supports_non_claude_harnesses(self):
        descriptor = HarnessCLICacheDescriptor(
            harness_name="future-agent",
            harness_version="2026.4.16",
            install_method="curl-script",
            os_release_id="ubuntu",
            os_release_version_id="24.04",
            arch="arm64",
            runtime_abi="glibc-2.39",
        )

        key = build_cache_key(descriptor)

        self.assertEqual(key["harness_name"], "future-agent")
        self.assertEqual(key["install_method"], "curl-script")
        self.assertEqual(key["arch"], "arm64")

    def test_failed_credential_validation_removes_partial_cache(self):
        class Environment:
            async def exec(self, command: str, **kwargs):
                return None

        async def setup():
            return None

        async def populate(_environment, cache_dir: Path, _binary_name: str):
            (cache_dir / ".codex").mkdir(parents=True)
            (cache_dir / ".codex" / "auth.json").write_text(
                '{"OPENAI_API_KEY":"sk-secret"}',
                encoding="utf-8",
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ,
                {
                    "STET_HARNESS_CLI_CACHE_DIR": tmpdir,
                    "STET_HARNESS_CLI_CACHE_MODE": "on",
                },
                clear=False,
            ), mock.patch("stet_harbor_agents.install_cache._populate_cache", populate):
                with self.assertRaisesRegex(ValueError, "credential material"):
                    import asyncio

                    asyncio.run(
                        setup_with_cli_cache(
                            environment=Environment(),
                            harness_name="codex",
                            harness_version="0.52.0",
                            install_method="npm-global",
                            binary_name="codex",
                            setup=setup,
                        )
                    )

            self.assertFalse(any(Path(tmpdir).glob("v1/*")))

    def test_lock_timeout_does_not_populate_without_lock(self):
        class Environment:
            async def exec(self, command: str, **kwargs):
                return None

        async def setup():
            raise AssertionError("setup must not run without a lock")

        async def acquire(_lock_dir):
            raise TimeoutError("cache lock timed out")

        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ,
                {
                    "STET_HARNESS_CLI_CACHE_DIR": tmpdir,
                    "STET_HARNESS_CLI_CACHE_MODE": "on",
                },
                clear=False,
            ), mock.patch("stet_harbor_agents.install_cache._acquire_lock", acquire):
                with self.assertRaisesRegex(TimeoutError, "cache lock timed out"):
                    import asyncio

                    asyncio.run(
                        setup_with_cli_cache(
                            environment=Environment(),
                            harness_name="codex",
                            harness_version="0.52.0",
                            install_method="npm-global",
                            binary_name="codex",
                            setup=setup,
                        )
                    )


if __name__ == "__main__":
    os.environ.setdefault("PYTHONPATH", ".")
    unittest.main()
