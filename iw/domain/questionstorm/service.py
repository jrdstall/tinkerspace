"""Questionstorming Service orchestrating question nodes and relationship graph.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.questionstorm.models, and stdlib.
Governed by Vision §12 and QSTORM-01 through QSTORM-10.
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


def _build_edges(qid: str, subject_id: str, parent_id: str | None, rel: str, now: datetime, auth: Author) -> list[Edge]:
    edges = [Edge(from_id=qid, to_id=subject_id.upper(), relation="questions", created=now, author=auth)]
    if parent_id:
        clean_rel = rel if rel in QUESTION_RELATIONS else "reframes"
        edges.append(Edge(from_id=qid, to_id=parent_id.upper(), relation=clean_rel, created=now, author=auth))
    return edges


class QuestionstormService:
    """Orchestrates Question node creation, transforms, edits, and edge linking."""

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

        clean_form = form.lower() if form.lower() in ("open", "closed") else "open"
        clean_imp = importance.lower() if importance.lower() in ("high", "medium", "low") else "medium"
        now = datetime.now(timezone.utc)
        qid = self.store.allocate_id("QUE")
        edges = _build_edges(qid, subject_id, parent_question_id, relation, now, auth)
        node = Node(
            id=qid, type="question", title=text.strip(), created=now, domain=domain, tags=tags,
            state="held_open", author=auth, last_touched=now, body="",
            attrs={"form": clean_form, "importance": clean_imp, "move": move, "subject_id": subject_id.upper(), "is_subquestion": True},
            edges=edges,
        )
        self.store.write_node(node, author=auth)
        return node

    def update_question(
        self, question_id: str, text: str | None = None, form: str | None = None,
        importance: str | None = None, author: Author | None = None,
    ) -> Node | None:
        """Update an existing Question node's text, form, and/or importance."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        node = self.store.get_node(question_id)
        if node is None or node.type != "question":
            return None
        if text is not None and text.strip():
            node.title = text.strip()
        if form is not None and form.lower().strip() in ("open", "closed"):
            node.attrs["form"] = form.lower().strip()
        if importance is not None and importance.lower().strip() in ("high", "medium", "low"):
            node.attrs["importance"] = importance.lower().strip()
        node.last_touched = datetime.now(timezone.utc)
        self.store.write_node(node, author=auth)
        return node

    def transform_open_closed(
        self, question_id: str, new_text: str, author: Author | None = None,
    ) -> Node | None:
        """Transform a question into its opposite form, linking with directional edge."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        source = self.store.get_node(question_id)
        if source is None:
            return None

        current_form = source.attrs.get("form", "open")
        new_form = invert_question_form(current_form)
        relation = suggest_relation_for_transform(current_form, new_form)
        subj = str(source.attrs.get("subject_id") or "")
        if not subj:
            subj = next((e.to_id for e in source.edges if e.relation == "questions"), source.id)

        return self.create_question(
            subject_id=subj, text=new_text, form=new_form,
            importance=source.attrs.get("importance", "medium"),
            move="open_closed", parent_question_id=source.id,
            relation=relation, author=auth,
        )

    def link_questions(
        self, from_id: str, to_id: str, relation: str, author: Author | None = None,
    ) -> Edge | None:
        """Create or update a directional relationship edge between two question nodes."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        from_node = self.store.get_node(from_id)
        if from_node is None:
            return None

        clean_rel = relation if relation in QUESTION_RELATIONS else "sibling"
        now = datetime.now(timezone.utc)
        clean_to = to_id.upper()
        for existing in from_node.edges:
            if existing.to_id.upper() == clean_to and existing.relation != "questions":
                existing.relation = clean_rel
                existing.author = auth
                from_node.last_touched = now
                self.store.write_node(from_node, author=auth)
                return existing

        edge = Edge(from_id=from_id.upper(), to_id=clean_to, relation=clean_rel, created=now, author=auth)
        from_node.edges.append(edge)
        from_node.last_touched = now
        self.store.write_node(from_node, author=auth)
        return edge

    def update_relation(
        self, from_id: str, to_id: str, new_relation: str, author: Author | None = None,
    ) -> Edge | None:
        """Update an existing relationship relation between two questions."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        clean_from, clean_to = from_id.upper(), to_id.upper()
        clean_rel = new_relation if new_relation in QUESTION_RELATIONS else "sibling"
        now = datetime.now(timezone.utc)

        for qid, target in ((clean_from, clean_to), (clean_to, clean_from)):
            node = self.store.get_node(qid)
            if node is not None:
                for edge in node.edges:
                    if edge.to_id.upper() == target and edge.relation != "questions":
                        edge.relation = clean_rel
                        edge.author = auth
                        node.last_touched = now
                        self.store.write_node(node, author=auth)
                        return edge
        return None

    def unlink_questions(
        self, from_id: str, to_id: str, author: Author | None = None,
    ) -> bool:
        """Remove relationship edge between two question nodes."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        clean_from, clean_to = from_id.upper(), to_id.upper()
        now = datetime.now(timezone.utc)
        removed = False

        for qid, target in ((clean_from, clean_to), (clean_to, clean_from)):
            node = self.store.get_node(qid)
            if node is not None:
                initial_count = len(node.edges)
                node.edges = [e for e in node.edges if not (e.to_id.upper() == target and e.relation != "questions")]
                if len(node.edges) < initial_count:
                    node.last_touched = now
                    self.store.write_node(node, author=auth)
                    removed = True
        return removed

    def resolve_subject_questions(self, subject_id: str) -> list[Node]:
        """Resolve all question nodes connected to a subject node."""
        target = subject_id.upper()
        questions: list[Node] = []
        for n in self.store.list_nodes():
            if n.type == "question" and any(e.to_id.upper() == target and e.relation == "questions" for e in n.edges):
                questions.append(n)
        return questions
