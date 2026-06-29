"""NormalizedIR v1 contract checks."""

import json
import unittest
from pathlib import Path

from disclosure_anchor.adapters.parsers.mineru.artifact_reader import MinerUArtifactReader
from disclosure_anchor.adapters.parsers.mineru.mapper_to_ir import (
    MinerUParserInfo,
    MinerUToNormalizedIRMapper,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "contracts" / "normalized_ir" / "normalized_ir.v1.json"
PHASE00_ROOT = REPO_ROOT / "tests" / "fixtures" / "phase00"


def _content_list_from_ref(sample_key: str) -> Path | None:
    ref = PHASE00_ROOT / sample_key / "parser_artifacts_ref.txt"
    if not ref.is_file():
        return None
    for line in ref.read_text(encoding="utf-8").splitlines():
        if line.startswith("Content list: "):
            return Path(line.removeprefix("Content list: ").strip())
    return None


class NormalizedIRContractTests(unittest.TestCase):
    def test_schema_has_phase04_required_contract_shape(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        required = set(schema["required"])
        self.assertIn("parser_artifacts", required)
        self.assertIn("elements", required)
        element_required = set(schema["properties"]["elements"]["items"]["required"])
        self.assertEqual(
            element_required,
            {"ir_id", "kind", "order_index", "source_item_index"},
        )

    def test_phase00_golden_fixtures_match_schema_required_keys(self) -> None:
        for sample_key in ("annual_report", "ir_activity", "short_announcement"):
            data = json.loads(
                (PHASE00_ROOT / sample_key / "normalized_ir.v1.json").read_text(
                    encoding="utf-8"
                )
            )
            missing = set(json.loads(SCHEMA_PATH.read_text())["required"]) - data.keys()
            self.assertFalse(missing, f"{sample_key} missing keys: {sorted(missing)}")
            self.assertGreater(len(data["elements"]), 0, sample_key)
            for index, element in enumerate(data["elements"][:20]):
                for key in ("ir_id", "kind", "order_index", "source_item_index"):
                    self.assertIn(key, element, f"{sample_key}:{index}")

    def test_mapper_accepts_real_phase00_mineru_content_list_when_available(self) -> None:
        content_list_path = _content_list_from_ref("short_announcement")
        if content_list_path is None or not content_list_path.is_file():
            self.skipTest("local Phase 00 MinerU content_list artifact is absent")

        reader = MinerUArtifactReader()
        content_list = reader.read_content_list(content_list_path)
        normalized = MinerUToNormalizedIRMapper().map_content_list(
            content_list=content_list,
            parser_info=MinerUParserInfo(
                name="MinerU",
                package_version="3.4.0",
                backend="pipeline",
                method="auto",
                language="ch",
                formula=False,
                table=True,
            ),
            document_metadata={
                "document_id": "phase04_real_mapper_smoke",
                "source_pdf": "tmp/sample_filings/real.pdf",
                "title": "real mapper smoke",
                "sample_key": "short_announcement",
            },
            parser_artifacts={
                "content_list_relpath": "parser_artifacts/short/content_list.json"
            },
        )
        self.assertEqual(len(normalized["elements"]), len(content_list))
        self.assertEqual(normalized["elements"][0]["text"], content_list[0]["text"])
        self.assertEqual(normalized["parsed_pages"]["start_page_no"], 1)
        self.assertGreaterEqual(normalized["parsed_pages"]["end_page_no"], 1)


if __name__ == "__main__":
    unittest.main()
