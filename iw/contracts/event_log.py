"""Event log protocol definition."""

from typing import Any, Protocol, runtime_checkable
from iw.contracts.models import Author, EventRecord


@runtime_checkable
class EventLogProtocol(Protocol):
    """Protocol for append-only lifecycle event recording."""

    def append(
        self,
        kind: str,
        subject_id: str | None = None,
        author: Author | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        """Append an event record to the log."""
        ...

    def read_events(self, limit: int | None = None) -> list[EventRecord]:
        """Read recorded events in chronological order."""
        ...
