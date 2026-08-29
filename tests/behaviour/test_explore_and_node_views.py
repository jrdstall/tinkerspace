"""Behaviour tests for Explore and Node views, multi-facet filtering, and full-text search.

Traces DA-06 §03, §04 and STORE-09.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Edge, Node, QueryFilters
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


def test_full_text_search_finds_nodes_by_body_or_title_or_id():
    """STORE-09: Full-text search locates nodes by words in body, title, tags, or ID."""
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


def test_multi_facet_filtering():
    """QueryFilters correctly filter by domain, type, tag, and state."""
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


def test_web_explore_search_and_filter_views(tmp_path: Path):
    """Web explore landing page executes search queries and filters cleanly."""
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


def test_node_detail_view_renders_frontmatter_cml_and_edges(tmp_path: Path):
    """Node detail page renders CML scores and resolves inbound edge graph links."""
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
