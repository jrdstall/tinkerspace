"""Behaviour tests for Custom Creative Exercises and Active Ideation Prompts (EXERCISE-10, EXERCISE-11).

Proves EXERCISE-10 and EXERCISE-11 from docs/design/specs/EXERCISE.md:
- EXERCISE-10: Users may construct one-off custom exercise prompts per exercise type
  and load them into the active exercise session without persisting them to seed banks.
- EXERCISE-11: For any active exercise prompt (pre-made or custom), the system generates
  a tailored, ready-to-copy LLM ideation prompt.
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.exercises import CustomExerciseInput
from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.exercises.custom import (
    build_custom_exercise_prompt,
    build_ideation_llm_prompt,
)
from iw.web.app import create_app


def test_exercise_10_domain_custom_prompts_all_types(tmp_path: Path) -> None:
    """EXERCISE-10: Domain builder constructs structured prompts per exercise type without mutating seeds."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="IDEA-A01",
        type="idea",
        title="Magnetic Gear Reducer",
        created=datetime.now(timezone.utc),
        domain="robotics",
        tags=["actuators"],
        state="active",
    )
    store.write_node(node, author=author)

    # 1. Custom 3-Word Triad
    triad_inp = CustomExerciseInput(
        exercise_type="triad",
        word_1="ferrofluid",
        word_2="origami",
        word_3="periscope",
    )
    triad_prompt = build_custom_exercise_prompt(triad_inp, store=store)
    assert triad_prompt.exercise_type == "triad"
    assert triad_prompt.prompt_text == "ferrofluid • origami • periscope"
    assert triad_prompt.metadata.get("custom") == "true"

    # 2. Custom Cross-Domain What-If
    what_if_inp = CustomExerciseInput(
        exercise_type="what_if",
        entity="Formula 1 Pit Crew",
        system="a hospital emergency room",
    )
    what_if_prompt = build_custom_exercise_prompt(what_if_inp, store=store)
    assert what_if_prompt.exercise_type == "what_if"
    assert what_if_prompt.prompt_text == "What if Formula 1 Pit Crew ran a hospital emergency room?"

    # 3. Custom Vault Hybrid
    vault_inp = CustomExerciseInput(
        exercise_type="vault_hybrid",
        node_id="IDEA-A01",
        wildcard="caterpillar",
    )
    vault_prompt = build_custom_exercise_prompt(vault_inp, store=store)
    assert vault_prompt.exercise_type == "vault_hybrid"
    assert "'Magnetic Gear Reducer'  ✕  [CATERPILLAR]" in vault_prompt.prompt_text
    assert "IDEA-A01" in vault_prompt.title

    # 4. Custom Paradox, Biomimicry, Assumption, Freeform
    paradox_prompt = build_custom_exercise_prompt(
        CustomExerciseInput(exercise_type="paradox", custom_text="A soldering iron that never gets hot")
    )
    assert paradox_prompt.prompt_text == "A soldering iron that never gets hot"

    bio_prompt = build_custom_exercise_prompt(
        CustomExerciseInput(exercise_type="biomimicry", organism="Gecko", custom_text="Van der Waals dry adhesion")
    )
    assert "Gecko" in bio_prompt.title
    assert bio_prompt.prompt_text == "Van der Waals dry adhesion"

    assump_prompt = build_custom_exercise_prompt(
        CustomExerciseInput(
            exercise_type="assumption",
            standard_assumption="3D printers move the nozzle over a bed",
            inversion="The nozzle stays fixed while the room rotates",
        )
    )
    assert "3D printers move the nozzle over a bed" in assump_prompt.prompt_text
    assert "The nozzle stays fixed while the room rotates" in assump_prompt.prompt_text

    # Confirm no seed files were written to vault/exercises
    assert not (vault_dir / "exercises" / "triads.yaml").exists()


def test_exercise_11_ideation_llm_prompt_generation() -> None:
    """EXERCISE-11: Tailored LLM ideation prompt includes active prompt title, text, and challenge."""
    inp = CustomExerciseInput(
        exercise_type="triad",
        word_1="gyroscope",
        word_2="moss",
        word_3="bellows",
    )
    prompt = build_custom_exercise_prompt(inp)
    llm_prompt = build_ideation_llm_prompt(prompt)

    assert "3-Word Triad (Custom)" in llm_prompt
    assert "gyroscope • moss • bellows" in llm_prompt
    assert "Core Mechanism" in llm_prompt
    assert "Surprising Use Case" in llm_prompt


def test_exercise_10_11_web_custom_flow_and_capture(tmp_path: Path) -> None:
    """EXERCISE-10 & EXERCISE-11: Web POST /exercises/custom loads custom 3 words and captures to inbox."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. Submit custom 3-word triad via POST /exercises/custom
    resp = client.post(
        "/exercises/custom",
        data={
            "exercise_type": "triad",
            "word_1": "laser",
            "word_2": "bonsai",
            "word_3": "trampoline",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "3-Word Triad (Custom)" in resp.text
    assert "laser • bonsai • trampoline" in resp.text
    # Verify EXERCISE-11 LLM ideation prompt is rendered on page
    assert "Copy AI Ideation Prompt" in resp.text
    assert "Starting Prompt: laser • bonsai • trampoline" in resp.text

    # 2. Capture ideation result into inbox from custom exercise
    cap_resp = client.post(
        "/exercises/capture",
        data={
            "exercise_type": "triad",
            "prompt_title": "3-Word Triad (Custom)",
            "prompt_text": "laser • bonsai • trampoline",
            "raw_text": "Optical tensioned canopy that prunes miniature trees via focused light.",
        },
        follow_redirects=True,
    )
    assert cap_resp.status_code == 200
    assert "Thought Captured!" in cap_resp.text

    inbox = store.list_inbox()
    assert len(inbox) == 1
    assert "[Creative Exercise: 3-Word Triad (Custom) — laser • bonsai • trampoline]" in inbox[0].raw_text
    assert "Optical tensioned canopy" in inbox[0].raw_text

    # Confirm custom words were not saved into vault seed banks
    assert not (vault_dir / "exercises" / "triads.yaml").exists()
