"""Contracts for pluggable format and content extractors."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ExtractionResult:
    """Represents text and metadata extracted from a file or byte stream."""

    text: str
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    content_type: str = "text/plain"
    warnings: list[str] = field(default_factory=list)


@runtime_checkable
class ExtractorProtocol(Protocol):
    """Protocol for single-format or multi-format content extractors."""

    def supports_mime_type(self, mime_type: str) -> bool:
        """Return True if this extractor can process the given MIME type."""
        ...

    def supports_extension(self, extension: str) -> bool:
        """Return True if this extractor can process the given file extension."""
        ...

    def extract_from_bytes(
        self,
        data: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ExtractionResult:
        """Extract text and metadata from raw bytes."""
        ...

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        """Extract text and metadata from a local file path."""
        ...


@runtime_checkable
class ExtractorRegistryProtocol(Protocol):
    """Protocol for managing and routing between registered extractors."""

    def register_extractor(self, extractor: ExtractorProtocol) -> None:
        """Register an extractor instance."""
        ...

    def extract(
        self,
        source: Path | bytes,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> ExtractionResult:
        """Route to appropriate extractor and extract text."""
        ...
