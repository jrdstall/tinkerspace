"""Combinatorial exercise prompt generator.

Layer 2 Domain module. Pure business logic adhering to EXERCISE-01..06.
"""

from pathlib import Path
import random
from typing import Any

from iw.contracts.exercises import ExercisePrompt
from iw.contracts.store import StoreProtocol
from iw.domain.exercises.loader import load_seed_bank
from iw.domain.exercises.models import ExerciseType


def _sample_triad(bank: dict[str, Any], rng: random.Random) -> ExercisePrompt:
    """Sample 3 concrete nouns across mutually distinct categories (EXERCISE-02)."""
    available_cats = [k for k, v in bank.items() if isinstance(v, list) and v]
    if len(available_cats) < 3:
        words = ["printer", "house", "caterpillar"]
        cats = ["mechanical_tools", "domestic_apparel", "organic"]
    else:
        chosen_cats = rng.sample(available_cats, 3)
        words = [rng.choice(bank[c]) for c in chosen_cats]
        cats = chosen_cats

    prompt_text = " • ".join(words)
    return ExercisePrompt(
        exercise_type=ExerciseType.TRIAD.value,
        title="3-Word Triad",
        prompt_text=prompt_text,
        sub_text="Riff on novel connections: what hybrid mechanism, product, or scenario connects these three?",
        categories=cats,
        metadata={"words": ", ".join(words)},
    )


def _sample_paradox(bank: dict[str, Any], rng: random.Random) -> ExercisePrompt:
    """Sample a paradoxical negative constraint (EXERCISE-03)."""
    curated = bank.get("curated", [])
    twists = bank.get("twists", [])
    pool = list(curated) + list(twists)

    if pool:
        prompt_text = rng.choice(pool)
    else:
        prompt_text = "A mower that doesn't mow"

    return ExercisePrompt(
        exercise_type=ExerciseType.PARADOX.value,
        title="Paradoxical Constraint",
        prompt_text=prompt_text,
        sub_text="What does it do instead? What surprising new problem is this uniquely suited to solve?",
        categories=["constraint", "paradox"],
    )


def _sample_what_if(bank: dict[str, Any], rng: random.Random) -> ExercisePrompt:
    """Sample an entity x system cross-domain mashup (EXERCISE-04)."""
    curated = bank.get("curated", [])
    entities = bank.get("entities", [])
    systems = bank.get("systems", [])

    if curated and (not entities or not systems or rng.random() < 0.5):
        prompt_text = rng.choice(curated)
    elif entities and systems:
        prompt_text = f"What if {rng.choice(entities)} ran {rng.choice(systems)}?"
    else:
        prompt_text = "What if IKEA ran an elementary school?"

    return ExercisePrompt(
        exercise_type=ExerciseType.WHAT_IF.value,
        title="Cross-Domain 'What If?'",
        prompt_text=prompt_text,
        sub_text="If you transplanted their core culture, rules, and obsessions into this system, what would happen?",
        categories=["mashup", "transfer"],
    )


def _sample_biomimicry(bank: dict[str, Any], rng: random.Random) -> ExercisePrompt:
    """Sample a biological mechanism challenge (EXERCISE-05)."""
    items = bank.get("mechanisms", [])
    if not items:
        return ExercisePrompt(
            exercise_type=ExerciseType.BIOMIMICRY.value,
            title="Biomimicry Spark",
            prompt_text="Namib Desert Beetle: Fog harvesting via hydrophilic bumps & hydrophobic gutters",
            sub_text="How could you apply passive fluid gradient routing in products?",
            categories=["biology", "mechanisms"],
        )
    picked = rng.choice(items)
    return ExercisePrompt(
        exercise_type=ExerciseType.BIOMIMICRY.value,
        title=f"Biomimicry: {picked.get('organism', 'Organism')}",
        prompt_text=picked.get("adaptation", ""),
        sub_text=picked.get("challenge", "Apply this mechanism to human design."),
        categories=["biomimicry", picked.get("organism", "").lower()],
    )


def _sample_assumption(bank: dict[str, Any], rng: random.Random) -> ExercisePrompt:
    """Sample an orthogonal dogma inversion (EXERCISE-05)."""
    items = bank.get("inversions", [])
    if not items:
        return ExercisePrompt(
            exercise_type=ExerciseType.ASSUMPTION.value,
            title="Assumption Inversion",
            prompt_text="Assumption: Restaurants cook for you ➔ Inversion: Diners assemble meals with chef-timed heat",
            sub_text="Design a concept around the inverted dogma.",
            categories=["inversion"],
        )
    picked = rng.choice(items)
    p_text = f"{picked.get('standard_assumption', '')}\n➔ Inversion: {picked.get('orthogonal_inversion', '')}"
    return ExercisePrompt(
        exercise_type=ExerciseType.ASSUMPTION.value,
        title=f"Inversion: {picked.get('domain', 'Domain')}",
        prompt_text=p_text,
        sub_text=picked.get("spark_question", "How would you design around this reversal?"),
        categories=["assumption", picked.get("domain", "").lower()],
    )


def _sample_vault_hybrid(
    store: StoreProtocol | None,
    triads_bank: dict[str, Any],
    rng: random.Random,
) -> ExercisePrompt:
    """Sample an active vault node and pair it with a wildcard seed (EXERCISE-06)."""
    if store is not None:
        nodes = [n for n in store.list_nodes() if n.state == "active"]
        if nodes:
            node = rng.choice(nodes)
            nouns = [w for cat in triads_bank.values() if isinstance(cat, list) for w in cat]
            wildcard = rng.choice(nouns) if nouns else "caterpillar"
            return ExercisePrompt(
                exercise_type=ExerciseType.VAULT_HYBRID.value,
                title=f"Vault Wildcard: {node.id}",
                prompt_text=f"'{node.title}'  ✕  [{wildcard.upper()}]",
                sub_text=f"Force-multiply your idea {node.id} with '{wildcard}'. How does it transform the core mechanism?",
                categories=["vault", node.type, node.domain],
                metadata={"node_id": node.id, "node_title": node.title, "wildcard": wildcard},
            )
    return _sample_triad(triads_bank, rng)


class ExerciseEngine:
    """Engine managing exercise generation from seed banks."""

    def __init__(
        self,
        vault_dir: Path | None = None,
        store: StoreProtocol | None = None,
    ) -> None:
        self.vault_dir = vault_dir
        self.store = store

    def get_available_types(self) -> list[str]:
        """Return all supported exercise types."""
        return [ExerciseType.SURPRISE.value] + ExerciseType.all_types()

    def reload(self) -> None:
        """Clear cache if any."""
        pass

    def generate(self, exercise_type: str = "surprise", seed: int | None = None) -> ExercisePrompt:
        """Generate exercise prompt matching requested type."""
        rng = random.Random(seed)
        t = exercise_type.lower().strip()
        if t in ("surprise", "", "random"):
            choices = [
                ExerciseType.TRIAD.value, ExerciseType.PARADOX.value, ExerciseType.WHAT_IF.value,
                ExerciseType.BIOMIMICRY.value, ExerciseType.ASSUMPTION.value,
            ]
            if self.store is not None and any(n.state == "active" for n in self.store.list_nodes()):
                choices.append(ExerciseType.VAULT_HYBRID.value)
            t = rng.choice(choices)

        if t == ExerciseType.TRIAD.value:
            return _sample_triad(load_seed_bank("triads", self.vault_dir), rng)
        if t == ExerciseType.PARADOX.value:
            return _sample_paradox(load_seed_bank("paradoxes", self.vault_dir), rng)
        if t == ExerciseType.WHAT_IF.value:
            return _sample_what_if(load_seed_bank("what_if", self.vault_dir), rng)
        if t == ExerciseType.BIOMIMICRY.value:
            return _sample_biomimicry(load_seed_bank("biomimicry", self.vault_dir), rng)
        if t == ExerciseType.ASSUMPTION.value:
            return _sample_assumption(load_seed_bank("assumptions", self.vault_dir), rng)
        if t == ExerciseType.VAULT_HYBRID.value:
            return _sample_vault_hybrid(self.store, load_seed_bank("triads", self.vault_dir), rng)
        return _sample_triad(load_seed_bank("triads", self.vault_dir), rng)
