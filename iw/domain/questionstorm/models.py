"""Data models and constants for Questionstorming domain.

Layer 2 Domain module. Depends only on stdlib.
Governed by Vision §12 and QSTORM-01 through QSTORM-08.
"""

from dataclasses import dataclass
from enum import Enum


class QuestionForm(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class QuestionImportance(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


QUESTION_RELATIONS = (
    "broadens",
    "narrows",
    "presupposes",
    "reframes",
    "sibling",
    "questions",
)

BERGER_MOVES = {
    "why": "Why is it this way?",
    "why_must_it_be": "Why does it have to be this way?",
    "question_the_question": "What does this question assume?",
    "constraint_removal": "What if the constraint weren't there?",
    "inversion": "What if the opposite were true?",
    "how_might_we": "How might we...?",
    "open_closed": "Open ↔ Closed Transform",
    "dissenter": "What would a skeptic or dissenter ask?",
}


@dataclass(frozen=True)
class QuestionDraft:
    """Input payload for generating a question node."""
    text: str
    form: QuestionForm = QuestionForm.OPEN
    importance: QuestionImportance = QuestionImportance.MEDIUM
    move: str = "why"
    parent_question_id: str | None = None
    relation: str = "reframes"
