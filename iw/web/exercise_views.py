"""Creative Exercises web views and capture handlers.

Layer 4 Web surface component.
Governed by EXERCISE-01 through EXERCISE-08.
"""

from urllib.parse import quote_plus
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.store import StoreProtocol
from iw.domain.exercises.combinator import ExerciseEngine
from iw.domain.exercises.manager import (
    build_seed_generation_prompt,
    import_seed_yaml,
    reset_seeds_to_defaults,
)

EXERCISE_NAV_OPTIONS = [
    ("surprise", "🎲 Surprise Me"),
    ("triad", "3-Word Triad"),
    ("paradox", "Paradoxical Constraint"),
    ("what_if", "Cross-Domain 'What If?'"),
    ("biomimicry", "Biomimicry Spark"),
    ("assumption", "Assumption Inversion"),
    ("vault_hybrid", "Vault Wildcard"),
]


async def exercise_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the Creative Exercises gym surface."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    req_type = request.query_params.get("type", "surprise").strip().lower()
    captured_id = request.query_params.get("captured", "").strip()
    notice = request.query_params.get("notice", "").strip()

    engine = ExerciseEngine(vault_dir=store.vault_dir, store=store)
    prompt = engine.generate(exercise_type=req_type)

    prompt_key = req_type if req_type in ("triad", "paradox", "what_if") else "triads"
    ai_prompt = build_seed_generation_prompt(prompt_key)

    return templates.TemplateResponse(
        request=request,
        name="exercises.html",
        context={
            "request": request,
            "current_type": req_type,
            "prompt": prompt,
            "nav_options": EXERCISE_NAV_OPTIONS,
            "captured_id": captured_id,
            "notice": notice,
            "ai_prompt_template": ai_prompt,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
        },
    )


async def exercise_capture_action(request: Request) -> Response:
    """Capture scratchpad thought with prompt provenance into inbox (EXERCISE-08)."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    raw_text = str(form.get("raw_text", "")).strip()
    exercise_type = str(form.get("exercise_type", "surprise")).strip()
    prompt_title = str(form.get("prompt_title", "")).strip()
    prompt_text = str(form.get("prompt_text", "")).strip()

    if raw_text:
        full_note = f"[Creative Exercise: {prompt_title} — {prompt_text}]\n{raw_text}"
        item = store.append_inbox(raw_text=full_note, inlet="creative-exercises")
        return RedirectResponse(
            url=f"/exercises?type={exercise_type}&captured={item.id}",
            status_code=303,
        )
    return RedirectResponse(url=f"/exercises?type={exercise_type}", status_code=303)


async def exercise_import_action(request: Request) -> Response:
    """Import new seeds in replace or merge mode (EXERCISE-07)."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    seed_name = str(form.get("seed_name", "triads")).strip()
    mode = str(form.get("mode", "replace")).strip()
    yaml_content = str(form.get("yaml_content", "")).strip()

    if yaml_content:
        import_seed_yaml(store.vault_dir, seed_name=seed_name, yaml_text=yaml_content, mode=mode)
        notice = quote_plus(f"Updated {seed_name} seeds ({mode})")
        return RedirectResponse(url=f"/exercises?type={seed_name}&notice={notice}", status_code=303)
    return RedirectResponse(url="/exercises", status_code=303)


async def exercise_reset_action(request: Request) -> Response:
    """Reset all vault seeds to factory defaults (EXERCISE-07)."""
    store: StoreProtocol = request.app.state.store
    reset_seeds_to_defaults(store.vault_dir)
    notice = quote_plus("All seed banks reset to factory defaults")
    return RedirectResponse(url=f"/exercises?notice={notice}", status_code=303)
