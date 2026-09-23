"""Behaviour tests for Questionstorming question and relationship edits.

Proves QSTORM-09 and QSTORM-10 from docs/design/specs/QSTORM.md:
- QSTORM-09: Updating question node title, form (open <-> closed), and importance.
- QSTORM-10: Updating and deleting question relationship edges.
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.questionstorm.service import QuestionstormService


def _setup_fixture(tmp_path: Path) -> tuple[MarkdownStore, QuestionstormService, str]:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    service = QuestionstormService(store=store)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    friction = Node(
        id="FRI-A01",
        type="friction",
        title="Bike display battery dies in cold weather",
        created=datetime.now(timezone.utc),
        domain="hardware",
        tags=["cycling", "battery"],
    )
    store.write_node(friction, author=author)
    return store, service, friction.id


def test_qstorm_09_update_question_text_form_and_importance(tmp_path: Path):
    """QSTORM-09: Updating question node mutates title, form, and importance while preserving identity."""
    store, service, subject_id = _setup_fixture(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    q = service.create_question(
        subject_id=subject_id,
        text="Why does cold deplete voltage?",
        form="open",
        importance="medium",
        author=author,
    )
    assert q.id == "QUE-A01"
    assert q.title == "Why does cold deplete voltage?"
    assert q.attrs["form"] == "open"
    assert q.attrs["importance"] == "medium"

    # Mutate text, form, and importance
    updated = service.update_question(
        question_id=q.id,
        text="Does battery chemistry freeze at -10C?",
        form="closed",
        importance="high",
        author=author,
    )
    assert updated is not None
    assert updated.id == "QUE-A01"
    assert updated.title == "Does battery chemistry freeze at -10C?"
    assert updated.attrs["form"] == "closed"
    assert updated.attrs["importance"] == "high"

    # Verify persistence to disk
    loaded = store.get_node("QUE-A01")
    assert loaded is not None
    assert loaded.title == "Does battery chemistry freeze at -10C?"
    assert loaded.attrs["form"] == "closed"
    assert loaded.attrs["importance"] == "high"


def test_qstorm_10_update_and_delete_question_relations(tmp_path: Path):
    """QSTORM-10: Relationship updates modify or delete directional edges without altering subject link."""
    store, service, subject_id = _setup_fixture(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    q1 = service.create_question(subject_id=subject_id, text="Q1 Open", form="open", author=author)
    q2 = service.create_question(
        subject_id=subject_id, text="Q2 Closed", form="closed",
        parent_question_id=q1.id, relation="narrows", author=author,
    )

    # 1. Verify initial relation
    edges_q2_to_q1 = [e for e in q2.edges if e.to_id == q1.id]
    assert len(edges_q2_to_q1) == 1
    assert edges_q2_to_q1[0].relation == "narrows"

    # 2. Update relation from narrows to broadens
    updated_edge = service.update_relation(from_id=q2.id, to_id=q1.id, new_relation="broadens", author=author)
    assert updated_edge is not None
    assert updated_edge.relation == "broadens"

    loaded_q2 = store.get_node(q2.id)
    assert loaded_q2 is not None
    rel = [e.relation for e in loaded_q2.edges if e.to_id == q1.id]
    assert rel == ["broadens"]

    # 3. link_questions upsert updates existing edge rather than duplicating
    service.link_questions(from_id=q2.id, to_id=q1.id, relation="sibling", author=author)
    loaded_q2_after = store.get_node(q2.id)
    assert loaded_q2_after is not None
    q1_edges = [e for e in loaded_q2_after.edges if e.to_id == q1.id]
    assert len(q1_edges) == 1
    assert q1_edges[0].relation == "sibling"

    # 4. Unlink questions removes edge between q2 and q1 but keeps questions edge to subject
    removed = service.unlink_questions(from_id=q2.id, to_id=q1.id, author=author)
    assert removed is True

    loaded_unlinked = store.get_node(q2.id)
    assert loaded_unlinked is not None
    assert len([e for e in loaded_unlinked.edges if e.to_id == q1.id]) == 0
    # questions edge to subject must still exist
    assert any(e.to_id == subject_id and e.relation == "questions" for e in loaded_unlinked.edges)


def test_qstorm_05_additional_question_relations(tmp_path: Path):
    """QSTORM-05: Supports decomposes, explores, challenges, tests, and depends_on relations."""
    store, service, subject_id = _setup_fixture(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    main_q = service.create_question(subject_id=subject_id, text="How to solve cold battery drain?", author=author)

    # 1. decomposes
    q_decomp = service.create_question(
        subject_id=subject_id, text="What cell chemistry is best below 0C?",
        parent_question_id=main_q.id, relation="decomposes", author=author,
    )
    assert any(e.to_id == main_q.id and e.relation == "decomposes" for e in q_decomp.edges)

    # 2. explores
    q_explore = service.create_question(
        subject_id=subject_id, text="Could we harvest rider body heat?",
        parent_question_id=main_q.id, relation="explores", author=author,
    )
    assert any(e.to_id == main_q.id and e.relation == "explores" for e in q_explore.edges)

    # 3. challenges
    q_chall = service.create_question(
        subject_id=subject_id, text="Do winter riders actually look at the display?",
        parent_question_id=main_q.id, relation="challenges", author=author,
    )
    assert any(e.to_id == main_q.id and e.relation == "challenges" for e in q_chall.edges)

    # 4. tests
    q_test = service.create_question(
        subject_id=subject_id, text="Does an aerogel wrap preserve >3.2V for 3 hours at -10C?",
        form="closed", parent_question_id=main_q.id, relation="tests", author=author,
    )
    assert any(e.to_id == main_q.id and e.relation == "tests" for e in q_test.edges)

    # 5. depends_on
    q_dep = service.create_question(
        subject_id=subject_id, text="Which PCB heater circuit should we layout?",
        parent_question_id=main_q.id, relation="depends_on", author=author,
    )
    assert any(e.to_id == main_q.id and e.relation == "depends_on" for e in q_dep.edges)
