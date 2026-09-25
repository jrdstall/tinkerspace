"""Combinatorial exercise prompt generator.

Layer 2 Domain module. Pure business logic adhering to EXERCISE-01..06.
"""

from pathlib import Path
import random
from typing import Any

from iw.contracts.exercises import ExercisePrompt
from iw.contracts.store import StoreProtocol
from iw.domain.exercises.loader import (
    clear_done_exercises, load_done_exercises, load_seed_bank, save_done_exercise,
)
from iw.domain.exercises.models import ExerciseType


def _sample_triad(bank: dict[str, Any], rng: random.Random, done: set[str] | None = None) -> ExercisePrompt:
    """Sample 3 concrete nouns across mutually distinct categories (EXERCISE-02)."""
    available_cats = [k for k, v in bank.items() if isinstance(v, list) and v]
    if len(available_cats) < 3:
        words = ["printer", "house", "caterpillar"]
        cats = ["mechanical_tools", "domestic_apparel", "organic"]
    else:
        words, cats = [], []
        for _ in range(25):
            chosen_cats = rng.sample(available_cats, 3)
            words = [rng.choice(bank[c]) for c in chosen_cats]
            cats = chosen_cats
            if not done or " • ".join(words) not in done:
                break

    prompt_text = " • ".join(words)
    return ExercisePrompt(
        exercise_type=ExerciseType.TRIAD.value,
        title="3-Word Triad",
        prompt_text=prompt_text,
        sub_text="Riff on novel connections: what hybrid mechanism, product, or scenario connects these three?",
        categories=cats,
        metadata={"words": ", ".join(words)},
    )


def _sample_paradox(bank: dict[str, Any], rng: random.Random, done: set[str] | None = None) -> ExercisePrompt:
    """Sample a paradoxical negative constraint (EXERCISE-03)."""
    pool = [p for p in (list(bank.get("curated", [])) + list(bank.get("twists", []))) if not done or p.strip() not in done]
    prompt_text = rng.choice(pool) if pool else "A mower that doesn't mow"
    return ExercisePrompt(
        exercise_type=ExerciseType.PARADOX.value,
        title="Paradoxical Constraint",
        prompt_text=prompt_text,
        sub_text="What does it do instead? What surprising new problem is this uniquely suited to solve?",
        categories=["constraint", "paradox"],
    )


def _sample_what_if(bank: dict[str, Any], rng: random.Random, done: set[str] | None = None) -> ExercisePrompt:
    """Sample an entity x system cross-domain mashup (EXERCISE-04)."""
    curated = [c for c in bank.get("curated", []) if not done or c.strip() not in done]
    entities = bank.get("entities", [])
    systems = bank.get("systems", [])
    if curated and (not entities or not systems or rng.random() < 0.5):
        prompt_text = rng.choice(curated)
    elif entities and systems:
        prompt_text = f"What if {rng.choice(entities)} ran {rng.choice(systems)}?"
        for _ in range(25):
            candidate = f"What if {rng.choice(entities)} ran {rng.choice(systems)}?"
            if not done or candidate not in done:
                prompt_text = candidate
                break
    else:
        prompt_text = "What if IKEA ran an elementary school?"

    return ExercisePrompt(
        exercise_type=ExerciseType.WHAT_IF.value,
        title="Cross-Domain 'What If?'",
        prompt_text=prompt_text,
        sub_text="If you transplanted their core culture, rules, and obsessions into this system, what would happen?",
        categories=["mashup", "transfer"],
    )


def _sample_biomimicry(bank: dict[str, Any], rng: random.Random, done: set[str] | None = None) -> ExercisePrompt:
    """Sample a biological mechanism challenge (EXERCISE-05)."""
    items = [it for it in bank.get("mechanisms", []) if not done or it.get("adaptation", "").strip() not in done]
    picked = rng.choice(items) if items else {"organism": "Beetle", "adaptation": "Fog harvesting via hydrophilic bumps", "challenge": "Apply fluid routing."}
    return ExercisePrompt(
        exercise_type=ExerciseType.BIOMIMICRY.value,
        title=f"Biomimicry: {picked.get('organism', 'Organism')}",
        prompt_text=picked.get("adaptation", ""),
        sub_text=picked.get("challenge", "Apply this mechanism to human design."),
        categories=["biomimicry", picked.get("organism", "").lower()],
    )


def _sample_assumption(bank: dict[str, Any], rng: random.Random, done: set[str] | None = None) -> ExercisePrompt:
    """Sample an orthogonal dogma inversion (EXERCISE-05)."""
    items = [
        it for it in bank.get("inversions", [])
        if not done or f"{it.get('standard_assumption', '')}\n➔ Inversion: {it.get('orthogonal_inversion', '')}".strip() not in done
    ]
    picked = rng.choice(items) if items else {"domain": "Dining", "standard_assumption": "Restaurants cook for you", "orthogonal_inversion": "Diners assemble meals", "spark_question": "Design concept."}
    p_text = f"{picked.get('standard_assumption', '')}\n➔ Inversion: {picked.get('orthogonal_inversion', '')}"
    return ExercisePrompt(
        exercise_type=ExerciseType.ASSUMPTION.value,
        title=f"Inversion: {picked.get('domain', 'Domain')}",
        prompt_text=p_text,
        sub_text=picked.get("spark_question", "How would you design around this reversal?"),
        categories=["inversion", picked.get("domain", "").lower()],
    )


def _sample_vault_hybrid(
    store: StoreProtocol | None,
    triads_bank: dict[str, Any],
    rng: random.Random,
    done: set[str] | None = None,
) -> ExercisePrompt:
    """Sample an active vault node and pair it with a wildcard seed (EXERCISE-06)."""
    if store is not None:
        nodes = [n for n in store.list_nodes() if n.state == "active"]
        if nodes:
            nouns = [w for cat in triads_bank.values() if isinstance(cat, list) for w in cat]
            node = rng.choice(nodes)
            wildcard = rng.choice(nouns) if nouns else "caterpillar"
            for _ in range(25):
                n_cand = rng.choice(nodes)
                w_cand = rng.choice(nouns) if nouns else "caterpillar"
                cand_text = f"'{n_cand.title}'  ✕  [{w_cand.upper()}]"
                if not done or cand_text not in done:
                    node, wildcard = n_cand, w_cand
                    break
            return ExercisePrompt(
                exercise_type=ExerciseType.VAULT_HYBRID.value,
                title=f"Vault Wildcard: {node.id}",
                prompt_text=f"'{node.title}'  ✕  [{wildcard.upper()}]",
                sub_text=f"Force-multiply your idea {node.id} with '{wildcard}'. How does it transform the core mechanism?",
                categories=["vault", node.type, node.domain],
                metadata={"node_id": node.id, "node_title": node.title, "wildcard": wildcard},
            )
    return _sample_triad(triads_bank, rng, done)


class ExerciseEngine:
    """Engine managing exercise generation from seed banks and tracking completed exercises."""

    def __init__(self, vault_dir: Path | None = None, store: StoreProtocol | None = None) -> None:
        self.vault_dir = vault_dir
        self.store = store

    def get_available_types(self) -> list[str]:
        return [ExerciseType.SURPRISE.value] + ExerciseType.all_types()

    def reload(self) -> None:
        pass

    def mark_done(self, prompt_text: str, title: str = "") -> None:
        """Mark an exercise prompt as done to exclude it from future sampling (EXERCISE-09)."""
        if self.vault_dir and prompt_text.strip():
            save_done_exercise(self.vault_dir, prompt_text.strip())

    def list_done(self) -> list[str]:
        return sorted(load_done_exercises(self.vault_dir))

    def reset_done(self) -> None:
        """Reset completed exercises pool back to empty (EXERCISE-09)."""
        if self.vault_dir:
            clear_done_exercises(self.vault_dir)

    def generate(self, exercise_type: str = "surprise", seed: int | None = None) -> ExercisePrompt:
        """Generate exercise prompt matching requested type, skipping completed ones."""
        rng = random.Random(seed)
        done = load_done_exercises(self.vault_dir)
        t = exercise_type.lower().strip()
        if t in ("surprise", "", "random"):
            choices = [
                ExerciseType.TRIAD.value, ExerciseType.PARADOX.value, ExerciseType.WHAT_IF.value,
                ExerciseType.BIOMIMICRY.value, ExerciseType.ASSUMPTION.value,
            ]
            if self.store is not None and any(n.state == "active" for n in self.store.list_nodes()):
                choices.append(ExerciseType.VAULT_HYBRID.value)
            t = rng.choice(choices)

        samplers = {
            ExerciseType.TRIAD.value: lambda: _sample_triad(load_seed_bank("triads", self.vault_dir), rng, done),
            ExerciseType.PARADOX.value: lambda: _sample_paradox(load_seed_bank("paradoxes", self.vault_dir), rng, done),
            ExerciseType.WHAT_IF.value: lambda: _sample_what_if(load_seed_bank("what_if", self.vault_dir), rng, done),
            ExerciseType.BIOMIMICRY.value: lambda: _sample_biomimicry(load_seed_bank("biomimicry", self.vault_dir), rng, done),
            ExerciseType.ASSUMPTION.value: lambda: _sample_assumption(load_seed_bank("assumptions", self.vault_dir), rng, done),
            ExerciseType.VAULT_HYBRID.value: lambda: _sample_vault_hybrid(self.store, load_seed_bank("triads", self.vault_dir), rng, done),
        }
        return samplers.get(t, samplers[ExerciseType.TRIAD.value])()
