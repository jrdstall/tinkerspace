"""Concept Maturity Level (CML), Assessment Scoring, and Laggard Mapping.

Layer 2 Domain module. Depends only on iw.contracts and stdlib.
Governed by InnovatorsWorkspaceVision §11 and ASSESS-01 through ASSESS-08.
"""

from typing import Any
from iw.contracts.models import Node

SCORE_KEYS = ("novel", "works", "reach", "story")
VALID_WORTH_RATINGS = {"high", "medium", "low"}
VALID_VERDICTS = {"pursue", "park", "let_go"}

LAGGARD_ACTIVITIES = {
    "novel": "prior-art-survey@1",
    "works": "feasibility-spike@1",
    "reach": "parts-and-skills-survey@1",
    "story": "pitch-draft@1",
}


def compute_cml(scores: dict[str, int] | None) -> int:
    """Compute CML from 4 maturity scores (lowest of the 4 scores).

    ASSESS-01, ASSESS-02, ASSESS-03:
    Defaults to 1 if unassessed or scores are empty.
    """
    if not scores:
        return 1
    numeric_scores = [
        int(scores[k]) for k in SCORE_KEYS if k in scores and isinstance(scores[k], (int, float))
    ]
    if not numeric_scores:
        return 1
    return max(1, min(5, min(numeric_scores)))


def identify_laggards(scores: dict[str, int] | None) -> list[str]:
    """Identify the maturity score keys holding back the CML.

    ASSESS-07: Returns the keys whose score equals the minimum score.
    """
    if not scores:
        return []
    valid_scores = {
        k: int(scores[k]) for k in SCORE_KEYS if k in scores and isinstance(scores[k], (int, float))
    }
    if not valid_scores:
        return []
    min_val = min(valid_scores.values())
    return [k for k in SCORE_KEYS if k in valid_scores and valid_scores[k] == min_val]


def recommend_activity_for_laggard(laggard_key: str) -> str:
    """Map a laggard score dimension to its recommended advancement activity.

    ASSESS-07: Returns the activity template ID that moves the laggard score.
    """
    return LAGGARD_ACTIVITIES.get(laggard_key.lower(), "screening-assessment@1")


def apply_assessment_to_node(
    node: Node,
    scores: dict[str, int] | None = None,
    worth_to_me: str | None = None,
    worth_to_others: str | None = None,
    verdict: str | None = None,
    reason: str | None = None,
    concept_graphic: str | None = None,
) -> Node:
    """Apply assessment scores, worth ratings, and verdict to a Node.

    ASSESS-01..ASSESS-08: Materializes frontmatter attributes and derived CML.
    """
    if scores is not None:
        validated_scores: dict[str, int] = {}
        for k in SCORE_KEYS:
            if k in scores:
                validated_scores[k] = max(1, min(5, int(scores[k])))
        node.attrs["scores"] = validated_scores
        node.attrs["cml"] = compute_cml(validated_scores)
    else:
        scores_dict = node.attrs.get("scores")
        node.attrs["cml"] = compute_cml(scores_dict if isinstance(scores_dict, dict) else None)

    if worth_to_me is not None and worth_to_me.lower() in VALID_WORTH_RATINGS:
        node.attrs["worth_to_me"] = worth_to_me.lower()

    if worth_to_others is not None and worth_to_others.lower() in VALID_WORTH_RATINGS:
        node.attrs["worth_to_others"] = worth_to_others.lower()

    if verdict is not None and verdict.lower() in VALID_VERDICTS:
        node.attrs["screening_verdict"] = verdict.lower()
        if reason is not None:
            node.attrs["screening_reason"] = reason

    if concept_graphic is not None:
        node.attrs["concept_graphic"] = concept_graphic

    return node
