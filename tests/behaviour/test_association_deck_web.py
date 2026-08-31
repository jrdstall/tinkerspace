"""Behaviour tests for Association Review Deck and rapid triage UI.

Proves ASSOCREV-01 through ASSOCREV-06 from docs/design/specs/ASSOCREV.md:
- ASSOCREV-01: Sequential card presentation in review deck
- ASSOCREV-02: Keep action (K) promotes proposal to Idea node with derived_from lineage
- ASSOCREV-03: Discard action (D) archives candidate and updates telemetry
- ASSOCREV-04: Review card displays abstract mechanism, transfer, and judge objection
- ASSOCREV-05: Empty deck displays clear state and generate action
- ASSOCREV-06: Yield metrics per sampler strategy displayed in telemetry bar
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.association.models import AssociationProposal
from iw.domain.association.review import append_proposal
from iw.web.app import create_app


def _setup_review_fixture(tmp_path: Path) -> tuple[MarkdownStore, AssociationProposal]:
    """Setup test vault, store, parent nodes, and pending proposal."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    f1 = Node(
        id="FRI-A01", type="friction", title="Bike computer battery freezes",
        created=datetime.now(timezone.utc), domain="hardware", tags=["cycling"],
    )
    a1 = Node(
        id="AST-A01", type="asset", title="Ultrasonic transducer rig",
        created=datetime.now(timezone.utc), domain="acoustics", tags=["audio"],
    )
    o1 = Node(
        id="OBS-A01", type="observation", title="Honeybee thoracic heat",
        created=datetime.now(timezone.utc), domain="biology", tags=["nature"],
    )
    store.write_node(f1, author=author)
    store.write_node(a1, author=author)
    store.write_node(o1, author=author)

    proposal = AssociationProposal(
        id="PROP-A01",
        pair_id="PAIR-01",
        node_a_id="FRI-A01",
        node_b_id="AST-A01",
        node_a_title=f1.title,
        node_b_title=a1.title,
        sampler_strategy="anti_similar",
        distance_metric=0.85,
        proposal_title="Acoustic Boundary Layer De-Icer",
        target_domain="aerospace",
        abstract_mechanism="Surface acoustic waves prevent ice nucleation.",
        transfer_proposal="Mount ultrasonic piezoelectric strips to leading edges.",
        strongest_objection="Power consumption may exceed thermal foil in heavy icing.",
        judge_verdict="keep",
        confidence=0.85,
        created_at=datetime.now(timezone.utc),
        reviewed=False,
    )
    append_proposal(vault_dir, proposal)
    return store, proposal


def test_assocrev_01_and_04_deck_renders_pending_proposal_and_objection(tmp_path: Path):
    """ASSOCREV-01 & ASSOCREV-04: Deck renders proposal card with abstraction, transfer, and objection."""
    store, _ = _setup_review_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/associations")
    assert response.status_code == 200
    assert "Acoustic Boundary Layer De-Icer" in response.text
    assert "Surface acoustic waves prevent ice nucleation." in response.text
    assert "Mount ultrasonic piezoelectric strips to leading edges." in response.text
    assert "Power consumption may exceed thermal foil in heavy icing." in response.text
    assert "VERDICT: KEEP" in response.text


def test_assocrev_02_keep_action_promotes_to_idea_with_lineage(tmp_path: Path):
    """ASSOCREV-02: Keep action (K) creates Idea node with derived_from lineage and logs event."""
    store, _ = _setup_review_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    res = client.post("/associations/keep", data={"proposal_id": "PROP-A01"}, follow_redirects=True)
    assert res.status_code == 200

    # Verify idea created in store
    ideas = [n for n in store.list_nodes() if n.type == "idea"]
    assert len(ideas) == 1
    new_idea = ideas[0]
    assert new_idea.title == "Acoustic Boundary Layer De-Icer"
    assert new_idea.attrs["derived_from"] == ["FRI-A01", "AST-A01"]

    derived_edges = [e for e in new_idea.edges if e.relation == "derived_from"]
    assert len(derived_edges) == 2

    # Verify event logged
    events = store.event_log.read_events()
    reviewed_evts = [e for e in events if e.kind == "association_reviewed"]
    assert len(reviewed_evts) == 1
    assert reviewed_evts[0].payload["decision"] == "keep"


def test_assocrev_03_discard_action_archives_candidate(tmp_path: Path):
    """ASSOCREV-03: Discard action (D) marks proposal discarded without creating idea."""
    store, _ = _setup_review_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    res = client.post("/associations/discard", data={"proposal_id": "PROP-A01"}, follow_redirects=True)
    assert res.status_code == 200

    # No idea should be created
    ideas = [n for n in store.list_nodes() if n.type == "idea"]
    assert len(ideas) == 0

    # Empty state should now show
    assert "Review Deck Cleared!" in res.text

    # Verify event logged
    events = store.event_log.read_events()
    reviewed_evts = [e for e in events if e.kind == "association_reviewed"]
    assert len(reviewed_evts) == 1
    assert reviewed_evts[0].payload["decision"] == "discard"


def test_assocrev_05_empty_state_and_generate_action(tmp_path: Path):
    """ASSOCREV-05: Empty deck displays clear state and generate action creates new deck."""
    store, _ = _setup_review_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # Discard existing card
    client.post("/associations/discard", data={"proposal_id": "PROP-A01"})

    # Check empty state
    empty_resp = client.get("/associations")
    assert "Review Deck Cleared!" in empty_resp.text

    # Generate new batch
    gen_resp = client.post(
        "/associations/generate",
        data={"strategy": "anti_similar", "count": 2},
        follow_redirects=True,
    )
    assert gen_resp.status_code == 200
    assert "Review Deck Cleared!" not in gen_resp.text
    assert "1 of 2" in gen_resp.text
    assert "PROP-A02" in gen_resp.text


def test_assocrev_06_sampler_telemetry_yield_displayed(tmp_path: Path):
    """ASSOCREV-06: Yield metrics per sampler strategy displayed in telemetry bar."""
    store, _ = _setup_review_fixture(tmp_path)
    # Log some mock reviews
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    store.event_log.append(
        kind="association_reviewed", subject_id="PROP-01", author=author,
        payload={"strategy": "anti_similar", "decision": "keep"},
    )
    store.event_log.append(
        kind="association_reviewed", subject_id="PROP-02", author=author,
        payload={"strategy": "anti_similar", "decision": "discard"},
    )

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get("/associations")
    assert response.status_code == 200
    assert "Anti-Similar:" in response.text
    assert "50.0%" in response.text
