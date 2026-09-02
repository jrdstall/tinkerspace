"""Behaviour tests for Explore and Node views, multi-facet filtering, and full-text search.

Traces EXPLORE-01 through EXPLORE-04 per docs/design/specs/EXPLORE.md.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node, QueryFilters
from iw.core.events import FileEventLog
from iw.core.index import InMemoryIndex
from iw.core.store import MarkdownStore
from iw.web.app import create_app


def _sample_nodes() -> list[Node]:
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    return [
        Node(
            id="FRI-A01",
            type="friction",
            title="Bike computer screens washed out in sunlight",
            created=now,
            domain="cycling",
            tags=["hardware", "display"],
            state="active",
            author=author,
            body="Existing LCD head units are completely illegible under midday sun without backlight draining battery.",
        ),
        Node(
            id="IDEA-A01",
            type="idea",
            title="Memory-in-pixel handlebar puck display",
            created=now,
            domain="cycling",
            tags=["hardware", "low-power", "display"],
            state="active",
            author=author,
            edges=[Edge(from_id="IDEA-A01", to_id="FRI-A01", relation="addresses", created=now, author=author)],
            body="Reflective Sharp memory LCD consumes microwatts and has infinite contrast in sunlight.",
            attrs={"cml": 2, "scores": {"novel": 2, "works": 3, "reach": 2, "story": 3}, "worth_to_me": "high"},
        ),
        Node(
            id="AST-A01",
            type="asset",
            title="Rigol 4-channel Digital Oscilloscope",
            created=now,
            domain="hardware",
            tags=["lab", "measurement"],
            state="have",
            author=author,
            body="100MHz digital storage oscilloscope on workbench.",
        ),
    ]


def test_explore_01_full_text_search_finds_nodes_by_body_or_title_or_id():
    """EXPLORE-01: Full-text search locates nodes by words in body, title, tags, or ID."""
    nodes = _sample_nodes()
    index = InMemoryIndex(nodes)

    # 1. Search by word in body
    results_body = index.search("microwatts")
    assert len(results_body) == 1
    assert results_body[0].id == "IDEA-A01"

    # 2. Search by ID
    results_id = index.search("FRI-A01")
    assert len(results_id) == 1
    assert results_id[0].id == "FRI-A01"

    # 3. Search by tag
    results_tag = index.search("measurement")
    assert len(results_tag) == 1
    assert results_tag[0].id == "AST-A01"


def test_explore_02_multi_facet_filtering():
    """EXPLORE-02: QueryFilters correctly filter by domain, type, tag, and state."""
    nodes = _sample_nodes()
    index = InMemoryIndex(nodes)

    # Filter by domain
    res_domain = index.query(QueryFilters(domain="cycling"))
    assert len(res_domain) == 2
    assert set(r.id for r in res_domain) == {"FRI-A01", "IDEA-A01"}

    # Filter by type
    res_type = index.query(QueryFilters(type="asset"))
    assert len(res_type) == 1
    assert res_type[0].id == "AST-A01"

    # Filter by state
    res_state = index.query(QueryFilters(state="have"))
    assert len(res_state) == 1
    assert res_state[0].id == "AST-A01"

    # Filter by min_cml
    res_cml = index.query(QueryFilters(min_cml=2))
    assert len(res_cml) == 1
    assert res_cml[0].id == "IDEA-A01"


def test_explore_03_web_explore_search_and_filter_views(tmp_path: Path):
    """EXPLORE-03: Web explore landing page executes search queries and filters cleanly."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Base view lists all 3 nodes
    res_all = client.get("/")
    assert res_all.status_code == 200
    assert "Showing <strong>3</strong> of <strong>3</strong>" in res_all.text
    assert "FRI-A01" in res_all.text
    assert "IDEA-A01" in res_all.text
    assert "AST-A01" in res_all.text

    # 2. Search query for "microwatts" returns only IDEA-A01
    res_q = client.get("/?q=microwatts")
    assert res_q.status_code == 200
    assert "IDEA-A01" in res_q.text
    assert "FRI-A01" not in res_q.text
    assert "Showing <strong>1</strong> of <strong>3</strong>" in res_q.text

    # 3. Filter by type=asset returns AST-A01
    res_type = client.get("/?type=asset")
    assert res_type.status_code == 200
    assert "AST-A01" in res_type.text
    assert "IDEA-A01" not in res_type.text


def test_explore_04_node_detail_view_renders_frontmatter_cml_and_edges(tmp_path: Path):
    """EXPLORE-04: Node detail page renders CML scores and resolves inbound edge graph links."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Idea detail view renders CML scores breakdown
    res_idea = client.get("/node/IDEA-A01")
    assert res_idea.status_code == 200
    assert "CML Level:" in res_idea.text
    assert "Novel: <strong>2</strong>" in res_idea.text
    assert "Worth (me): <strong>high</strong>" in res_idea.text
    assert "&rarr; [addresses]" in res_idea.text
    assert "FRI-A01" in res_idea.text

    # 2. Friction detail view resolves inbound edge from IDEA-A01
    res_fri = client.get("/node/FRI-A01")
    assert res_fri.status_code == 200
    assert "&larr; [addresses]" in res_fri.text
    assert "IDEA-A01" in res_fri.text


def test_explore_05_node_link_and_unlink_post_triage(tmp_path: Path):
    """EXPLORE-05: Node detail view supports post-triage relationship creation and removal."""
    event_log = FileEventLog(tmp_path / "events.jsonl")
    store = MarkdownStore(vault_dir=tmp_path, event_log=event_log)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Verify available targets in GET view
    res_view = client.get("/node/IDEA-A01")
    assert res_view.status_code == 200
    assert "+ Link to Another Node" in res_view.text
    assert "available-targets-list" in res_view.text
    assert "AST-A01" in res_view.text

    # 2. Add relationship link from IDEA-A01 -> AST-A01
    res_link = client.post(
        "/node/IDEA-A01/link",
        data={
            "target_id": "AST-A01 — Rigol 4-channel Digital Oscilloscope (asset)",
            "relation": "requires",
            "note": "Required for power consumption benchmarking",
        },
        follow_redirects=True,
    )
    assert res_link.status_code == 200
    assert "&rarr; [requires]" in res_link.text
    assert "AST-A01" in res_link.text

    # Verify persisted in store
    node_idea = store.get_node("IDEA-A01")
    assert node_idea is not None
    assert any(e.to_id == "AST-A01" and e.relation == "requires" for e in node_idea.edges)

    # Verify event logged
    events = event_log.read_events()
    created_events = [e for e in events if e.kind == "edge_created"]
    assert len(created_events) == 1
    assert created_events[0].subject_id == "IDEA-A01"
    assert created_events[0].payload.get("to_id") == "AST-A01"

    # 3. Unlink relationship
    res_unlink = client.post(
        "/node/IDEA-A01/unlink",
        data={
            "target_id": "AST-A01",
            "relation": "requires",
        },
        follow_redirects=True,
    )
    assert res_unlink.status_code == 200

    # Verify removed from store
    node_idea_after = store.get_node("IDEA-A01")
    assert node_idea_after is not None
    assert not any(e.to_id == "AST-A01" for e in node_idea_after.edges)

    # Verify unlink event logged
    events_after = event_log.read_events()
    removed_events = [e for e in events_after if e.kind == "edge_removed"]
    assert len(removed_events) == 1
    assert removed_events[0].subject_id == "IDEA-A01"
    assert removed_events[0].payload.get("to_id") == "AST-A01"


def test_explore_06_subquestions_excluded_from_explore_and_search(tmp_path: Path):
    """EXPLORE-06: Questionstorm sub-questions are excluded from explore catalog and search."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    # Add 1 top-level macro question (should appear in Explore)
    top_question = Node(
        id="QUE-A01",
        type="question",
        title="Why do bike computers drain batteries so rapidly in winter?",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["power"],
        state="held_open",
        author=author,
        body="Macro question driving cold-weather display inquiries.",
    )
    store.write_node(top_question, author=author)

    # Add 2 questionstorm sub-questions (should NOT appear in Explore)
    sub_q1 = Node(
        id="QUE-A02",
        type="question",
        title="What if we eliminate LCD backlights entirely?",
        created=datetime.now(timezone.utc),
        domain="cycling",
        tags=["questionstorm"],
        state="held_open",
        author=author,
        body="",
        attrs={"subject_id": "IDEA-A01", "is_subquestion": True, "form": "open", "move": "what_if"},
    )
    store.write_node(sub_q1, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Base explore page shows 4 corpus nodes (FRI-A01, IDEA-A01, AST-A01, and top QUE-A01)
    # but does NOT show QUE-A02
    res = client.get("/")
    assert res.status_code == 200
    assert "Showing <strong>4</strong> of <strong>4</strong>" in res.text
    assert "QUE-A01" in res.text
    assert "QUE-A02" not in res.text

    # 2. Searching for "backlights" (which is in sub-question QUE-A02) returns 0 corpus results
    res_search = client.get("/?q=backlights")
    assert res_search.status_code == 200
    assert "QUE-A02" not in res_search.text
    assert "Showing <strong>0</strong> of <strong>4</strong>" in res_search.text


