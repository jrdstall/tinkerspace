"""Question Graph Web Views and Fast Questioning Actions.

Layer 4 Web surface module. Depends on iw.contracts, iw.domain.questionstorm, and starlette.
Governed by Vision §12 and QGRAPH-01 through QGRAPH-06.
"""

import json
from typing import Any
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind, Node
from iw.contracts.store import StoreProtocol
from iw.domain.questionstorm.graph import generate_mermaid_graph
from iw.domain.questionstorm.models import BERGER_MOVES, QUESTION_RELATIONS
from iw.domain.questionstorm.moves import apply_berger_move
from iw.domain.questionstorm.service import QuestionstormService


def _enrich_question(q: Node) -> dict[str, Any]:
    """Enrich a question node with connected relations and form/importance metadata."""
    out_edges = [
        {"to_id": e.to_id, "relation": e.relation}
        for e in q.edges if e.relation != "questions"
    ]
    return {
        "node": q,
        "id": q.id,
        "title": q.title,
        "form": q.attrs.get("form", "open"),
        "importance": q.attrs.get("importance", "medium"),
        "move": q.attrs.get("move", "why"),
        "state": q.state,
        "out_edges": out_edges,
        "is_orphan": len(out_edges) == 0,
    }


def _build_graph_context(
    request: Request, subject: Node, question_nodes: list[Node], store: StoreProtocol,
) -> dict[str, Any]:
    enriched = [_enrich_question(q) for q in question_nodes]
    selected_move = request.query_params.get("move", "why")
    is_added = request.query_params.get("added") == "1"
    suggested_stem = "" if is_added else apply_berger_move(selected_move, subject.title)
    all_stems = {k: apply_berger_move(k, subject.title) for k in BERGER_MOVES.keys()}
    mermaid_code = generate_mermaid_graph(subject, question_nodes)
    return {
        "request": request, "subject": subject,
        "open_questions": [q for q in enriched if q["form"] == "open"],
        "closed_questions": [q for q in enriched if q["form"] == "closed"],
        "total_questions": len(question_nodes), "berger_moves": BERGER_MOVES,
        "berger_stems_json": json.dumps(all_stems),
        "mermaid_code": mermaid_code,
        "relations": [r for r in QUESTION_RELATIONS if r != "questions"],
        "selected_move": selected_move, "suggested_stem": suggested_stem,
        "just_added": is_added, "inbox_count": len(store.list_inbox()),
        "drop_count": len(store.list_dropped_files()),
    }


async def question_graph_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the visual Question Graph DAG surface for a subject node."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    subject_id = request.path_params.get("subject_id", "").strip().upper()
    subject = store.get_node(subject_id)
    if subject is None:
        return HTMLResponse(f"<h1>404 Not Found</h1><p>Subject node '{subject_id}' not found.</p>", status_code=404)

    service = QuestionstormService(store=store)
    question_nodes = service.resolve_subject_questions(subject_id)
    ctx = _build_graph_context(request, subject, question_nodes, store)
    return templates.TemplateResponse(request=request, name="question_graph.html", context=ctx)



async def question_create_action(request: Request) -> Response:
    """Handle creating a new question attached to a subject node."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    subject_id = str(form.get("subject_id", "")).strip().upper()
    text = str(form.get("text", "")).strip()
    q_form = str(form.get("form", "open")).strip()
    importance = str(form.get("importance", "medium")).strip()
    move = str(form.get("move", "why")).strip()
    parent_id = str(form.get("parent_id", "")).strip().upper() or None
    relation = str(form.get("relation", "reframes")).strip()

    if subject_id and text:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        service = QuestionstormService(store=store)
        service.create_question(
            subject_id=subject_id, text=text, form=q_form,
            importance=importance, move=move, parent_question_id=parent_id,
            relation=relation, author=author,
        )

    return RedirectResponse(url=f"/question-graph/{subject_id}?added=1", status_code=303)


async def question_transform_action(request: Request) -> Response:
    """Handle open <-> closed question transformations."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    question_id = str(form.get("question_id", "")).strip().upper()
    new_text = str(form.get("new_text", "")).strip()
    subject_id = str(form.get("subject_id", "")).strip().upper()

    if question_id and new_text:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        service = QuestionstormService(store=store)
        service.transform_open_closed(question_id=question_id, new_text=new_text, author=author)

    return RedirectResponse(url=f"/question-graph/{subject_id}", status_code=303)


async def question_link_action(request: Request) -> Response:
    """Handle linking two existing question nodes with a typed relation."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    from_id = str(form.get("from_id", "")).strip().upper()
    to_id = str(form.get("to_id", "")).strip().upper()
    relation = str(form.get("relation", "sibling")).strip()
    subject_id = str(form.get("subject_id", "")).strip().upper()

    if from_id and to_id and relation:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        service = QuestionstormService(store=store)
        service.link_questions(from_id=from_id, to_id=to_id, relation=relation, author=author)

    return RedirectResponse(url=f"/question-graph/{subject_id}", status_code=303)
