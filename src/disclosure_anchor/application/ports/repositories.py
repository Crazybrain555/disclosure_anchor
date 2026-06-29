"""Repository ports.

Repositories persist and load domain entities. Concrete implementations live in
``adapters/db/postgres``. Use cases depend only on these protocols.
"""

from __future__ import annotations

from typing import Optional, Protocol

from disclosure_anchor.domain.entities import (
    Company,
    Document,
    DocumentUnit,
    OutboxEvent,
    ProcessingRun,
    Security,
    SourceAccess,
    SourceCheckpoint,
    TrackedCompany,
)


class CompanyRepository(Protocol):
    def add(self, company: Company) -> Company: ...
    def get(self, company_id: str) -> Optional[Company]: ...


class SecurityRepository(Protocol):
    def add(self, security: Security) -> Security: ...
    def get(self, security_id: str) -> Optional[Security]: ...


class TrackedCompanyRepository(Protocol):
    def add(self, tracked_company: TrackedCompany) -> TrackedCompany: ...
    def get(self, tracked_company_id: str) -> Optional[TrackedCompany]: ...


class SourceAccessRepository(Protocol):
    def add(self, source_access: SourceAccess) -> SourceAccess: ...
    def get(self, source_access_id: str) -> Optional[SourceAccess]: ...


class SourceCheckpointRepository(Protocol):
    def add(self, checkpoint: SourceCheckpoint) -> SourceCheckpoint: ...
    def get(self, source_checkpoint_id: str) -> Optional[SourceCheckpoint]: ...


class DocumentRepository(Protocol):
    def add(self, document: Document) -> Document: ...
    def get(self, document_id: str) -> Optional[Document]: ...


class ProcessingRunRepository(Protocol):
    def add(self, run: ProcessingRun) -> ProcessingRun: ...
    def get(self, processing_run_id: str) -> Optional[ProcessingRun]: ...


class DocumentUnitRepository(Protocol):
    def add(self, unit: DocumentUnit) -> DocumentUnit: ...
    def get(self, document_unit_id: str) -> Optional[DocumentUnit]: ...


class OutboxRepository(Protocol):
    def add(self, event: OutboxEvent) -> OutboxEvent: ...
    def get(self, event_id: str) -> Optional[OutboxEvent]: ...
