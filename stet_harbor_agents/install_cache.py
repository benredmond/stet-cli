from __future__ import annotations

import asyncio
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable


CACHE_DIR_ENV = "STET_HARNESS_CLI_CACHE_DIR"
CACHE_MODE_ENV = "STET_HARNESS_CLI_CACHE_MODE"
CACHE_ARTIFACT_PATH = Path("/logs/agent/harness_cli_cache.json")
SECRET_KEY_RE = re.compile(
    r"(token|secret|password|credential|api[_-]?key|oauth)",
    re.IGNORECASE,
)
SECRET_FILE_NAMES = {
    ".credentials.json",
    "auth.json",
    "credentials.json",
}
SECRET_DIR_NAMES = {
    ".claude",
    ".codex",
}


@dataclass(frozen=True)
class HarnessCLICacheDescriptor:
    harness_name: str
    harness_version: str
    install_method: str
    os_release_id: str = ""
    os_release_version_id: str = ""
    arch: str = ""
    runtime_abi: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def build_cache_key(descriptor: HarnessCLICacheDescriptor) -> dict[str, str]:
    payload = {
        "schema": "stet.harness_cli_cache.v1",
        "harness_name": descriptor.harness_name.strip(),
        "harness_version": descriptor.harness_version.strip(),
        "install_method": descriptor.install_method.strip(),
        "os_release_id": descriptor.os_release_id.strip(),
        "os_release_version_id": descriptor.os_release_version_id.strip(),
        "arch": descriptor.arch.strip(),
        "runtime_abi": descriptor.runtime_abi.strip(),
    }
    for key, value in sorted((descriptor.extra or {}).items()):
        if _looks_secret_key(key):
            continue
        payload[f"extra.{key.strip()}"] = str(value).strip()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["cache_key"] = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return payload


def validate_cache_tree_for_credentials(root: Path) -> None:
    root = Path(root)
    if not root.exists():
        return
    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        parts = set(path.parts)
        if parts & SECRET_DIR_NAMES or path.name.lower() in SECRET_FILE_NAMES:
            raise ValueError(f"credential material is not allowed in harness CLI cache: {rel}")


async def setup_with_cli_cache(
    *,
    environment,
    harness_name: str,
    harness_version: str,
    install_method: str,
    binary_name: str,
    setup: Callable[[], Awaitable[None]],
    extra: dict[str, str] | None = None,
) -> dict[str, str | bool]:
    mode = (os.environ.get(CACHE_MODE_ENV) or "auto").strip().lower()
    root_raw = (os.environ.get(CACHE_DIR_ENV) or "").strip()
    if mode in ("", "off") or not root_raw:
        await setup()
        metadata = {
            "mode": mode or "off",
            "enabled": False,
            "status": "disabled",
            "miss_reason": "cache_disabled" if mode == "off" else "cache_dir_missing",
            "harness_name": harness_name,
            "harness_version": harness_version,
        }
        _write_metadata(metadata)
        return metadata
    if mode not in ("auto", "on"):
        raise ValueError("STET_HARNESS_CLI_CACHE_MODE must be auto, on, or off")

    descriptor = HarnessCLICacheDescriptor(
        harness_name=harness_name,
        harness_version=harness_version or "default",
        install_method=install_method,
        os_release_id=_os_release_value("ID"),
        os_release_version_id=_os_release_value("VERSION_ID"),
        arch=platform.machine(),
        runtime_abi=_runtime_abi(),
        extra=extra or {},
    )
    key = build_cache_key(descriptor)
    root = Path(root_raw)
    cache_dir = root / "v1" / key["cache_key"]
    manifest_path = cache_dir / "manifest.json"
    lock_dir = cache_dir.with_suffix(".lock")

    if manifest_path.exists():
        await _activate_cache(environment, cache_dir, binary_name)
        metadata = _metadata("hit", mode, harness_name, harness_version, key)
        _write_metadata(metadata)
        return metadata

    await _acquire_lock(lock_dir)
    try:
        if manifest_path.exists():
            await _activate_cache(environment, cache_dir, binary_name)
            metadata = _metadata("hit", mode, harness_name, harness_version, key)
            _write_metadata(metadata)
            return metadata

        await setup()
        stage_dir = root / "staging" / f"{key['cache_key']}.{os.getpid()}"
        shutil.rmtree(stage_dir, ignore_errors=True)
        stage_dir.mkdir(parents=True, exist_ok=True)
        try:
            await _populate_cache(environment, stage_dir, binary_name)
            validate_cache_tree_for_credentials(stage_dir)
        except Exception:
            shutil.rmtree(stage_dir, ignore_errors=True)
            raise
        manifest = dict(key)
        manifest["binary_name"] = binary_name
        (stage_dir / "manifest.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        stage_dir.rename(cache_dir)
        metadata = _metadata("miss", mode, harness_name, harness_version, key)
        _write_metadata(metadata)
        return metadata
    finally:
        try:
            lock_dir.rmdir()
        except OSError:
            pass


async def _acquire_lock(lock_dir: Path) -> None:
    lock_dir.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(120):
        try:
            lock_dir.mkdir()
            return
        except FileExistsError:
            await asyncio.sleep(0.5)
    raise TimeoutError(f"timed out waiting for harness CLI cache lock: {lock_dir}")


async def _activate_cache(environment, cache_dir: Path, binary_name: str) -> None:
    command = (
        "prefix=$(npm prefix -g 2>/dev/null || true); "
        f"if [ -n \"$prefix\" ] && [ -d {shlex.quote(str(cache_dir / 'npm-prefix'))} ]; then "
        f"tar -C {shlex.quote(str(cache_dir / 'npm-prefix'))} -cf - . 2>/dev/null | tar -C \"$prefix\" -xf - 2>/dev/null || true; "
        "fi; "
        "mkdir -p \"$HOME/.local/bin\" /usr/local/bin 2>/dev/null || true; "
        f"if [ -d {shlex.quote(str(cache_dir / 'bin'))} ]; then "
        f"for f in {shlex.quote(str(cache_dir / 'bin'))}/*; do "
        "[ -e \"$f\" ] || continue; "
        "ln -sf \"$f\" \"$HOME/.local/bin/$(basename \"$f\")\" 2>/dev/null || true; "
        "ln -sf \"$f\" \"/usr/local/bin/$(basename \"$f\")\" 2>/dev/null || true; "
        "done; fi"
    )
    await environment.exec(command=command)


async def _populate_cache(environment, cache_dir: Path, binary_name: str) -> None:
    bin_dir = cache_dir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    quoted_bin = shlex.quote(binary_name)
    quoted_target = shlex.quote(str(bin_dir))
    command = (
        "prefix=$(npm prefix -g 2>/dev/null || true); "
        f"if [ -n \"$prefix\" ]; then mkdir -p {shlex.quote(str(cache_dir / 'npm-prefix'))}; "
        f"tar -C \"$prefix\" -cf - bin lib share 2>/dev/null | tar -C {shlex.quote(str(cache_dir / 'npm-prefix'))} -xf - 2>/dev/null || true; "
        "fi; "
        f"p=$(command -v {quoted_bin} 2>/dev/null || true); "
        f"if [ -n \"$p\" ]; then cp -a \"$p\" {quoted_target}/; fi"
    )
    await environment.exec(command=command)


def _metadata(
    status: str,
    mode: str,
    harness_name: str,
    harness_version: str,
    key: dict[str, str],
) -> dict[str, str | bool]:
    return {
        "mode": mode,
        "enabled": True,
        "status": status,
        "harness_name": harness_name,
        "harness_version": harness_version,
        "cache_key": key["cache_key"],
    }


def _write_metadata(metadata: dict[str, str | bool]) -> None:
    try:
        CACHE_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_ARTIFACT_PATH.write_text(
            json.dumps(metadata, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _os_release_value(name: str) -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key == name:
                return value.strip().strip('"')
    except OSError:
        return ""
    return ""


def _runtime_abi() -> str:
    libc_name, libc_version = platform.libc_ver()
    libc = "-".join(part for part in (libc_name, libc_version) if part)
    return libc or platform.system().lower()


def _looks_secret_key(name: str) -> bool:
    return bool(SECRET_KEY_RE.search(str(name)))
