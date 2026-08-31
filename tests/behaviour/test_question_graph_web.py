"""Behaviour tests for Question Graph visual DAG surface and fast questioning actions.

Proves QGRAPH-01 through QGRAPH-06 from docs/design/specs/QGRAPH.md:
- QGRAPH-01: Question Graph renders visual DAG of questions attached to subject
- QGRAPH-02: Questions partitioned into Open and Closed columns
- QGRAPH-03: Importance styling rendered
- QGRAPH-04: Directed relationship indicators (broadens, narrows, etc.)
- QGRAPH-05: Web form actions to create, transform, and link questions
- QGRAPH-06: Orphan vs. connected question chains visible
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.questionstorm.service import QuestionstormService
from iw.web.app import create_app


def _setup_graph_fixture(tmp_path: Path) -> tuple[MarkdownStore, QuestionstormService, str]:
    """Populate store with subject friction and connected question DAG."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    service = QuestionstormService(store=store)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    friction = Node(
        id="FRI-A01",
        type="friction",
        title="Bike display battery freezes in winter",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling"],
    )
    store.write_node(friction, author=author)

    # Question 1: Open, High importance
    q1 = service.create_question(
        subject_id="FRI-A01",
        text="Why does cold temperature deplete battery voltage?",
        form="open",
        importance="high",
        move="why",
        author=author,
    )

    # Question 2: Closed, Medium importance (narrows Q1)
    q2 = service.create_question(
        subject_id="FRI-A01",
        text="Can internal self-heating circuitry prevent freeze cutoff?",
        form="closed",
        importance="medium",
        parent_question_id=q1.id,
        relation="narrows",
        author=author,
    )

    return store, service, friction.id


def test_qgraph_01_question_graph_renders_attached_questions(tmp_path: Path):
    """QGRAPH-01: Question Graph renders visual DAG of questions attached to subject."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "QUESTION GRAPH" in response.text
    assert "FRI-A01" in response.text
    assert "Bike display battery freezes in winter" in response.text
    assert "Why does cold temperature deplete battery voltage?" in response.text
    assert "Can internal self-heating circuitry prevent freeze cutoff?" in response.text


def test_qgraph_02_groups_open_and_closed_questions(tmp_path: Path):
    """QGRAPH-02: Questions are visually grouped into Open and Closed columns."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "Open Questions (Exploration Space)" in response.text
    assert "Closed Questions (Decidable Choices)" in response.text


def test_qgraph_03_importance_styling_rendered(tmp_path: Path):
    """QGRAPH-03: High importance questions reflect prominent visual styling."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "HIGH" in response.text
    assert "MED" in response.text


def test_qgraph_04_directed_relationship_edges_rendered(tmp_path: Path):
    """QGRAPH-04: Directed edge relations (e.g. narrows) render on connected cards."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "[narrows]" in response.text
    assert "QUE-A01" in response.text


def test_qgraph_05_quick_action_creates_transforms_and_links(tmp_path: Path):
    """QGRAPH-05: Web action forms support create, transform, and link actions."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # 1. Create Question
    create_resp = client.post(
        "/question-graph/create",
        data={
            "subject_id": subject_id,
            "text": "What if we harvest power from pedal rotation?",
            "form": "open",
            "importance": "high",
            "move": "constraint_removal",
        },
        follow_redirects=True,
    )
    assert create_resp.status_code == 200
    assert "What if we harvest power from pedal rotation?" in create_resp.text

    # 2. Transform Question
    transform_resp = client.post(
        "/question-graph/transform",
        data={
            "subject_id": subject_id,
            "question_id": "QUE-A01",
            "new_text": "Is battery voltage drop irreversible after 1 hour at -10C?",
        },
        follow_redirects=True,
    )
    assert transform_resp.status_code == 200
    assert "Is battery voltage drop irreversible after 1 hour at -10C?" in transform_resp.text

    # 3. Link Questions
    link_resp = client.post(
        "/question-graph/link",
        data={
            "subject_id": subject_id,
            "from_id": "QUE-A01",
            "to_id": "QUE-A02",
            "relation": "broadens",
        },
        follow_redirects=True,
    )
    assert link_resp.status_code == 200
    assert "[broadens]" in link_resp.text


def test_qgraph_06_orphan_and_connected_questions_visible(tmp_path: Path):
    """QGRAPH-06: Orphan questions and connected question chains render on graph."""
    store, service, subject_id = _setup_graph_fixture(tmp_path)
    # Add standalone orphan question
    service.create_question(
        subject_id=subject_id,
        text="Standalone orphan question with no peer links",
        form="open",
    )

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "Standalone orphan question with no peer links" in response.text
