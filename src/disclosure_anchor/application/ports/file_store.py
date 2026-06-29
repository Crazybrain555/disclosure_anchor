"""File-store port contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class FileStorePathPort(Protocol):
    def raw_document_relpath(
        self,
        *,
        provider: str,
        provider_document_id: str,
        raw_file_hash: str,
        extension: str = ".pdf",
    ) -> Path:
        ...

    def parser_artifacts_root_relpath(self, *, document_id: str, processing_run_id: str) -> Path:
        ...

    def normalized_ir_relpath(self, *, document_id: str, processing_run_id: str) -> Path:
        ...

    def document_units_snapshot_relpath(
        self, *, document_id: str, processing_run_id: str
    ) -> Path:
        ...

    def runtime_tmp_path(self, name: str | None = None) -> Path:
        ...
