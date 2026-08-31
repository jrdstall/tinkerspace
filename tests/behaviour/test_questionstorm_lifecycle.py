"""Behaviour tests for Questionstorming domain, Berger questioning moves, and question graph edges.

Proves QSTORM-01 through QSTORM-08 from docs/design/specs/QSTORM.md:
- QSTORM-01: Questionstorm creates typed question nodes (QUE-xxx) attached to a subject
- QSTORM-02: Form (open/closed), importance (high/med/low), and state (held_open) recorded
- QSTORM-03: held_open is a first-class valid state
- QSTORM-04: questions directional edge established from question to subject
- QSTORM-05: 5 canonical question-to-question relations (broadens, narrows, presupposes, reframes, sibling)
- QSTORM-06: Berger questioning moves generate starter prompts
- QSTORM-07: Transform between open and closed forms produces linked question node
- QSTORM-08: Events appended and author attribution stamped
"""

from datetime import datetime, timezone
from pathlib import Path

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.questionstorm.models import QuestionForm, QuestionImportance
from iw.domain.questionstorm.moves import apply_berger_move, get_berger_stems
from iw.domain.questionstorm.service import QuestionstormService


def _setup_store_and_subject(tmp_path: Path) -> tuple[MarkdownStore, QuestionstormService, str]:
    """Create test store, questionstorm service, and subject node."""
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


def test_qstorm_01_questionstorm_creates_batch_of_question_nodes(tmp_path: Path):
    """QSTORM-01: Questionstorm creates typed question nodes (QUE-xxx) linked to subject."""
    _, service, subject_id = _setup_store_and_subject(tmp_path)
    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")

    q1 = service.create_question(
        subject_id=subject_id,
        text="Why does cold weather degrade battery voltage so rapidly?",
        form="open",
        importance="high",
        move="why",
        author=author,
    )
    q2 = service.create_question(
        subject_id=subject_id,
        text="What if we used supercapacitors instead of lithium cells?",
        form="open",
        importance="medium",
        move="constraint_removal",
        author=author,
    )

    assert q1.id == "QUE-A01"
    assert q1.type == "question"
    assert q2.id == "QUE-A02"
    assert q2.type == "question"


def test_qstorm_02_and_03_form_importance_and_held_open_state(tmp_path: Path):
    """QSTORM-02 & QSTORM-03: Records form, importance, and first-class held_open state."""
    store, service, subject_id = _setup_store_and_subject(tmp_path)
    q = service.create_question(
        subject_id=subject_id,
        text="Can we harvest energy from the wheel hub dynamo?",
        form=QuestionForm.CLOSED.value,
        importance=QuestionImportance.HIGH.value,
    )

    assert q.state == "held_open"
    assert q.attrs["form"] == "closed"
    assert q.attrs["importance"] == "high"

    # Reload from disk and verify frontmatter state
    loaded = store.get_node(q.id)
    assert loaded is not None
    assert loaded.state == "held_open"
    assert loaded.attrs["form"] == "closed"
    assert loaded.attrs["importance"] == "high"


def test_qstorm_04_questions_edge_to_subject(tmp_path: Path):
    """QSTORM-04: Question establishes a 'questions' directional edge pointing to subject."""
    store, service, subject_id = _setup_store_and_subject(tmp_path)
    q = service.create_question(
        subject_id=subject_id,
        text="Why do we display real-time speed instead of cadence?",
    )

    loaded = store.get_node(q.id)
    assert loaded is not None
    edge_to_subject = [e for e in loaded.edges if e.to_id == subject_id and e.relation == "questions"]
    assert len(edge_to_subject) == 1


def test_qstorm_05_question_to_question_relations(tmp_path: Path):
    """QSTORM-05: 5 canonical question-to-question edge relations (broadens, narrows, etc.)."""
    _, service, subject_id = _setup_store_and_subject(tmp_path)

    q_parent = service.create_question(
        subject_id=subject_id,
        text="How might we extend cold-weather run time?",
    )
    q_child = service.create_question(
        subject_id=subject_id,
        text="Can insulated aerogel pouch packaging double thermal retention?",
        form="closed",
        parent_question_id=q_parent.id,
        relation="narrows",
    )

    child_edges = [e for e in q_child.edges if e.to_id == q_parent.id]
    assert len(child_edges) == 1
    assert child_edges[0].relation == "narrows"

    # Test explicit link_questions
    edge = service.link_questions(from_id=q_parent.id, to_id=q_child.id, relation="broadens")
    assert edge is not None
    assert edge.relation == "broadens"


def test_qstorm_06_berger_moves_generate_stems():
    """QSTORM-06: Berger questioning moves generate starter prompts."""
    stems = get_berger_stems()
    assert "why" in stems
    assert "constraint_removal" in stems
    assert "inversion" in stems

    stem_why = apply_berger_move("why", "Battery drain in winter")
    assert "Why is Battery drain in winter currently done this way?" in stem_why

    stem_inv = apply_berger_move("inversion", "High refresh rate screen")
    assert "What if the complete opposite were true for High refresh rate screen?" in stem_inv


def test_qstorm_07_transform_open_closed_creates_linked_question(tmp_path: Path):
    """QSTORM-07: Transforming open <-> closed creates linked node with directional edge."""
    _, service, subject_id = _setup_store_and_subject(tmp_path)

    open_q = service.create_question(
        subject_id=subject_id,
        text="What power sources are viable in freezing temperatures?",
        form="open",
    )

    closed_q = service.transform_open_closed(
        question_id=open_q.id,
        new_text="Is a lithium-titanate (LTO) cell viable below -20C?",
    )
    assert closed_q is not None
    assert closed_q.attrs["form"] == "closed"
    rel_edges = [e for e in closed_q.edges if e.to_id == open_q.id]
    assert len(rel_edges) == 1
    assert rel_edges[0].relation == "narrows"


def test_qstorm_08_question_creation_logs_events_and_stamps_author(tmp_path: Path):
    """QSTORM-08: Question creation logs write events to events.jsonl and stamps attribution."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)
    service = QuestionstormService(store=store)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    service.create_question(
        subject_id="FRI-A01",
        text="What if we didn't use a screen at all?",
        author=author,
    )

    events = event_log.read_events()
    assert len(events) >= 1
    assert events[-1].subject_id == "QUE-A01"
    assert events[-1].author.kind == AuthorKind.HUMAN
