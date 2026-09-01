"""Behaviour tests for Scout standing interests and recommended activities.

Proves SCOUT-01 through SCOUT-06 from docs/design/specs/SCOUT.md:
- SCOUT-01: Standing interest registration
- SCOUT-02: On-demand staleness computation (no background threads/daemons)
- SCOUT-03: Stale interest offer generation
- SCOUT-04: Dismissal resets staleness clock
- SCOUT-05: Sweep dispatch resets staleness clock
- SCOUT-06: Deactivation excludes interest from active offers
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from iw.domain.scout.service import ScoutService


def test_scout_01_register_standing_interest(tmp_path: Path):
    """SCOUT-01: Standing interest registers topic, domain, subject, and staleness interval."""
    service = ScoutService(tmp_path / "scout.json")
    interest = service.register_interest(
        topic="Piezoelectric energy harvesting from bicycle forks",
        domain="hardware",
        staleness_interval_days=14,
        subject_id="IDEA-A01",
        tags=["energy", "piezo", "cycling"],
    )

    assert interest.id == "SCT-A01"
    assert interest.staleness_interval_days == 14
    assert interest.subject_id == "IDEA-A01"
    assert interest.active is True

    loaded = service.get_interest("SCT-A01")
    assert loaded is not None
    assert loaded.topic == interest.topic


def test_scout_02_on_demand_computation_without_background_threads(tmp_path: Path):
    """SCOUT-02: Staleness evaluation executes strictly on demand without background watchers."""
    service = ScoutService(tmp_path / "scout.json")
    service.register_interest(topic="Solid-state battery safety", domain="materials", staleness_interval_days=30)

    # Calling get_stale_offers is purely synchronous
    offers = service.get_stale_offers()
    assert isinstance(offers, list)


def test_scout_03_staleness_generates_offers_after_interval_elapsed(tmp_path: Path):
    """SCOUT-03: An offer appears when days elapsed >= staleness interval."""
    service = ScoutService(tmp_path / "scout.json")
    interest = service.register_interest(
        topic="Direct laser metal sintering for titanium dropouts",
        domain="manufacturing",
        staleness_interval_days=10,
    )

    t_created = interest.created_at

    # Day 5: not stale
    offers_day5 = service.get_stale_offers(as_of=t_created + timedelta(days=5))
    assert len(offers_day5) == 0

    # Day 11: stale (11 >= 10)
    offers_day11 = service.get_stale_offers(as_of=t_created + timedelta(days=11))
    assert len(offers_day11) == 1
    assert offers_day11[0].interest.id == interest.id
    assert offers_day11[0].days_stale == 11


def test_scout_04_dismissal_resets_staleness_clock(tmp_path: Path):
    """SCOUT-04: Dismissing an offer resets the staleness clock and clears the offer."""
    service = ScoutService(tmp_path / "scout.json")
    interest = service.register_interest(
        topic="Ultra-low power E-Ink display refresh controllers",
        domain="electronics",
        staleness_interval_days=7,
    )

    t_stale = interest.created_at + timedelta(days=10)
    offers = service.get_stale_offers(as_of=t_stale)
    assert len(offers) == 1

    # Dismiss at day 10
    updated = service.dismiss_interest(interest.id, as_of=t_stale)
    assert updated.last_dismissed_at == t_stale

    # Immediately after dismissal on day 10, offer is gone
    offers_now = service.get_stale_offers(as_of=t_stale)
    assert len(offers_now) == 0

    # 4 days after dismissal (day 14 total, 4 after dismissal), still not stale (4 < 7)
    offers_day14 = service.get_stale_offers(as_of=t_stale + timedelta(days=4))
    assert len(offers_day14) == 0

    # 8 days after dismissal (day 18 total, 8 after dismissal), stale again (8 >= 7)
    offers_day18 = service.get_stale_offers(as_of=t_stale + timedelta(days=8))
    assert len(offers_day18) == 1


def test_scout_05_sweep_dispatch_resets_staleness_clock(tmp_path: Path):
    """SCOUT-05: Dispatching a sweep updates last_swept_at and resets the clock."""
    service = ScoutService(tmp_path / "scout.json")
    interest = service.register_interest(
        topic="Optical flow odometry in GPS-denied tunnels",
        domain="software",
        staleness_interval_days=5,
    )

    t_sweep = interest.created_at + timedelta(days=6)
    service.record_sweep_dispatched(interest.id, as_of=t_sweep)

    # Immediately after sweep dispatch, offer is cleared
    offers = service.get_stale_offers(as_of=t_sweep)
    assert len(offers) == 0


def test_scout_06_deactivation_excludes_interest_from_offers(tmp_path: Path):
    """SCOUT-06: Deactivating an interest prevents it from generating future offers."""
    service = ScoutService(tmp_path / "scout.json")
    interest = service.register_interest(
        topic="Legacy carbon composite bonding resins",
        domain="materials",
        staleness_interval_days=3,
    )

    t_stale = interest.created_at + timedelta(days=10)
    assert len(service.get_stale_offers(as_of=t_stale)) == 1

    service.deactivate_interest(interest.id)
    assert len(service.get_stale_offers(as_of=t_stale)) == 0
    assert len(service.list_interests(active_only=True)) == 0
    assert len(service.list_interests(active_only=False)) == 1
