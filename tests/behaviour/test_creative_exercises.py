"""Behaviour tests for Creative Exercises subsystem.

Proves EXERCISE-01 through EXERCISE-08 from docs/design/specs/EXERCISE.md:
- EXERCISE-01: Seed bank loader hierarchy (vault with fallback to content)
- EXERCISE-02: Triad generator samples 3 nouns across distinct categories (including tech)
- EXERCISE-03: Paradoxical constraint generator samples negative functional constraints
- EXERCISE-04: Cross-domain "What If?" generator pairs entities with alien systems
- EXERCISE-05: Biomimicry and assumption inversion generators yield structured challenges
- EXERCISE-06: Vault cross-pollination pairs active vault nodes with creative seeds
- EXERCISE-07: Seed manager supports prompt templates, import (flush/merge), and reset
- EXERCISE-08: Capture action appends scratchpad notes with prompt provenance to inbox
"""

from datetime import datetime, timezone
from pathlib import Path
from starlette.testclient import TestClient

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.exercises.combinator import ExerciseEngine
from iw.domain.exercises.loader import load_seed_bank, reset_vault_seeds, save_seed_bank
from iw.domain.exercises.manager import (
    build_seed_generation_prompt,
    import_seed_yaml,
    reset_seeds_to_defaults,
)
from iw.domain.exercises.models import ExerciseType
from iw.web.app import create_app


def test_exercise_01_loader_hierarchy(tmp_path: Path) -> None:
    """EXERCISE-01: Loader resolves content seeds by default, overridden by vault seeds."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()

    # Loads default from content
    content_triads = load_seed_bank("triads", vault_dir=vault_dir)
    assert "organic" in content_triads
    assert "technology" in content_triads

    # Override in vault
    custom_triads = {"custom_cat": ["flux_capacitor", "quantum_gizmo"]}
    save_seed_bank(vault_dir, "triads", custom_triads)

    loaded_vault = load_seed_bank("triads", vault_dir=vault_dir)
    assert "custom_cat" in loaded_vault
    assert "flux_capacitor" in loaded_vault["custom_cat"]


def test_exercise_02_triad_generator_categories() -> None:
    """EXERCISE-02: Triad generator samples 3 nouns across distinct categories including tech."""
    engine = ExerciseEngine()
    prompt = engine.generate(ExerciseType.TRIAD.value, seed=42)

    assert prompt.exercise_type == ExerciseType.TRIAD.value
    assert len(prompt.categories) == 3
    # Distinct categories
    assert len(set(prompt.categories)) == 3
    # Check words are formatted
    parts = prompt.prompt_text.split(" • ")
    assert len(parts) == 3

    # Verify technology category exists in bank and can be sampled
    bank = load_seed_bank("triads")
    assert "technology" in bank
    assert any("lidar" in w or "microcontroller" in w or "sensor" in w for w in bank["technology"])


def test_exercise_03_paradox_generator() -> None:
    """EXERCISE-03: Paradoxical constraint generator samples negative functional constraints."""
    engine = ExerciseEngine()
    prompt = engine.generate(ExerciseType.PARADOX.value, seed=123)

    assert prompt.exercise_type == ExerciseType.PARADOX.value
    assert len(prompt.prompt_text) > 0
    assert "A " in prompt.prompt_text or "that" in prompt.prompt_text or "doesn't" in prompt.prompt_text


def test_exercise_04_what_if_generator() -> None:
    """EXERCISE-04: Cross-domain generator pairs organizational archetypes with systems."""
    engine = ExerciseEngine()
    prompt = engine.generate(ExerciseType.WHAT_IF.value, seed=99)

    assert prompt.exercise_type == ExerciseType.WHAT_IF.value
    assert "What if " in prompt.prompt_text or "ran " in prompt.prompt_text


def test_exercise_05_biomimicry_and_assumptions() -> None:
    """EXERCISE-05: Biomimicry and assumption inversion generators yield structured challenges."""
    engine = ExerciseEngine()

    bio_prompt = engine.generate(ExerciseType.BIOMIMICRY.value, seed=7)
    assert bio_prompt.exercise_type == ExerciseType.BIOMIMICRY.value
    assert len(bio_prompt.prompt_text) > 0
    assert len(bio_prompt.sub_text) > 0

    assump_prompt = engine.generate(ExerciseType.ASSUMPTION.value, seed=7)
    assert assump_prompt.exercise_type == ExerciseType.ASSUMPTION.value
    assert "Inversion" in assump_prompt.prompt_text or "➔" in assump_prompt.prompt_text


def test_exercise_06_vault_cross_pollination(tmp_path: Path) -> None:
    """EXERCISE-06: Vault cross-pollination pairs active vault nodes with creative seeds."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    author = Author(kind=AuthorKind.HUMAN, courier="web-ui")
    node = Node(
        id="IDEA-A01", type="idea", title="Autonomous Solar Weeder",
        created=datetime.now(timezone.utc), domain="robotics", tags=["robotics"], state="active",
    )
    store.write_node(node, author=author)

    engine = ExerciseEngine(vault_dir=vault_dir, store=store)
    prompt = engine.generate(ExerciseType.VAULT_HYBRID.value, seed=1)

    assert prompt.exercise_type == ExerciseType.VAULT_HYBRID.value
    assert "Autonomous Solar Weeder" in prompt.prompt_text
    assert "IDEA-A01" in prompt.title


def test_exercise_07_seed_manager_prompt_and_import(tmp_path: Path) -> None:
    """EXERCISE-07: Seed manager supports prompt templating, flush/replace, merge, and reset."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()

    # 1. Prompt builder
    prompt_str = build_seed_generation_prompt("triads", count=15)
    assert "organic:" in prompt_str
    assert "technology:" in prompt_str
    assert "YAML" in prompt_str

    # 2. Replace mode (Flush and replace)
    incoming_yaml = "organic:\n  - mutant_fern\ntechnology:\n  - quantum_core\n"
    res1 = import_seed_yaml(vault_dir, "triads", incoming_yaml, mode="replace")
    assert res1["status"] == "ok"

    loaded = load_seed_bank("triads", vault_dir=vault_dir)
    assert loaded == {"organic": ["mutant_fern"], "technology": ["quantum_core"]}

    # 3. Merge mode
    merge_yaml = "organic:\n  - mutant_fern\n  - glowing_moss\n"
    res2 = import_seed_yaml(vault_dir, "triads", merge_yaml, mode="merge")
    assert res2["status"] == "ok"

    loaded_merged = load_seed_bank("triads", vault_dir=vault_dir)
    assert "quantum_core" in loaded_merged["technology"]
    assert "glowing_moss" in loaded_merged["organic"]
    # No duplicate for mutant_fern
    assert loaded_merged["organic"].count("mutant_fern") == 1

    # 4. Reset to defaults
    copied = reset_seeds_to_defaults(vault_dir)
    assert len(copied) > 0
    loaded_reset = load_seed_bank("triads", vault_dir=vault_dir)
    assert "mechanical_tools" in loaded_reset


def test_exercise_08_web_view_and_capture(tmp_path: Path) -> None:
    """EXERCISE-08: Web surface renders gym and captures scratchpad thoughts into inbox."""
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    event_log = FileEventLog(vault_dir / "events.jsonl")
    store = MarkdownStore(vault_dir=vault_dir, event_log=event_log)

    app = create_app(store=store)
    client = TestClient(app)

    # 1. GET /exercises
    resp = client.get("/exercises?type=triad")
    assert resp.status_code == 200
    assert "Creative Exercises" in resp.text
    assert "3-Word Triad" in resp.text
    assert "Ideation Scratchpad" in resp.text

    # 2. POST /exercises/capture
    capture_resp = client.post(
        "/exercises/capture",
        data={
            "exercise_type": "triad",
            "prompt_title": "3-Word Triad",
            "prompt_text": "printer • house • caterpillar",
            "raw_text": "Tiny 3D printers that crawl like silkworms.",
        },
        follow_redirects=True,
    )
    assert capture_resp.status_code == 200
    assert "Thought Captured!" in capture_resp.text

    inbox_items = store.list_inbox()
    assert len(inbox_items) == 1
    item = inbox_items[0]
    events = store.event_log.read_events() if store.event_log else []
    assert any(e.kind == "inbox_captured" and e.author.courier == "creative-exercises" for e in events)
    assert "Tiny 3D printers that crawl like silkworms." in item.raw_text
    assert "[Creative Exercise: 3-Word Triad — printer • house • caterpillar]" in item.raw_text
