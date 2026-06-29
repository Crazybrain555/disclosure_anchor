"""Basic fail-closed runtime checks for Phase 01."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from disclosure_anchor.settings import Settings


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str

    @property
    def ok(self) -> bool:
        return self.status == "PASS"


@dataclass(frozen=True)
class DoctorReport:
    results: tuple[CheckResult, ...]

    @property
    def ok(self) -> bool:
        return all(result.ok for result in self.results)


def _is_writable_dir(path: Path) -> bool:
    return path.is_dir() and os.access(path, os.R_OK | os.W_OK | os.X_OK)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _check_path_exists(name: str, path: Path) -> CheckResult:
    if path.exists():
        return CheckResult(name=name, status="PASS", message=str(path))
    return CheckResult(name=name, status="FAIL", message=f"missing: {path}")


def _check_writable_dir(name: str, path: Path) -> CheckResult:
    if _is_writable_dir(path):
        return CheckResult(name=name, status="PASS", message=str(path))
    return CheckResult(name=name, status="FAIL", message=f"not writable directory: {path}")


def _check_under_root(name: str, path: Path, root: Path) -> CheckResult:
    if _is_relative_to(path, root):
        return CheckResult(name=name, status="PASS", message=str(path))
    return CheckResult(name=name, status="FAIL", message=f"{path} is not under {root}")


def run_doctor(settings: Settings) -> DoctorReport:
    """Run Phase 01 checks without creating or repairing external state."""

    checks: list[CheckResult] = [
        _check_path_exists("agent_system_root", settings.agent_system_root),
        _check_path_exists("mount sentinel", settings.sentinel_path),
        _check_writable_dir("DISCLOSURE_DATA_ROOT", settings.disclosure_data_root),
        _check_writable_dir("DISCLOSURE_SHARED_ROOT", settings.disclosure_shared_root),
        _check_writable_dir("DISCLOSURE_RUNTIME_ROOT", settings.disclosure_runtime_root),
    ]

    cache_names = ("MINERU_MODEL_CACHE", "HF_HOME", "MODELSCOPE_CACHE")
    checks.extend(
        _check_under_root(name, path, settings.disclosure_shared_root)
        for name, path in zip(cache_names, settings.model_cache_paths)
    )

    return DoctorReport(results=tuple(checks))


def render_report(results: Iterable[CheckResult]) -> str:
    return "\n".join(f"[{result.status}] {result.name}: {result.message}" for result in results)
