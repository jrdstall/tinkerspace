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

    # 4. Filter by type alias ?type=fri returns FRI-A01
    res_fri = client.get("/?type=fri")
    assert res_fri.status_code == 200
    assert "FRI-A01" in res_fri.text
    assert "AST-A01" not in res_fri.text

    # 5. Domain dropdown presence and filtering
    assert 'id="domain-select"' in res_all.text
    assert 'name="domain"' in res_all.text
    assert '<option value="" selected>All Domains</option>' in res_all.text
    assert '<option value="cycling" >cycling</option>' in res_all.text or '<option value="cycling">cycling</option>' in res_all.text
    assert '<option value="hardware" >hardware</option>' in res_all.text or '<option value="hardware">hardware</option>' in res_all.text

    # Filter by domain=hardware
    res_domain_hw = client.get("/?domain=hardware")
    assert res_domain_hw.status_code == 200
    assert "AST-A01" in res_domain_hw.text
    assert "IDEA-A01" not in res_domain_hw.text
    assert "FRI-A01" not in res_domain_hw.text
    assert '<option value="hardware" selected>hardware</option>' in res_domain_hw.text
    assert 'href="/" class="btn"' in res_domain_hw.text  # Clear button rendered

    # Filter by domain=cycling
    res_domain_cy = client.get("/?domain=cycling")
    assert res_domain_cy.status_code == 200
    assert "IDEA-A01" in res_domain_cy.text
    assert "FRI-A01" in res_domain_cy.text
    assert "AST-A01" not in res_domain_cy.text
    assert '<option value="cycling" selected>cycling</option>' in res_domain_cy.text

    assert "node-tile" in res_all.text
    assert "setTypeFilter" in res_all.text
    assert "setStateFilter" in res_all.text


def test_explore_04_node_detail_view_renders_frontmatter_cml_and_edges(tmp_path: Path):
    """EXPLORE-04: Node detail page renders CML scores and resolves inbound edge graph links."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Idea detail view renders CML scores breakdown and flush body text
    res_idea = client.get("/node/IDEA-A01")
    assert res_idea.status_code == 200
    assert "CML Level:" in res_idea.text
    assert "Novel: <strong>2</strong>" in res_idea.text
    assert "Worth (me): <strong>high</strong>" in res_idea.text
    assert "&rarr; [addresses]" in res_idea.text
    assert "FRI-A01" in res_idea.text
    assert ">Reflective Sharp memory LCD consumes microwatts" in res_idea.text

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
    assert "Add Link" in res_view.text
    assert "node-target-search" in res_view.text
    add_link_sec = res_view.text[res_view.text.find("Add Link"):]
    assert add_link_sec.find('name="relation"') < add_link_sec.find('name="target_id"')

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


def test_explore_07_node_back_link_navigation(tmp_path: Path):
    """EXPLORE-07: Node detail view resolves intelligent back links from referring nodes/pages."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    for n in _sample_nodes():
        store.write_node(n, author=author)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Direct view from explore (no from param, no referer) -> Back to Explore
    res_direct = client.get("/node/IDEA-A01")
    assert res_direct.status_code == 200
    assert 'href="/"' in res_direct.text
    assert "Back to Explore" in res_direct.text
    assert 'href="/node/FRI-A01?from=IDEA-A01"' in res_direct.text

    # 2. View node arriving from another node via ?from= query param
    res_from_node = client.get("/node/FRI-A01?from=IDEA-A01")
    assert res_from_node.status_code == 200
    assert 'href="/node/IDEA-A01"' in res_from_node.text
    assert "Back to Idea (IDEA-A01: Memory-in-pixel handlebar puck...)" in res_from_node.text

    # 3. View node arriving via Referer header
    res_referer = client.get("/node/FRI-A01", headers={"referer": "http://testserver/node/IDEA-A01"})
    assert res_referer.status_code == 200
    assert 'href="/node/IDEA-A01"' in res_referer.text
    assert "Back to Idea (IDEA-A01: Memory-in-pixel handlebar puck...)" in res_referer.text

    # 4. View node arriving from Work Board
    res_board = client.get("/node/IDEA-A01?from=board")
    assert res_board.status_code == 200
    assert 'href="/board"' in res_board.text
    assert "Back to Work Board" in res_board.text

    # 5. Form actions preserve ?from= parameter upon redirect
    res_link = client.post(
        "/node/FRI-A01/link?from=IDEA-A01",
        data={"target_id": "AST-A01", "relation": "relates_to", "note": "test"},
        follow_redirects=False,
    )
    assert res_link.status_code == 303
    assert res_link.headers["location"] == "/node/FRI-A01?from=IDEA-A01"


def test_explore_08_node_detail_editing_and_personal_ux(tmp_path: Path):
    """EXPLORE-08: Node detail view supports in-place editing of core attributes and personal UX labels."""
    store = MarkdownStore(vault_dir=tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    t0 = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
    for n in _sample_nodes():
        if n.id == "IDEA-A01":
            n.last_touched = t1
        store.write_node(n, author=author)
    store.write_node(
        Node(
            id="IDEA-A00",
            type="idea",
            title="Earlier Idea Solar Cells",
            created=t0,
            last_touched=t0,
            domain="energy",
            tags=["energy"],
            state="active",
            author=author,
        ),
        author=author,
    )
    store.write_node(
        Node(
            id="IDEA-A02",
            type="idea",
            title="Later Idea Head-Up Display",
            created=t2,
            last_touched=t2,
            domain="cycling",
            tags=["cycling"],
            state="active",
            author=author,
        ),
        author=author,
    )

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Verify personal labels, single-line datalist, and adjacent idea buttons on GET
    res_view = client.get("/node/IDEA-A01")
    assert res_view.status_code == 200
    assert "Jared" in res_view.text
    assert "human (web-ui)" not in res_view.text
    assert "My Idea" in res_view.text
    assert "Note Prose (Markdown Body)" not in res_view.text
    assert "Links" in res_view.text
    assert "Typed Relationships &amp; Graph Edges" not in res_view.text
    assert "Add Link" in res_view.text
    assert "+ Link to Another Node" not in res_view.text
    assert "node-target-search" in res_view.text
    # Adjacent idea buttons by title
    assert "&larr; Prev: Later Idea Head-Up Display" in res_view.text
    assert "Next: Earlier Idea Solar Cells &rarr;" in res_view.text
    assert 'href="/node/IDEA-A02"' in res_view.text
    assert 'href="/node/IDEA-A00"' in res_view.text

    # 2. Edit the idea node via POST /node/{node_id}/edit with leading '#' on tags and keywords
    res_edit = client.post(
        "/node/IDEA-A01/edit",
        data={
            "title": "Sunlight-readable BLE number puck v2",
            "domain": "hardware",
            "tags": "#cycling, #display, ble",
            "keywords": "#transflective, ultralow-power, #eink",
            "state": "parked",
            "worth_to_me": "high",
            "worth_to_others": "medium",
            "body": "Updated prose: Transflective display optimized for 100hr battery life.",
        },
        follow_redirects=True,
    )
    assert res_edit.status_code == 200
    assert "Sunlight-readable BLE number puck v2" in res_edit.text
    assert "Domain: <strong style=\"color: var(--text-main);\">hardware</strong>" in res_edit.text
    assert "🔑 transflective" in res_edit.text
    assert "🔑 ultralow-power" in res_edit.text
    assert "🔑 #transflective" not in res_edit.text
    assert "#cycling" in res_edit.text
    assert "##cycling" not in res_edit.text
    assert "Updated prose: Transflective display optimized for 100hr battery life." in res_edit.text

    # 3. Verify disk persistence without caching
    updated_node = store.get_node("IDEA-A01")
    assert updated_node is not None
    assert updated_node.title == "Sunlight-readable BLE number puck v2"
    assert updated_node.domain == "hardware"
    assert updated_node.state == "parked"
    assert updated_node.tags == ["cycling", "display", "ble"]
    assert updated_node.attrs.get("keywords") == ["transflective", "ultralow-power", "eink"]
    assert updated_node.attrs.get("worth_to_me") == "high"
    assert updated_node.attrs.get("worth_to_others") == "medium"
    assert "Transflective display optimized for 100hr battery life." in updated_node.body

    # 4. Verify search matches newly added keyword
    res_search = client.get("/?q=transflective")
    assert res_search.status_code == 200
    assert "IDEA-A01" in res_search.text

    # 5. Unlinking last edge removes edges key from frontmatter
    res_unlink = client.post(
        "/node/IDEA-A01/unlink",
        data={"target_id": "FRI-A01", "relation": "addresses"},
        follow_redirects=True,
    )
    assert res_unlink.status_code == 200
    node_no_edges = store.get_node("IDEA-A01")
    assert node_no_edges is not None
    assert len(node_no_edges.edges) == 0



