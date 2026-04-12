from __future__ import annotations

from dataclasses import dataclass


try:
    from harbor.agents.installed.base import ExecInput as ExecInput

    HARBOR_HAS_EXEC_INPUT = True
except ImportError:
    HARBOR_HAS_EXEC_INPUT = False

    @dataclass
    class ExecInput:
        command: str
        cwd: str | None = None
        env: dict[str, str] | None = None
        timeout_sec: int | None = None
