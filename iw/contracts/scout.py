"""Contracts for Scout standing interests and recommended activities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StandingInterest:
    """Represents a standing research interest with a staleness interval."""

    id: str
    topic: str
    domain: str
    staleness_interval_days: int
    created_at: datetime
    subject_id: str | None = None
    last_swept_at: datetime | None = None
    last_dismissed_at: datetime | None = None
    active: bool = True
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScoutOffer:
    """Represents a recommended sweep offer presented to Jared upon arrival."""

    interest: StandingInterest
    days_stale: int
    suggested_activity: str = "observation-sweep@1"
    reason: str = ""


@runtime_checkable
class ScoutProtocol(Protocol):
    """Protocol for managing standing interests and computing recommended activity offers."""

    def register_interest(
        self,
        topic: str,
        domain: str,
        staleness_interval_days: int = 30,
        subject_id: str | None = None,
        tags: list[str] | None = None,
    ) -> StandingInterest:
        """Register a new standing interest."""
        ...

    def get_interest(self, interest_id: str) -> StandingInterest | None:
        """Get an existing standing interest by ID."""
        ...

    def list_interests(self, active_only: bool = True) -> list[StandingInterest]:
        """List registered standing interests."""
        ...

    def get_stale_offers(self, as_of: datetime | None = None) -> list[ScoutOffer]:
        """Compute all currently stale standing interest offers."""
        ...

    def dismiss_interest(
        self,
        interest_id: str,
        as_of: datetime | None = None,
    ) -> StandingInterest:
        """Dismiss a stale offer, resetting its staleness clock."""
        ...

    def record_sweep_dispatched(
        self,
        interest_id: str,
        as_of: datetime | None = None,
    ) -> StandingInterest:
        """Record that a sweep order was raised, resetting its staleness clock."""
        ...

    def deactivate_interest(self, interest_id: str) -> StandingInterest:
        """Deactivate a standing interest."""
        ...
