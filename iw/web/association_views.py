"""Association Review Deck and Triage Web Views.

Layer 4 Web surface module. Depends on iw.contracts, iw.domain.association, and starlette.
Governed by Vision §13 and ASSOCREV-01 through ASSOCREV-06.
"""

from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind
from iw.contracts.store import StoreProtocol
from iw.domain.association.pipeline import AssociationPipeline
from iw.domain.association.review import (
    append_proposal,
    compute_sampler_telemetry,
    mark_proposal_reviewed,
    read_all_proposals,
)


async def association_deck_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the single-card rapid Association Review deck."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    all_proposals = read_all_proposals(store.vault_dir)
    pending = [p for p in all_proposals if not p.reviewed]
    current_card = pending[0] if pending else None

    events = store.event_log.read_events()
    telemetry = compute_sampler_telemetry(events)

    return templates.TemplateResponse(
        request=request,
        name="associations.html",
        context={
            "request": request,
            "current_card": current_card,
            "pending_count": len(pending),
            "total_reviewed": len(all_proposals) - len(pending),
            "telemetry": telemetry,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
        },
    )


async def association_keep_action(request: Request) -> Response:
    """Handle Keep action (K) promoting proposal to Idea node."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    prop_id = str(form.get("proposal_id", "")).strip()

    all_proposals = read_all_proposals(store.vault_dir)
    target = next((p for p in all_proposals if p.id == prop_id), None)
    if target:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        pipeline = AssociationPipeline(store=store)
        idea = pipeline.convert_proposal_to_idea(target, author=author)
        mark_proposal_reviewed(store.vault_dir, target.id, "keep", derived_idea_id=idea.id)

        store.event_log.append(
            kind="association_reviewed", subject_id=target.id, author=author,
            payload={"strategy": target.sampler_strategy, "decision": "keep", "idea_id": idea.id},
        )

    return RedirectResponse(url="/associations", status_code=303)


async def association_discard_action(request: Request) -> Response:
    """Handle Discard action (D) archiving candidate."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    prop_id = str(form.get("proposal_id", "")).strip()

    all_proposals = read_all_proposals(store.vault_dir)
    target = next((p for p in all_proposals if p.id == prop_id), None)
    if target:
        author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
        mark_proposal_reviewed(store.vault_dir, target.id, "discard")

        store.event_log.append(
            kind="association_reviewed", subject_id=target.id, author=author,
            payload={"strategy": target.sampler_strategy, "decision": "discard"},
        )

    return RedirectResponse(url="/associations", status_code=303)


async def association_generate_action(request: Request) -> Response:
    """Handle generating a new batch of candidate association proposals."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    strategy = str(form.get("strategy", "anti_similar")).strip()
    count_val = int(form.get("count", 3))

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    pipeline = AssociationPipeline(store=store)
    candidates = pipeline.generate_candidate_pairs(strategy_name=strategy, count=count_val)
    for c in candidates:
        prop = pipeline.synthesize_proposal(c, author=author)
        append_proposal(store.vault_dir, prop)

    return RedirectResponse(url="/associations", status_code=303)
