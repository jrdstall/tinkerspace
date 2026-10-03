"""Behaviour tests for Creative Exercises completed/done retirement (EXERCISE-09).

Proves EXERCISE-09 from docs/design/specs/EXERCISE.md:
- EXERCISE-09: Marking an exercise prompt as done persists its identifier to vault state
  and permanently excludes it from future sampling until explicitly reset.
"""

from pathlib import Path
from starlette.testclient import TestClient

from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.exercises.combinator import ExerciseEngine
from iw.domain.exercises.loader import save_seed_bank
from iw.domain.exercises.models import ExerciseType
from iw.web.app import create_app


def test_exercise_09_domain_mark_done_and_exclude(tmp_path: Path) -> None:
    """EXERCISE-09: Engine marks prompt done, persists to done.yaml, excludes from sampling."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    engine = ExerciseEngine(vault_dir=vault_dir)

    # Initially empty done list
    assert engine.list_done() == []

    # Setup a small custom paradox seed bank with two items
    custom_paradoxes = {
        "curated": [
            "A clock that operates without hands or digits",
            "A vehicle that drives without wheels or engine",
        ]
    }
    save_seed_bank(vault_dir, "paradoxes", custom_paradoxes)

    # Mark the first one done
    first_text = "A clock that operates without hands or digits"
    engine.mark_done(first_text, title="Paradoxical Constraint")

    # Confirm it is persisted in done list
    done_items = engine.list_done()
    assert first_text in done_items
    assert (vault_dir / "exercises" / "done.yaml").exists()

    # Generate prompt multiple times; it should never yield first_text
    for seed in range(10):
        prompt = engine.generate(ExerciseType.PARADOX.value, seed=seed)
        assert prompt.prompt_text != first_text
        assert "A vehicle" in prompt.prompt_text

    # Reset done pool
    engine.reset_done()
    assert engine.list_done() == []
    assert not (vault_dir / "exercises" / "done.yaml").exists()


def test_exercise_09_web_mark_done_action(tmp_path: Path) -> None:
    """EXERCISE-09: POST /exercises/done marks prompt done and redirects with notice."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    app = create_app(store=store)
    client = TestClient(app)

    prompt_text = "drone • origami • mycelium"
    resp = client.post(
        "/exercises/done",
        data={
            "exercise_type": "triad",
            "prompt_title": "3-Word Triad",
            "prompt_text": prompt_text,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Exercise marked as done" in resp.text

    engine = ExerciseEngine(vault_dir=vault_dir, store=store)
    assert prompt_text in engine.list_done()

    # Verify done count is reflected in the gym page
    page_resp = client.get("/exercises?type=triad")
    assert page_resp.status_code == 200
    assert "Completed Exercises (1)" in page_resp.text

    # Reset via web action
    reset_resp = client.post("/exercises/done/reset", follow_redirects=True)
    assert reset_resp.status_code == 200
    assert "Completed exercises have been reset" in reset_resp.text
    assert engine.list_done() == []


def test_exercise_09_capture_with_mark_done(tmp_path: Path) -> None:
    """EXERCISE-09: POST /exercises/capture with mark_done=true captures and retires prompt."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    app = create_app(store=store)
    client = TestClient(app)

    prompt_text = "What if a jazz ensemble ran a nuclear submarine?"
    resp = client.post(
        "/exercises/capture",
        data={
            "exercise_type": "what_if",
            "prompt_title": "Cross-Domain 'What If?'",
            "prompt_text": prompt_text,
            "raw_text": "Improvised protocol execution during emergencies.",
            "mark_done": "true",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Thought Captured!" in resp.text

    # Verify inbox item created
    inbox = store.list_inbox()
    assert len(inbox) == 1
    assert "Improvised protocol" in inbox[0].raw_text

    # Verify prompt retired
    engine = ExerciseEngine(vault_dir=vault_dir, store=store)
    assert prompt_text in engine.list_done()
