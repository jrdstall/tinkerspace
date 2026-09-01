"""Contracts for the Bookkeeper content-addressed storage adapter."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StoredArtifact:
    """Represents a content-addressed file in the Bookkeeper store."""

    content_id: str
    size_bytes: int
    mime_type: str
    stored_at: datetime
    original_filename: str | None = None
    renditions: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class BookkeeperProtocol(Protocol):
    """Protocol for immutable content-addressed storage of raw files and renditions."""

    def store_bytes(
        self,
        data: bytes,
        mime_type: str,
        original_filename: str | None = None,
    ) -> StoredArtifact:
        """Store raw byte data and return the StoredArtifact metadata."""
        ...

    def store_file(
        self,
        source_path: Path,
        mime_type: str | None = None,
    ) -> StoredArtifact:
        """Store a file from a local path and return StoredArtifact metadata."""
        ...

    def get_bytes(self, content_id: str) -> bytes:
        """Retrieve the exact bytes for a content ID."""
        ...

    def get_path(self, content_id: str) -> Path:
        """Retrieve the local file system path for a stored artifact."""
        ...

    def has_content(self, content_id: str) -> bool:
        """Check whether a content ID exists in the store."""
        ...

    def register_rendition(
        self,
        content_id: str,
        rendition_name: str,
        rendition_bytes: bytes,
        mime_type: str,
    ) -> str:
        """Store a derived rendition and link it to the primary content ID."""
        ...

    def get_rendition_bytes(
        self,
        content_id: str,
        rendition_name: str,
    ) -> bytes | None:
        """Retrieve bytes of a named rendition for a content ID."""
        ...
