"""Behaviour tests for Question Graph web editing of questions and relations.

Proves QGRAPH-10 and QGRAPH-11 from docs/design/specs/QGRAPH.md:
- QGRAPH-10: Inline editing of question text, form (open <-> closed), and importance.
- QGRAPH-11: Inline editing and deletion of question-to-question relations.
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

    q1 = service.create_question(
        subject_id="FRI-A01",
        text="Why does cold temperature deplete battery voltage?",
        form="open",
        importance="high",
        author=author,
    )
    q2 = service.create_question(
        subject_id="FRI-A01",
        text="Can internal self-heating prevent cutoff?",
        form="closed",
        importance="medium",
        parent_question_id=q1.id,
        relation="narrows",
        author=author,
    )
    return store, service, friction.id


def test_qgraph_10_edit_question_text_form_and_importance(tmp_path: Path):
    """QGRAPH-10: Question editor updates text, changes form (open->closed), and modifies importance."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # Initially QUE-A01 is open and has original text
    resp_init = client.get(f"/question-graph/{subject_id}")
    assert "Why does cold temperature deplete battery voltage?" in resp_init.text

    # Edit QUE-A01 to closed form and update text
    edit_resp = client.post(
        "/question-graph/edit",
        data={
            "subject_id": subject_id,
            "question_id": "QUE-A01",
            "text": "Is battery voltage depletion chemically unavoidable below 0C?",
            "form": "closed",
            "importance": "low",
        },
        follow_redirects=True,
    )
    assert edit_resp.status_code == 200
    assert "Is battery voltage depletion chemically unavoidable below 0C?" in edit_resp.text

    # Verify node in store has been updated
    node = store.get_node("QUE-A01")
    assert node is not None
    assert node.title == "Is battery voltage depletion chemically unavoidable below 0C?"
    assert node.attrs["form"] == "closed"
    assert node.attrs["importance"] == "low"


def test_qgraph_11_update_and_delete_question_relations(tmp_path: Path):
    """QGRAPH-11: Relationship controls update relation type and remove question-to-question links."""
    store, _, subject_id = _setup_graph_fixture(tmp_path)
    app = create_app(store=store)
    client = TestClient(app)

    # Initially QUE-A02 has [narrows] pointing to QUE-A01
    resp_init = client.get(f"/question-graph/{subject_id}")
    assert "[narrows]" in resp_init.text

    # 1. Update relation to broadens
    update_resp = client.post(
        "/question-graph/relation/update",
        data={
            "subject_id": subject_id,
            "from_id": "QUE-A02",
            "to_id": "QUE-A01",
            "relation": "broadens",
        },
        follow_redirects=True,
    )
    assert update_resp.status_code == 200
    assert "[broadens]" in update_resp.text

    # 2. Delete the relation
    delete_resp = client.post(
        "/question-graph/relation/delete",
        data={
            "subject_id": subject_id,
            "from_id": "QUE-A02",
            "to_id": "QUE-A01",
        },
        follow_redirects=True,
    )
    assert delete_resp.status_code == 200
    assert "[broadens]" not in delete_resp.text

    # Verify underlying store state
    q2 = store.get_node("QUE-A02")
    assert q2 is not None
    assert len([e for e in q2.edges if e.to_id == "QUE-A01"]) == 0
    # Questions edge to subject is preserved
    assert any(e.to_id == subject_id and e.relation == "questions" for e in q2.edges)

    # 3. Reconnect question with a new relation via link endpoint
    link_resp = client.post(
        "/question-graph/link",
        data={
            "subject_id": subject_id,
            "from_id": "QUE-A02",
            "to_id": "QUE-A01",
            "relation": "decomposes",
        },
        follow_redirects=True,
    )
    assert link_resp.status_code == 200
    assert "[decomposes]" in link_resp.text
    q2_reconnected = store.get_node("QUE-A02")
    assert any(e.to_id == "QUE-A01" and e.relation == "decomposes" for e in q2_reconnected.edges)


def test_qgraph_04_additional_relations_in_web_and_diagram(tmp_path: Path):
    """QGRAPH-04: decomposes and explores relations render in cards, selectors, and Mermaid DAG."""
    store, service, subject_id = _setup_graph_fixture(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    # Create branching question with decomposes
    q3 = service.create_question(
        subject_id=subject_id,
        text="What power management circuits optimize cold current draw?",
        parent_question_id="QUE-A01",
        relation="decomposes",
        author=author,
    )
    # Link QUE-A02 to QUE-A03 with explores
    service.link_questions(from_id="QUE-A02", to_id=q3.id, relation="explores", author=author)

    app = create_app(store=store)
    client = TestClient(app)

    response = client.get(f"/question-graph/{subject_id}")
    assert response.status_code == 200
    assert "[decomposes]" in response.text
    assert "[explores]" in response.text
    assert 'value="decomposes"' in response.text
    assert 'value="explores"' in response.text
    assert 'value="challenges"' in response.text
    assert 'value="tests"' in response.text
    assert 'value="depends_on"' in response.text

    # Verify Mermaid graph renders directed edges with new relations
    assert "QUE_A01 -->|decomposes| QUE_A03" in response.text
    assert "QUE_A03 -->|explores| QUE_A02" in response.text or "QUE_A02 -->|explores| QUE_A03" in response.text
