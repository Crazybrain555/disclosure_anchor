"""Concrete MinerU parser adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from disclosure_anchor.adapters.parsers.mineru.artifact_reader import MinerUArtifactReader
from disclosure_anchor.adapters.parsers.mineru.mapper_to_ir import (
    MinerUParserInfo,
    MinerUToNormalizedIRMapper,
)
from disclosure_anchor.adapters.parsers.mineru.mineru_process import MinerUProcess
from disclosure_anchor.application.ports.parser import ParserOptions, ParserResult
from disclosure_anchor.domain.errors import ParserError


class MinerUDocumentParser:
    """Parse a PDF with MinerU and return parser-neutral NormalizedIR data."""

    def __init__(
        self,
        *,
        process: MinerUProcess,
        reader: MinerUArtifactReader | None = None,
        mapper: MinerUToNormalizedIRMapper | None = None,
        parser_version: str | None = None,
    ) -> None:
        self._process = process
        self._reader = reader or MinerUArtifactReader()
        self._mapper = mapper or MinerUToNormalizedIRMapper()
        self._parser_version = parser_version
        self._version_cache: str | None = parser_version

    def parse(
        self,
        *,
        input_pdf: Path,
        output_dir: Path,
        options: ParserOptions,
        document_metadata: dict[str, Any],
    ) -> ParserResult:
        self._process.run(input_pdf=input_pdf, output_dir=output_dir, options=options)
        artifacts = self._reader.locate(output_dir)
        content_list = self._reader.read_content_list(artifacts.content_list_path)
        parser_version, warnings = self._parser_version_with_warnings()
        parser_info = MinerUParserInfo(
            name="MinerU",
            package_version=parser_version,
            backend=options.backend,
            method=options.method,
            language=options.language,
            formula=options.formula,
            table=options.table,
        )
        normalized_ir = self._mapper.map_content_list(
            content_list=content_list,
            parser_info=parser_info,
            document_metadata=document_metadata,
            parser_artifacts={},
        )
        if warnings:
            normalized_ir["warnings"] = warnings
        return ParserResult(
            parser_name=parser_info.name,
            parser_version=parser_info.package_version,
            parser_backend=parser_info.backend,
            parser_method=parser_info.method,
            artifact_root=artifacts.root,
            content_list_path=artifacts.content_list_path,
            markdown_path=artifacts.markdown_path,
            normalized_ir=normalized_ir,
        )

    def _parser_version_with_warnings(self) -> tuple[str, list[str]]:
        if self._version_cache is not None:
            return self._version_cache, []
        try:
            self._version_cache = self._process.version()
        except ParserError:
            return "unknown", ["version_probe_failed"]
        return self._version_cache, []
