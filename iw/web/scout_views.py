"""Web route handlers for Scout standing interests and recommended activities."""

from pathlib import Path
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.models import Author, AuthorKind
from iw.contracts.store import StoreProtocol
from iw.domain.planner.service import PlannerService
from iw.domain.scout.service import ScoutService


def _get_scout(request: Request) -> ScoutService:
    store: StoreProtocol = request.app.state.store
    storage_path = store.vault_dir / "meta" / "scout_interests.json"
    return ScoutService(storage_path=storage_path)


async def scout_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render standing interests and current recommended activity offers."""
    scout = _get_scout(request)
    interests = scout.list_interests(active_only=False)
    offers = scout.get_stale_offers()

    return templates.TemplateResponse(
        request=request,
        name="scout.html",
        context={
            "request": request,
            "interests": interests,
            "offers": offers,
        },
    )


async def scout_create_action(request: Request) -> Response:
    """Create a new standing interest from web form."""
    form = await request.form()
    topic = str(form.get("topic", "")).strip()
    domain = str(form.get("domain", "general")).strip()
    raw_days = str(form.get("staleness_interval_days", "30")).strip()
    days = int(raw_days) if raw_days.isdigit() else 30
    subject_id = str(form.get("subject_id", "")).strip() or None
    raw_tags = str(form.get("tags", "")).strip()
    tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    if topic:
        scout = _get_scout(request)
        scout.register_interest(
            topic=topic,
            domain=domain,
            staleness_interval_days=days,
            subject_id=subject_id,
            tags=tags,
        )

    redirect_url = request.headers.get("referer", "/scout")
    return RedirectResponse(url=redirect_url, status_code=303)


async def scout_dismiss_action(request: Request) -> Response:
    """Dismiss a stale offer, resetting its interval clock."""
    interest_id = request.path_params.get("interest_id", "").strip().upper()
    scout = _get_scout(request)
    try:
        scout.dismiss_interest(interest_id)
    except KeyError:
        pass
    redirect_url = request.headers.get("referer", "/")
    return RedirectResponse(url=redirect_url, status_code=303)


async def scout_sweep_action(request: Request) -> Response:
    """Raise a sweep order for a stale interest and reset its clock."""
    interest_id = request.path_params.get("interest_id", "").strip().upper()
    scout = _get_scout(request)
    try:
        scout.record_sweep_dispatched(interest_id)
    except KeyError:
        pass

    redirect_url = request.headers.get("referer", "/board")
    return RedirectResponse(url=redirect_url, status_code=303)
