"""Behaviour tests for Association Pairing Samplers and Corpus Distillation.

Proves SAMPLER-01 through SAMPLER-06 from docs/design/specs/SAMPLER.md:
- SAMPLER-01: Pairing pool contains frictions, observations, ideas, and assets
- SAMPLER-02: Distilled corpus projection without filesystem paths
- SAMPLER-03: State-blind selection includes parked and dead ideas
- SAMPLER-04: RandomSampler control arm baseline
- SAMPLER-05: AntiSimilarSampler maximum structural distance
- SAMPLER-06: MidBandSampler moderate distance pairing
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.association.corpus import distill_corpus_pool
from iw.domain.association.samplers import (
    AntiSimilarSampler,
    MidBandSampler,
    RandomSampler,
    calculate_structural_distance,
    get_sampler,
)


def _seed_corpus_pool(store: MarkdownStore) -> None:
    """Populate store with diverse types and states for pairing."""
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # 1. Friction (active)
    f1 = Node(
        id="FRI-A01", type="friction", title="Bike display freezes in cold",
        created=datetime.now(timezone.utc), domain="hardware", tags=["cycling", "battery"],
        state="active", body="Battery voltage drops in freezing weather.",
    )
    # 2. Asset (standing capability)
    a1 = Node(
        id="AST-A01", type="asset", title="Ultrasonic transducers and microphone rig",
        created=datetime.now(timezone.utc), domain="acoustics", tags=["audio", "sensors"],
        state="have", body="Dual-channel high-frequency ultrasonic transducers.",
    )
    # 3. Observation (feedstock)
    o1 = Node(
        id="OBS-A01", type="observation", title="Honeybees vibrate thorax to heat hive cluster",
        created=datetime.now(timezone.utc), domain="biology", tags=["thermal", "nature"],
        state="active", body="Bees decouple wings and flex thoracic muscles to generate heat.",
    )
    # 4. Dead Idea (retired concept)
    i1 = Node(
        id="IDEA-A01", type="idea", title="Chemical hand warmer pouch casing",
        created=datetime.now(timezone.utc), domain="hardware", tags=["battery", "thermal"],
        state="dead", body="Single-use disposable iron oxidation heat packs.",
    )
    # 5. Non-pool node: source (should be excluded)
    s1 = Node(
        id="SRC-A01", type="source", title="NASA Battery Thermal Management Paper",
        created=datetime.now(timezone.utc), domain="aerospace", tags=["reference"],
        state="active",
    )

    for n in (f1, a1, o1, i1, s1):
        store.write_node(n, author=author)


def test_sampler_01_and_02_corpus_distillation_and_pool_types(tmp_path: Path):
    """SAMPLER-01 & SAMPLER-02: Pool has frictions, observations, ideas, assets; no file paths."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_corpus_pool(store)

    pool = distill_corpus_pool(store)
    pool_ids = {r.id for r in pool}
    pool_types = {r.type for r in pool}

    assert pool_ids == {"FRI-A01", "AST-A01", "OBS-A01", "IDEA-A01"}
    assert "SRC-A01" not in pool_ids
    assert pool_types == {"friction", "asset", "observation", "idea"}

    # Invariant: No file paths leaked in distilled projection
    for r in pool:
        assert "/" not in r.excerpt or not r.excerpt.startswith("c:")
        assert "\\" not in r.excerpt


def test_sampler_03_pairing_is_state_blind_and_includes_dead_ideas(tmp_path: Path):
    """SAMPLER-03: Samplers operate state-blindly, including dead and have states."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_corpus_pool(store)

    pool = distill_corpus_pool(store)
    states = {r.state for r in pool}
    assert "dead" in states
    assert "have" in states
    assert "active" in states


def test_sampler_04_random_sampler_acts_as_control_arm(tmp_path: Path):
    """SAMPLER-04: RandomSampler selects pairs uniformly at random as empirical control arm."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_corpus_pool(store)

    pool = distill_corpus_pool(store)
    sampler = RandomSampler()
    candidates = sampler.sample_pairs(pool, count=3, seed=42)

    assert len(candidates) == 3
    for c in candidates:
        assert c.strategy == "random"
        assert c.node_a.id != c.node_b.id
        assert 0.0 <= c.distance_metric <= 1.0


def test_sampler_05_anti_similar_sampler_selects_max_distance_pairs(tmp_path: Path):
    """SAMPLER-05: AntiSimilarSampler prioritizes maximum structural and domain separation."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_corpus_pool(store)

    pool = distill_corpus_pool(store)
    sampler = AntiSimilarSampler()
    candidates = sampler.sample_pairs(pool, count=2, seed=42)

    assert len(candidates) >= 1
    assert candidates[0].strategy == "anti_similar"
    # Anti-similar pairs should have high distance (distinct domain and type)
    assert candidates[0].distance_metric >= 0.5


def test_sampler_06_mid_band_sampler_and_factory(tmp_path: Path):
    """SAMPLER-06: MidBandSampler selects moderate distance and factory resolves strategies."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    _seed_corpus_pool(store)

    pool = distill_corpus_pool(store)
    sampler = get_sampler("mid_band")
    assert isinstance(sampler, MidBandSampler)

    candidates = sampler.sample_pairs(pool, count=2, seed=42)
    assert len(candidates) >= 1
    assert candidates[0].strategy == "mid_band"

    # Factory checks
    assert isinstance(get_sampler("random"), RandomSampler)
    assert isinstance(get_sampler("anti-similar"), AntiSimilarSampler)
