"""Basic fail-closed runtime checks for Phase 01."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Engine

from disclosure_anchor.adapters.db.postgres.connection import create_db_engine
from disclosure_anchor.adapters.db.postgres.schema import CORE_SCHEMA
from disclosure_anchor.adapters.storage.path_builder import FileStorePathBuilder
from disclosure_anchor.adapters.storage.raw_document_store import RawDocumentStore
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


def _nearest_existing_parent(path: Path) -> Path | None:
    current = path
    while not current.exists():
        if current.parent == current:
            return None
        current = current.parent
    return current


def _check_same_filesystem(name: str, left: Path, right: Path) -> CheckResult:
    left_existing = _nearest_existing_parent(left)
    right_existing = _nearest_existing_parent(right)
    if left_existing is None or right_existing is None:
        return CheckResult(
            name=name,
            status="FAIL",
            message=f"cannot stat existing parents: {left} / {right}",
        )
    left_dev = left_existing.stat().st_dev
    right_dev = right_existing.stat().st_dev
    if left_dev == right_dev:
        return CheckResult(
            name=name,
            status="PASS",
            message=f"{left} and {right} share filesystem device {left_dev}",
        )
    return CheckResult(
        name=name,
        status="FAIL",
        message=(
            f"{left} and {right} are on different filesystem devices: "
            f"{left_dev} != {right_dev}"
        ),
    )


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
    checks.append(
        _check_same_filesystem(
            "raw archive filesystem",
            settings.disclosure_runtime_root / "tmp",
            settings.disclosure_data_root / "data" / "raw_documents",
        )
    )

    if settings.database_url is not None:
        try:
            engine = create_db_engine(settings.database_url.get_secret_value())
            checks.extend(run_raw_archive_checks(settings, engine))
        except Exception as exc:
            checks.append(CheckResult("raw archive db checks", "FAIL", str(exc)))

    return DoctorReport(results=tuple(checks))


def _registered_raw_documents(engine: Engine) -> list[tuple[str, str, str]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT document_id, raw_file_relpath, raw_file_hash "
                f"FROM {CORE_SCHEMA}.document "
                "WHERE raw_file_relpath IS NOT NULL OR raw_file_hash IS NOT NULL"
            )
        ).all()
    return [(str(row[0]), str(row[1]), str(row[2])) for row in rows]


def run_raw_archive_checks(settings: Settings, engine: Engine) -> list[CheckResult]:
    """Verify registered raw files without mutating DB or files."""

    store = RawDocumentStore(FileStorePathBuilder(settings))
    results: list[CheckResult] = []
    for document_id, relpath, expected_hash in _registered_raw_documents(engine):
        if not relpath or not expected_hash:
            results.append(
                CheckResult(
                    name="raw hash",
                    status="FAIL",
                    message=f"document_id={document_id} missing relpath/hash",
                )
            )
            continue

        verification = store.verify_raw_document(
            relpath=Path(relpath), expected_hash=expected_hash
        )
        results.append(
            CheckResult(
                name="raw hash",
                status="PASS" if verification.ok else "FAIL",
                message=(
                    f"document_id={document_id} relpath={relpath} "
                    f"message={verification.message}"
                ),
            )
        )

    if not results:
        results.append(CheckResult("raw hash", "PASS", "no registered raw documents"))
    return results


def render_report(results: Iterable[CheckResult]) -> str:
    return "\n".join(f"[{result.status}] {result.name}: {result.message}" for result in results)
