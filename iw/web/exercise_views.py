"""Creative Exercises web views and capture handlers.

Layer 4 Web surface component.
Governed by EXERCISE-01 through EXERCISE-11.
"""

from typing import Mapping
from urllib.parse import quote_plus, urlencode
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from starlette.templating import Jinja2Templates

from iw.contracts.exercises import CustomExerciseInput, ExercisePrompt
from iw.contracts.store import StoreProtocol
from iw.domain.exercises.combinator import ExerciseEngine
from iw.domain.exercises.custom import (
    build_custom_exercise_prompt,
    build_ideation_llm_prompt,
)
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

CUSTOM_PARAM_KEYS = (
    "word_1", "word_2", "word_3", "entity", "system",
    "node_id", "wildcard", "organism", "standard_assumption",
    "inversion", "custom_text", "custom_title",
)


def _extract_custom_input(req_type: str, params: Mapping[str, object]) -> CustomExerciseInput:
    """Extract structured CustomExerciseInput from query or form mapping."""
    return CustomExerciseInput(
        exercise_type=str(params.get("exercise_type", req_type)).strip().lower() or req_type,
        word_1=str(params.get("word_1", "")).strip(),
        word_2=str(params.get("word_2", "")).strip(),
        word_3=str(params.get("word_3", "")).strip(),
        entity=str(params.get("entity", "")).strip(),
        system=str(params.get("system", "")).strip(),
        node_id=str(params.get("node_id", "")).strip(),
        wildcard=str(params.get("wildcard", "")).strip(),
        organism=str(params.get("organism", "")).strip(),
        standard_assumption=str(params.get("standard_assumption", "")).strip(),
        inversion=str(params.get("inversion", "")).strip(),
        custom_text=str(params.get("custom_text", "")).strip(),
        custom_title=str(params.get("custom_title", "")).strip(),
    )


def _resolve_active_prompt(
    request: Request,
    req_type: str,
    engine: ExerciseEngine,
    store: StoreProtocol,
) -> tuple[ExercisePrompt, CustomExerciseInput, bool]:
    """Resolve either a user-supplied custom prompt or a sampled pre-made prompt."""
    qp = request.query_params
    has_custom = qp.get("custom") == "1" or any(str(qp.get(k, "")).strip() for k in CUSTOM_PARAM_KEYS)
    custom_inp = _extract_custom_input(req_type, qp)
    if has_custom:
        prompt = build_custom_exercise_prompt(custom_inp, store=store)
        return prompt, custom_inp, True
    return engine.generate(exercise_type=req_type), custom_inp, False


async def exercise_view(request: Request, templates: Jinja2Templates) -> Response:
    """Render the Creative Exercises gym surface."""
    store: StoreProtocol = request.app.state.store
    store.sync_refresh()
    req_type = request.query_params.get("type", "surprise").strip().lower()
    captured_id = request.query_params.get("captured", "").strip()
    notice = request.query_params.get("notice", "").strip()

    engine = ExerciseEngine(vault_dir=store.vault_dir, store=store)
    prompt, custom_inp, is_custom = _resolve_active_prompt(request, req_type, engine, store)

    prompt_key = req_type if req_type in ("triad", "paradox", "what_if") else "triads"
    ai_prompt = build_seed_generation_prompt(prompt_key)
    ideation_prompt = build_ideation_llm_prompt(prompt)
    active_nodes = [n for n in store.list_nodes() if n.state == "active"]

    return templates.TemplateResponse(
        request=request,
        name="exercises.html",
        context={
            "request": request,
            "current_type": req_type,
            "prompt": prompt,
            "is_custom": is_custom,
            "custom_input": custom_inp,
            "active_nodes": active_nodes,
            "ideation_llm_prompt": ideation_prompt,
            "nav_options": EXERCISE_NAV_OPTIONS,
            "captured_id": captured_id,
            "notice": notice,
            "ai_prompt_template": ai_prompt,
            "inbox_count": len(store.list_inbox()),
            "drop_count": len(store.list_dropped_files()),
            "done_count": len(engine.list_done()),
        },
    )


async def exercise_custom_action(request: Request) -> Response:
    """Load user-supplied custom exercise prompt into the active exercise session (EXERCISE-10)."""
    form = await request.form()
    req_type = str(form.get("exercise_type", "triad")).strip().lower() or "triad"
    query_dict: dict[str, str] = {"type": req_type, "custom": "1"}
    for key in CUSTOM_PARAM_KEYS:
        val = str(form.get(key, "")).strip()
        if val:
            query_dict[key] = val
    return RedirectResponse(url=f"/exercises?{urlencode(query_dict)}", status_code=303)


async def exercise_capture_action(request: Request) -> Response:
    """Capture scratchpad thought with prompt provenance into inbox (EXERCISE-08)."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    raw_text = str(form.get("raw_text", "")).strip()
    exercise_type = str(form.get("exercise_type", "surprise")).strip()
    prompt_title = str(form.get("prompt_title", "")).strip()
    prompt_text = str(form.get("prompt_text", "")).strip()
    mark_done = str(form.get("mark_done", "")).strip().lower() == "true"

    if mark_done and prompt_text:
        engine = ExerciseEngine(vault_dir=store.vault_dir, store=store)
        engine.mark_done(prompt_text, prompt_title)

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


async def exercise_done_action(request: Request) -> Response:
    """Mark an exercise as done and retired from future sampling (EXERCISE-09)."""
    store: StoreProtocol = request.app.state.store
    form = await request.form()
    exercise_type = str(form.get("exercise_type", "surprise")).strip()
    prompt_title = str(form.get("prompt_title", "")).strip()
    prompt_text = str(form.get("prompt_text", "")).strip()
    if prompt_text:
        engine = ExerciseEngine(vault_dir=store.vault_dir, store=store)
        engine.mark_done(prompt_text, prompt_title)
        notice = quote_plus("✓ Exercise marked as done and retired from future use.")
        return RedirectResponse(url=f"/exercises?type={exercise_type}&notice={notice}", status_code=303)
    return RedirectResponse(url=f"/exercises?type={exercise_type}", status_code=303)


async def exercise_reset_done_action(request: Request) -> Response:
    """Reset completed exercises pool back into active circulation (EXERCISE-09)."""
    store: StoreProtocol = request.app.state.store
    engine = ExerciseEngine(vault_dir=store.vault_dir, store=store)
    engine.reset_done()
    notice = quote_plus("Completed exercises have been reset back into circulation.")
    return RedirectResponse(url=f"/exercises?notice={notice}", status_code=303)
