"""Domain models and enums for Creative Exercises.

Layer 2 Domain module. Depends only on stdlib and contracts.
Governed by EXERCISE-01 through EXERCISE-08.
"""

from enum import Enum


class ExerciseType(str, Enum):
    """Supported creative exercise types."""

    SURPRISE = "surprise"
    TRIAD = "triad"
    PARADOX = "paradox"
    WHAT_IF = "what_if"
    BIOMIMICRY = "biomimicry"
    ASSUMPTION = "assumption"
    VAULT_HYBRID = "vault_hybrid"

    @classmethod
    def all_types(cls) -> list[str]:
        """Return all distinct exercise type strings."""
        return [
            cls.TRIAD.value,
            cls.PARADOX.value,
            cls.WHAT_IF.value,
            cls.BIOMIMICRY.value,
            cls.ASSUMPTION.value,
            cls.VAULT_HYBRID.value,
        ]
