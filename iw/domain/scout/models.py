"""Serialization models and helper utilities for Scout standing interests."""

from datetime import datetime
from typing import Any
from iw.contracts.scout import StandingInterest


def interest_to_dict(interest: StandingInterest) -> dict[str, Any]:
    """Convert StandingInterest to a JSON-serializable dictionary."""
    return {
        "id": interest.id,
        "topic": interest.topic,
        "domain": interest.domain,
        "staleness_interval_days": interest.staleness_interval_days,
        "created_at": interest.created_at.isoformat(),
        "subject_id": interest.subject_id,
        "last_swept_at": interest.last_swept_at.isoformat() if interest.last_swept_at else None,
        "last_dismissed_at": interest.last_dismissed_at.isoformat() if interest.last_dismissed_at else None,
        "active": interest.active,
        "tags": interest.tags,
    }


def interest_from_dict(data: dict[str, Any]) -> StandingInterest:
    """Reconstruct StandingInterest from a dictionary."""
    return StandingInterest(
        id=data["id"],
        topic=data["topic"],
        domain=data["domain"],
        staleness_interval_days=data["staleness_interval_days"],
        created_at=datetime.fromisoformat(data["created_at"]),
        subject_id=data.get("subject_id"),
        last_swept_at=datetime.fromisoformat(data["last_swept_at"]) if data.get("last_swept_at") else None,
        last_dismissed_at=datetime.fromisoformat(data["last_dismissed_at"]) if data.get("last_dismissed_at") else None,
        active=data.get("active", True),
        tags=data.get("tags", []),
    )
