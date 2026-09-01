"""Scout standing interest service implementation."""

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
from iw.contracts.scout import ScoutOffer, ScoutProtocol, StandingInterest
from iw.core.ids import allocate_next_id
from iw.domain.scout.models import interest_from_dict, interest_to_dict


class ScoutService:
    """Manages standing interests and generates on-demand recommendation offers."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_all({})

    def _load_all(self) -> dict[str, StandingInterest]:
        if not self.storage_path.exists():
            return {}
        with open(self.storage_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {item["id"]: interest_from_dict(item) for item in data.values()}

    def _save_all(self, interests: dict[str, StandingInterest]) -> None:
        serialized = {k: interest_to_dict(v) for k, v in interests.items()}
        parent = self.storage_path.parent
        with tempfile.NamedTemporaryFile("w", dir=parent, delete=False, encoding="utf-8") as tf:
            json.dump(serialized, tf, indent=2)
            tmp_name = tf.name
        Path(tmp_name).replace(self.storage_path)

    def register_interest(
        self,
        topic: str,
        domain: str,
        staleness_interval_days: int = 30,
        subject_id: str | None = None,
        tags: list[str] | None = None,
    ) -> StandingInterest:
        interests = self._load_all()
        new_id = allocate_next_id("SCT", list(interests.keys()))
        now = datetime.now(timezone.utc)
        interest = StandingInterest(
            id=new_id,
            topic=topic,
            domain=domain,
            staleness_interval_days=max(1, staleness_interval_days),
            created_at=now,
            subject_id=subject_id,
            active=True,
            tags=tags or [],
        )
        interests[interest.id] = interest
        self._save_all(interests)
        return interest

    def get_interest(self, interest_id: str) -> StandingInterest | None:
        return self._load_all().get(interest_id)

    def list_interests(self, active_only: bool = True) -> list[StandingInterest]:
        all_items = list(self._load_all().values())
        if active_only:
            return [i for i in all_items if i.active]
        return all_items

    def get_stale_offers(self, as_of: datetime | None = None) -> list[ScoutOffer]:
        now = as_of or datetime.now(timezone.utc)
        offers: list[ScoutOffer] = []
        for interest in self.list_interests(active_only=True):
            timestamps = [interest.created_at]
            if interest.last_swept_at:
                timestamps.append(interest.last_swept_at)
            if interest.last_dismissed_at:
                timestamps.append(interest.last_dismissed_at)
            baseline = max(timestamps)
            elapsed_days = (now - baseline).days
            if elapsed_days >= interest.staleness_interval_days:
                offers.append(
                    ScoutOffer(
                        interest=interest,
                        days_stale=elapsed_days,
                        suggested_activity="observation-sweep@1",
                        reason=f"Standing interest '{interest.topic}' last reviewed {elapsed_days}d ago.",
                    )
                )
        return offers

    def dismiss_interest(
        self,
        interest_id: str,
        as_of: datetime | None = None,
    ) -> StandingInterest:
        interests = self._load_all()
        if interest_id not in interests:
            raise KeyError(f"Standing interest '{interest_id}' not found")
        item = interests[interest_id]
        updated = StandingInterest(
            id=item.id,
            topic=item.topic,
            domain=item.domain,
            staleness_interval_days=item.staleness_interval_days,
            created_at=item.created_at,
            subject_id=item.subject_id,
            last_swept_at=item.last_swept_at,
            last_dismissed_at=as_of or datetime.now(timezone.utc),
            active=item.active,
            tags=item.tags,
        )
        interests[interest_id] = updated
        self._save_all(interests)
        return updated

    def record_sweep_dispatched(
        self,
        interest_id: str,
        as_of: datetime | None = None,
    ) -> StandingInterest:
        interests = self._load_all()
        if interest_id not in interests:
            raise KeyError(f"Standing interest '{interest_id}' not found")
        item = interests[interest_id]
        updated = StandingInterest(
            id=item.id,
            topic=item.topic,
            domain=item.domain,
            staleness_interval_days=item.staleness_interval_days,
            created_at=item.created_at,
            subject_id=item.subject_id,
            last_swept_at=as_of or datetime.now(timezone.utc),
            last_dismissed_at=item.last_dismissed_at,
            active=item.active,
            tags=item.tags,
        )
        interests[interest_id] = updated
        self._save_all(interests)
        return updated

    def deactivate_interest(self, interest_id: str) -> StandingInterest:
        interests = self._load_all()
        if interest_id not in interests:
            raise KeyError(f"Standing interest '{interest_id}' not found")
        item = interests[interest_id]
        updated = StandingInterest(
            id=item.id,
            topic=item.topic,
            domain=item.domain,
            staleness_interval_days=item.staleness_interval_days,
            created_at=item.created_at,
            subject_id=item.subject_id,
            last_swept_at=item.last_swept_at,
            last_dismissed_at=item.last_dismissed_at,
            active=False,
            tags=item.tags,
        )
        interests[interest_id] = updated
        self._save_all(interests)
        return updated
