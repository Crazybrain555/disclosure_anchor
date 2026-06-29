"""Common domain value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderRef:
    provider: str
    provider_document_id: str

    def __post_init__(self) -> None:
        if not self.provider:
            raise ValueError("provider is required")
        if not self.provider_document_id:
            raise ValueError("provider_document_id is required")


@dataclass(frozen=True)
class ContentHash:
    algorithm: str
    digest: str

    def __post_init__(self) -> None:
        if self.algorithm != "sha256":
            raise ValueError("only sha256 is supported")
        if not self.digest:
            raise ValueError("digest is required")

    @classmethod
    def parse(cls, value: str) -> "ContentHash":
        algorithm, separator, digest = value.partition(":")
        if not separator:
            raise ValueError("hash must use '<algorithm>:<digest>' format")
        return cls(algorithm=algorithm, digest=digest.lower())

    def __str__(self) -> str:
        return f"{self.algorithm}:{self.digest}"
