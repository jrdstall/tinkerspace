"""Questionstorming Service orchestrating question nodes and relationship graph.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.questionstorm.models, and stdlib.
Governed by Vision §12 and QSTORM-01 through QSTORM-08.
"""

from datetime import datetime, timezone
from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.domain.questionstorm.models import (
    QUESTION_RELATIONS,
    QuestionForm,
    QuestionImportance,
)
from iw.domain.questionstorm.moves import (
    invert_question_form,
    suggest_relation_for_transform,
)


def _build_edges(qid: str, subject_id: str, parent_id: str | None, relation: str, now: datetime, auth: Author) -> list[Edge]:
    """Construct initial subject and parent relationship edges for a question."""
    edges = [Edge(from_id=qid, to_id=subject_id.upper(), relation="questions", created=now, author=auth)]
    if parent_id:
        clean_rel = relation if relation in QUESTION_RELATIONS else "reframes"
        edges.append(Edge(from_id=qid, to_id=parent_id.upper(), relation=clean_rel, created=now, author=auth))
    return edges


class QuestionstormService:
    """Orchestrates Question node creation, transforms, and edge linking."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    def create_question(
        self,
        subject_id: str,
        text: str,
        form: str = "open",
        importance: str = "medium",
        move: str = "why",
        parent_question_id: str | None = None,
        relation: str = "reframes",
        author: Author | None = None,
    ) -> Node:
        """Create a new Question node linked to the subject and optional parent question."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        subject = self.store.get_node(subject_id)
        domain = subject.domain if subject else "meta"
        tags = list(subject.tags) if subject else ["questionstorm"]
        if "question" not in tags:
            tags.append("question")

        clean_form = form.lower() if form.lower() in [f.value for f in QuestionForm] else "open"
        clean_imp = importance.lower() if importance.lower() in [i.value for i in QuestionImportance] else "medium"
        now = datetime.now(timezone.utc)
        qid = self.store.allocate_id("QUE")
        edges = _build_edges(qid, subject_id, parent_question_id, relation, now, auth)

        node = Node(
            id=qid, type="question", title=text.strip(), created=now, domain=domain, tags=tags,
            state="held_open", author=auth, last_touched=now, body="",
            attrs={"form": clean_form, "importance": clean_imp, "move": move, "subject_id": subject_id.upper()},
            edges=edges,
        )
        self.store.write_node(node, author=auth)
        return node

    def transform_open_closed(
        self,
        question_id: str,
        new_text: str,
        author: Author | None = None,
    ) -> Node | None:
        """Transform a question into its opposite form, linking with directional edge."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        source = self.store.get_node(question_id)
        if source is None:
            return None

        current_form = source.attrs.get("form", "open")
        new_form = invert_question_form(current_form)
        relation = suggest_relation_for_transform(current_form, new_form)

        subject_id = str(source.attrs.get("subject_id") or "")
        if not subject_id:
            for e in source.edges:
                if e.relation == "questions":
                    subject_id = e.to_id
                    break

        return self.create_question(
            subject_id=subject_id or source.id,
            text=new_text,
            form=new_form,
            importance=source.attrs.get("importance", "medium"),
            move="open_closed",
            parent_question_id=source.id,
            relation=relation,
            author=auth,
        )

    def link_questions(
        self,
        from_id: str,
        to_id: str,
        relation: str,
        author: Author | None = None,
    ) -> Edge | None:
        """Create a directional relationship edge between two question nodes."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        from_node = self.store.get_node(from_id)
        if from_node is None:
            return None

        clean_rel = relation if relation in QUESTION_RELATIONS else "sibling"
        now = datetime.now(timezone.utc)
        edge = Edge(from_id=from_id.upper(), to_id=to_id.upper(), relation=clean_rel, created=now, author=auth)

        from_node.edges.append(edge)
        self.store.write_node(from_node, author=auth)
        return edge

    def resolve_subject_questions(self, subject_id: str) -> list[Node]:
        """Resolve all question nodes connected to a subject node."""
        clean_target = subject_id.upper()
        all_nodes = self.store.list_nodes()
        questions: list[Node] = []
        for n in all_nodes:
            if n.type == "question":
                for e in n.edges:
                    if e.to_id.upper() == clean_target and e.relation == "questions":
                        questions.append(n)
                        break
        return questions
