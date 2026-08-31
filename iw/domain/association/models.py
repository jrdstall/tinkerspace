"""Domain data structures for Association Proposals and Judge Verdicts.

Layer 2 Domain module. Depends only on stdlib.
Governed by Vision §13 and ASSOC-01 through ASSOC-08.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class JudgeVerdict(str, Enum):
    KEEP = "keep"
    DISCARD = "discard"


@dataclass(frozen=True)
class AssociationProposal:
    """Represents the complete generated artifact of an association run."""
    id: str
    pair_id: str
    node_a_id: str
    node_b_id: str
    node_a_title: str
    node_b_title: str
    sampler_strategy: str
    distance_metric: float
    proposal_title: str
    target_domain: str
    abstract_mechanism: str
    transfer_proposal: str
    strongest_objection: str
    judge_verdict: str
    confidence: float
    created_at: datetime
    reviewed: bool = False
    review_decision: str | None = None
    derived_idea_id: str | None = None
