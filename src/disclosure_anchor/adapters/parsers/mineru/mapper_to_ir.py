"""Map MinerU content_list artifacts to parser-neutral NormalizedIR v1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MinerUParserInfo:
    name: str
    package_version: str
    backend: str
    method: str
    language: str
    formula: bool
    table: bool


def _page_no(item: dict[str, Any]) -> int | None:
    page_idx = item.get("page_idx")
    return page_idx + 1 if isinstance(page_idx, int) else None


def _parsed_pages(items: list[dict[str, Any]]) -> dict[str, Any]:
    page_numbers = [page for item in items if (page := _page_no(item)) is not None]
    if not page_numbers:
        return {"start_page_no": None, "end_page_no": None, "full_pdf": True}
    return {
        "start_page_no": min(page_numbers),
        "end_page_no": max(page_numbers),
        "full_pdf": True,
    }


def _table_html(item: dict[str, Any]) -> str | None:
    value = item.get("table_body")
    if value is None:
        value = item.get("table_html")
    return str(value) if value is not None else None


def _image_path(item: dict[str, Any]) -> str | None:
    value = item.get("img_path")
    if value is None:
        value = item.get("image_path")
    return str(value) if value else None


class MinerUToNormalizedIRMapper:
    """Convert the stable MinerU content_list shape into NormalizedIR."""

    def map_content_list(
        self,
        *,
        content_list: list[dict[str, Any]],
        parser_info: MinerUParserInfo,
        document_metadata: dict[str, Any],
        parser_artifacts: dict[str, str],
    ) -> dict[str, Any]:
        sample_key = document_metadata.get("sample_key")
        document_id = str(document_metadata["document_id"])
        elements = [
            self._map_item(
                item=item,
                index=index,
                document_id=document_id,
                sample_key=str(sample_key) if sample_key else document_id,
            )
            for index, item in enumerate(content_list)
        ]
        return {
            "contract_version": "normalized_ir.v1",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_id": document_id,
            "source_pdf": str(document_metadata.get("source_pdf", "")),
            "title": document_metadata.get("title"),
            "sample_key": sample_key,
            "sample_role": document_metadata.get("sample_role"),
            "parser": {
                "name": parser_info.name,
                "package_version": parser_info.package_version,
                "backend": parser_info.backend,
                "method": parser_info.method,
                "language": parser_info.language,
                "formula": parser_info.formula,
                "table": parser_info.table,
            },
            "parser_artifacts": parser_artifacts,
            "parsed_pages": _parsed_pages(content_list),
            "elements": elements,
        }

    def _map_item(
        self,
        *,
        item: dict[str, Any],
        index: int,
        document_id: str,
        sample_key: str,
    ) -> dict[str, Any]:
        kind = str(item.get("type") or "unknown")
        element: dict[str, Any] = {
            "ir_id": f"{sample_key}_ir_{index:04d}",
            "kind": kind,
            "order_index": index,
            "source_item_index": index,
        }
        for key in ("page_idx", "bbox", "text_level"):
            if key in item:
                element[key] = item[key]
        if (page_no := _page_no(item)) is not None:
            element["page_no"] = page_no
        if "text" in item:
            element["text"] = item["text"]
        if kind == "table":
            element["table_caption"] = item.get("table_caption") or []
            element["table_footnote"] = item.get("table_footnote") or []
            element["table_html"] = _table_html(item) or ""
        if image_path := _image_path(item):
            element["image_path"] = image_path
        if "image" in item and "image_path" not in element:
            element["image_path"] = str(item["image"])
        element["document_id"] = document_id
        return element


def artifact_relpath_map(
    *,
    artifact_root_relpath: Path,
    content_list_relpath: Path,
    markdown_relpath: Path | None,
) -> dict[str, str]:
    artifacts = {
        "artifact_root_relpath": str(artifact_root_relpath),
        "content_list_relpath": str(content_list_relpath),
    }
    if markdown_relpath is not None:
        artifacts["markdown_relpath"] = str(markdown_relpath)
    return artifacts
