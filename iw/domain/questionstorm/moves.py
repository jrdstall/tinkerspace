"""Berger Questioning Moves generators and transformers.

Layer 2 Domain module. Depends only on iw.domain.questionstorm.models and stdlib.
Governed by Vision §12 and QSTORM-06, QSTORM-07.
"""

from iw.domain.questionstorm.models import BERGER_MOVES, QuestionForm


def get_berger_stems() -> dict[str, str]:
    """Return dictionary of Berger questioning moves and prompt descriptions."""
    return dict(BERGER_MOVES)


def apply_berger_move(move_key: str, subject_title: str) -> str:
    """Generate a starter question stem based on the selected Berger move."""
    clean_title = subject_title.rstrip("?").strip()
    key = move_key.lower().replace("-", "_")

    if key == "why":
        return f"Why is {clean_title} currently done this way?"
    if key == "why_must_it_be":
        return f"Why does {clean_title} have to work like this?"
    if key == "question_the_question":
        return f"What hidden assumptions underlie {clean_title}?"
    if key == "constraint_removal":
        return f"What if the primary constraint on {clean_title} were removed?"
    if key == "inversion":
        return f"What if the complete opposite were true for {clean_title}?"
    if key == "how_might_we":
        return f"How might we rethink {clean_title} from first principles?"
    if key == "dissenter":
        return f"What fatal flaw would a harsh critic find in {clean_title}?"
    return f"What if {clean_title}?"


def invert_question_form(current_form: str) -> str:
    """Invert form between open and closed."""
    if str(current_form).lower() == QuestionForm.OPEN.value:
        return QuestionForm.CLOSED.value
    return QuestionForm.OPEN.value


def suggest_relation_for_transform(from_form: str, to_form: str) -> str:
    """Suggest relationship type for transformed question."""
    if from_form == QuestionForm.OPEN.value and to_form == QuestionForm.CLOSED.value:
        return "narrows"
    return "reframes"
