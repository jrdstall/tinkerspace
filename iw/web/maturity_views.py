"""Maturity Board and Worth Matrix Web Views.

Layer 4 Web surface module. Depends on iw.contracts, iw.domain.assessor, and starlette.
Governed by V§11 and MATBOARD-01 through MATBOARD-06.
"""

from typing import Any
from starlette.requests import Request
from starlette.responses import Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Node
from iw.contracts.store import StoreProtocol
from iw.domain.assessor.cml import (
    compute_cml,
    identify_laggards,
    recommend_activity_for_laggard,
)


def _enrich_idea(node: Node) -> dict[str, Any]:
    """Extract and compute assessment, CML, and laggard metadata for an idea node."""
    scores_raw = node.attrs.get("scores", {})
    scores = {k: int(v) for k, v in scores_raw.items() if isinstance(v, (int, float))}
    cml_val = compute_cml(scores) if scores else int(node.attrs.get("cml", 1))
    laggards = identify_laggards(scores)
    rec_activity = recommend_activity_for_laggard(laggards[0]) if laggards else "screening-assessment@1"

    return {
        "node": node,
        "scores": scores,
        "cml": cml_val,
        "laggards": laggards,
        "primary_laggard": laggards[0] if laggards else None,
        "activity_rec": rec_activity,
        "worth_to_me": node.attrs.get("worth_to_me", "medium"),
        "worth_to_others": node.attrs.get("worth_to_others", "low"),
        "screening_verdict": node.attrs.get("screening_verdict"),
        "concept_graphic": node.attrs.get("concept_graphic"),
    }


def _filter_ideas(
    items: list[dict[str, Any]],
    domain: str,
    verdict: str,
    worth_me: str,
    worth_others: str,
) -> list[dict[str, Any]]:
    """Filter enriched idea items by domain, screening verdict, and worth ratings."""
    filtered = items
    if domain:
        filtered = [i for i in filtered if i["node"].domain.lower() == domain.lower()]
    if verdict:
        filtered = [i for i in filtered if str(i.get("screening_verdict") or "").lower() == verdict.lower()]
    if worth_me:
        filtered = [i for i in filtered if str(i.get("worth_to_me") or "").lower() == worth_me.lower()]
    if worth_others:
        filtered = [i for i in filtered if str(i.get("worth_to_others") or "").lower() == worth_others.lower()]
    return filtered


def _sort_ideas(items: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    """Sort enriched ideas by laggard score, CML, or title."""
    if sort_by == "laggard":
        return sorted(items, key=lambda x: (x["cml"], x["node"].title.lower()))
    if sort_by == "title":
        return sorted(items, key=lambda x: x["node"].title.lower())
    return sorted(items, key=lambda x: x["node"].created, reverse=True)


def _partition_cml_columns(items: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """Group items into 5 sequential CML columns."""
    columns: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: [], 4: [], 5: []}
    for item in items:
        lvl = max(1, min(5, item["cml"]))
        columns[lvl].append(item)
    return columns


def _partition_worth_quadrants(
    items: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition items into Passion Projects, High Impact, The Trap, and Other."""
    passion = [i for i in items if i["worth_to_me"] == "high" and i["worth_to_others"] != "high"]
    high_impact = [i for i in items if i["worth_to_me"] == "high" and i["worth_to_others"] == "high"]
    trap = [i for i in items if i["worth_to_me"] != "high" and i["worth_to_others"] == "high"]
    other = [i for i in items if i not in passion and i not in high_impact and i not in trap]
    return passion, high_impact, trap, other


async def maturity_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the Maturity Board and Worth Matrix surfaces."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    all_nodes = store.list_nodes()

    idea_nodes = [n for n in all_nodes if n.type == "idea"]
    enriched = [_enrich_idea(n) for n in idea_nodes]

    domain = request.query_params.get("domain", "").strip()
    verdict = request.query_params.get("verdict", "").strip()
    worth_me = request.query_params.get("worth_me", "").strip()
    worth_others = request.query_params.get("worth_others", "").strip()
    view_mode = request.query_params.get("view", "columns").strip()
    sort_by = request.query_params.get("sort", "laggard").strip()

    filtered = _filter_ideas(enriched, domain, verdict, worth_me, worth_others)
    sorted_ideas = _sort_ideas(filtered, sort_by)

    cml_columns = _partition_cml_columns(sorted_ideas)
    passion, high_impact, trap, other = _partition_worth_quadrants(sorted_ideas)
    domains = sorted(list(set(n.domain for n in idea_nodes if n.domain)))

    return templates.TemplateResponse(
        request=request,
        name="maturity.html",
        context={
            "request": request, "cml_columns": cml_columns, "total_ideas": len(idea_nodes),
            "passion_projects": passion, "high_impact": high_impact, "the_trap": trap,
            "hobby_other": other, "view_mode": view_mode, "domains": domains,
            "current_domain": domain, "current_verdict": verdict, "current_worth_me": worth_me,
            "current_worth_others": worth_others, "current_sort": sort_by,
            "inbox_count": len(store.list_inbox()), "drop_count": len(store.list_dropped_files()),
        },
    )
