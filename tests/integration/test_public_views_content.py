"""Public views return committed data with the expected projection."""

from __future__ import annotations

import unittest

from sqlalchemy import text

from disclosure_anchor.adapters.db.postgres.unit_of_work import SqlAlchemyUnitOfWork
from disclosure_anchor.domain import entities as e
from disclosure_anchor.domain import ids
from tests.integration._support import engine_or_skip


class PublicViewContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = engine_or_skip()
        self.document_id = ids.new_document_id()
        self.run_id = ids.new_processing_run_id()
        self.unit_id = ids.new_document_unit_id()

    def tearDown(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                text("DELETE FROM disclosure_core.document_unit WHERE document_unit_id = :v"),
                {"v": self.unit_id},
            )
            conn.execute(
                text("DELETE FROM disclosure_core.processing_run WHERE processing_run_id = :v"),
                {"v": self.run_id},
            )
            conn.execute(
                text("DELETE FROM disclosure_core.document WHERE document_id = :v"),
                {"v": self.document_id},
            )
        self.engine.dispose()

    def _seed(self) -> None:
        with SqlAlchemyUnitOfWork(engine=self.engine) as uow:
            uow.documents.add(
                e.Document(
                    document_id=self.document_id,
                    status="published",
                    provider="cninfo",
                    provider_document_id="1225087169",
                    raw_file_hash="sha256:abc",
                    raw_file_relpath="raw_documents/cninfo/ab/x.pdf",
                )
            )
            uow.processing_runs.add(
                e.ProcessingRun(
                    processing_run_id=self.run_id,
                    document_id=self.document_id,
                    run_kind="full",
                    status="succeeded",
                    is_active=True,
                )
            )
            uow.document_units.add(
                e.DocumentUnit(
                    document_unit_id=self.unit_id,
                    document_id=self.document_id,
                    processing_run_id=self.run_id,
                    unit_kind="table",
                    order_index=0,
                    heading_path=["第八节 财务报告", "应收账款"],
                    semantic_key="receivable_aging",
                    payload={"unit": "元", "rows": [["合计", "1"]]},
                    content_hash="sha256:unit",
                )
            )
            uow.commit()

    def test_document_units_and_source_refs_views(self) -> None:
        self._seed()
        with self.engine.connect() as conn:
            unit_row = conn.execute(
                text(
                    "SELECT unit_kind, semantic_key, payload "
                    "FROM disclosure_public.document_units_v1 "
                    "WHERE document_unit_id = :v"
                ),
                {"v": self.unit_id},
            ).mappings().one()
            self.assertEqual(unit_row["unit_kind"], "table")
            self.assertEqual(unit_row["semantic_key"], "receivable_aging")
            self.assertEqual(unit_row["payload"], {"unit": "元", "rows": [["合计", "1"]]})

            ref_row = conn.execute(
                text(
                    "SELECT provider, provider_document_id, raw_file_hash, "
                    "unit_content_hash FROM disclosure_public.source_refs_v1 "
                    "WHERE document_unit_id = :v"
                ),
                {"v": self.unit_id},
            ).mappings().one()
            self.assertEqual(ref_row["provider"], "cninfo")
            self.assertEqual(ref_row["provider_document_id"], "1225087169")
            self.assertEqual(ref_row["raw_file_hash"], "sha256:abc")
            self.assertEqual(ref_row["unit_content_hash"], "sha256:unit")

            doc_row = conn.execute(
                text(
                    "SELECT status, raw_file_hash FROM disclosure_public.documents_v1 "
                    "WHERE document_id = :v"
                ),
                {"v": self.document_id},
            ).mappings().one()
            self.assertEqual(doc_row["status"], "published")
            # raw_file_relpath must not be a column in the view.
            self.assertNotIn("raw_file_relpath", doc_row)


if __name__ == "__main__":
    unittest.main()
