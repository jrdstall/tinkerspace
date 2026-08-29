"""File-based append-only event log implementation.

Layer 1 Core component storing immutable JSONL event records in the vault.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import uuid

from iw.contracts.event_log import EventLogProtocol
from iw.contracts.models import Author, AuthorKind, EventRecord


class FileEventLog(EventLogProtocol):
    """Append-only event log written to events.jsonl."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path

    def append(
        self,
        kind: str,
        subject_id: str | None = None,
        author: Author | None = None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        """Append an immutable event record to the JSONL log file."""
        now = datetime.now(timezone.utc)
        event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
        record = EventRecord(
            id=event_id,
            timestamp=now,
            kind=kind,
            subject_id=subject_id,
            author=author,
            payload=payload if payload is not None else {},
        )
        self._write_record(record)
        return record

    def read_events(self, limit: int | None = None) -> list[EventRecord]:
        """Read all event records from the JSONL log file in order."""
        if not self.log_path.exists():
            return []

        records: list[EventRecord] = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    records.append(self._deserialize_line(line_str))

        if limit is not None and limit > 0:
            return records[-limit:]
        return records

    def _write_record(self, record: EventRecord) -> None:
        """Serialize and append record to disk."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "id": record.id,
            "timestamp": record.timestamp.isoformat(),
            "kind": record.kind,
            "subject_id": record.subject_id,
            "author": self._serialize_author(record.author),
            "payload": record.payload,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

    def _serialize_author(self, author: Author | None) -> dict[str, Any] | None:
        """Convert Author to dictionary."""
        if author is None:
            return None
        return {
            "kind": author.kind.value,
            "courier": author.courier,
            "requested_model": author.requested_model,
            "declared_model": author.declared_model,
        }

    def _deserialize_line(self, line: str) -> EventRecord:
        """Parse JSON line into an EventRecord."""
        raw = json.loads(line)
        author_data = raw.get("author")
        author: Author | None = None
        if author_data:
            author = Author(
                kind=AuthorKind(author_data["kind"]),
                courier=author_data.get("courier", "web-ui"),
                requested_model=author_data.get("requested_model"),
                declared_model=author_data.get("declared_model"),
            )

        return EventRecord(
            id=raw["id"],
            timestamp=datetime.fromisoformat(raw["timestamp"]),
            kind=raw["kind"],
            subject_id=raw.get("subject_id"),
            author=author,
            payload=raw.get("payload", {}),
        )
