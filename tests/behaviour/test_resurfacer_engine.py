"""Behaviour tests for Resurfacer Engine, Dormancy Scoring, and Observation Sweeps.

Proves RESURF-01 through RESURF-06 from docs/design/specs/RESURF.md:
- RESURF-01: Dormancy calculation across recency, isolation, and domain neglect
- RESURF-02: Observation clustering into candidate sweep groups
- RESURF-03: Ranking and surfacing corpus islands
- RESURF-04: observation-sweep@1 activity template validation
- RESURF-05: Resurfaced node metadata and explanatory reasons
- RESURF-06: Event audit logging for resurfacing sweeps
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml

from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.resurfacer.engine import ResurfacerEngine, calculate_dormancy_score


def _setup_resurfacer_fixture(tmp_path: Path) -> tuple[MarkdownStore, ResurfacerEngine]:
    """Setup store and populate with varying ages and connectivity."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    engine = ResurfacerEngine(store=store)

    now = datetime.now(timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # 1. Fresh connected node (low dormancy)
    n1 = Node(
        id="IDEA-A01", type="idea", title="Active Connected Idea",
        created=now, domain="software", tags=["active"], last_touched=now,
        edges=[Edge(from_id="IDEA-A01", to_id="FRI-A01", relation="relates_to", created=now, author=author)],
    )

    # 2. Old unlinked asset (high dormancy)
    forty_days_ago = now - timedelta(days=40)
    n2 = Node(
        id="AST-A01", type="asset", title="Forgotten Laser Rangefinder",
        created=forty_days_ago, domain="optics", tags=["hardware"], last_touched=forty_days_ago,
        edges=[],
    )

    # 3. Two observations in biology (candidate for sweep)
    twenty_days_ago = now - timedelta(days=20)
    o1 = Node(
        id="OBS-A01", type="observation", title="Mycelium network nutrient routing",
        created=twenty_days_ago, domain="biology", tags=["fungi", "routing"], last_touched=twenty_days_ago,
    )
    o2 = Node(
        id="OBS-A02", type="observation", title="Ant colony bridge building",
        created=twenty_days_ago, domain="biology", tags=["insects", "routing"], last_touched=twenty_days_ago,
    )

    for node in (n1, n2, o1, o2):
        store.write_node(node, author=author)

    return store, engine


def test_resurf_01_dormancy_score_penalizes_age_and_isolation():
    """RESURF-01: calculate_dormancy_score calculates high score for isolated aged node."""
    now = datetime.now(timezone.utc)
    domain_counts = {"optics": 1, "software": 10}

    auth = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    fresh_node = Node(
        id="IDEA-01", type="idea", title="Fresh", domain="software", tags=["test"],
        created=now, last_touched=now, edges=[Edge("IDEA-01", "FRI-01", "relates_to", now, auth)],
    )
    score_fresh, days_fresh, _ = calculate_dormancy_score(fresh_node, now, domain_counts)
    assert score_fresh <= 0.3
    assert days_fresh == 0

    # Old isolated node in rare domain
    old_time = now - timedelta(days=50)
    old_node = Node(
        id="AST-01", type="asset", title="Old Laser", domain="optics", tags=["optics"],
        created=old_time, last_touched=old_time, edges=[],
    )
    score_old, days_old, reason_old = calculate_dormancy_score(old_node, now, domain_counts)
    assert score_old >= 0.8
    assert days_old == 50
    assert "Unlinked island" in reason_old


def test_resurf_02_observation_sweep_clusters_unlinked_observations(tmp_path: Path):
    """RESURF-02: Observation sweep clusters observations sharing domain or theme."""
    _, engine = _setup_resurfacer_fixture(tmp_path)
    clusters = engine.cluster_observations()

    assert len(clusters) >= 1
    bio_cluster = next((c for c in clusters if "Biology" in c.theme), None)
    assert bio_cluster is not None
    assert "OBS-A01" in bio_cluster.observation_ids
    assert "OBS-A02" in bio_cluster.observation_ids


def test_resurf_03_and_05_find_dormant_nodes_ranks_islands_with_metadata(tmp_path: Path):
    """RESURF-03 & RESURF-05: find_dormant_nodes ranks dormant islands and provides rationale."""
    _, engine = _setup_resurfacer_fixture(tmp_path)
    dormant = engine.find_dormant_nodes(count=2)

    assert len(dormant) == 2
    top = dormant[0]
    # Forgotten Laser Rangefinder should rank top due to 40d age and 0 edges
    assert top.node.id == "AST-A01"
    assert top.days_since_touched == 40
    assert top.edge_count == 0
    assert top.dormancy_score > 0.5
    assert len(top.reason) > 0


def test_resurf_04_observation_sweep_template_schema():
    """RESURF-04: observation-sweep.v1.yaml activity template exists and adheres to schema."""
    tpl_path = Path(__file__).resolve().parent.parent.parent / "content" / "templates" / "observation-sweep.v1.yaml"
    assert tpl_path.is_file()

    with open(tpl_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "observation-sweep@1"
    assert data["category"] == "synthesis"
    assert "clusters" in data["deliverable_schema"]["required_sections"]
    assert "recommended_links" in data["deliverable_schema"]["required_sections"]


def test_resurf_06_resurfacer_logs_events_with_author(tmp_path: Path):
    """RESURF-06: log_sweep appends resurface_sweep_executed event with author."""
    store, engine = _setup_resurfacer_fixture(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    dormant = engine.find_dormant_nodes(count=2)
    engine.log_sweep(dormant, author=author)

    events = store.event_log.read_events()
    sweep_evts = [e for e in events if e.kind == "resurface_sweep_executed"]
    assert len(sweep_evts) == 1
    assert sweep_evts[0].payload["count"] == 2
    assert "AST-A01" in sweep_evts[0].payload["node_ids"]
