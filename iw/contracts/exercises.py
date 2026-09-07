"""Creative Exercise contracts and protocols.

Layer 1 Contracts module. Pure types and Protocols only.
Governed by EXERCISE-01 through EXERCISE-08.
"""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ExercisePrompt:
    """A generated creative exercise prompt for ideation."""

    exercise_type: str
    title: str
    prompt_text: str
    sub_text: str = ""
    categories: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class ExerciseEngineProtocol(Protocol):
    """Protocol for generating creative exercise prompts and managing seed banks."""

    def generate(self, exercise_type: str, seed: int | None = None) -> ExercisePrompt:
        """Generate a creative exercise prompt."""
        ...

    def get_available_types(self) -> list[str]:
        """Return list of supported exercise type identifiers."""
        ...

    def reload(self) -> None:
        """Reload seed banks from disk."""
        ...
