"""Association Engine domain package for Tinkerspace.

Layer 2 Domain module. Governed by Vision §13 and SAMPLER, ASSOC, ASSOCREV specifications.
"""

from iw.domain.association.corpus import distill_corpus_pool
from iw.domain.association.judge import (
    build_association_prompt,
    parse_deliverable_to_proposal,
)
from iw.domain.association.models import (
    AssociationProposal,
    JudgeVerdict,
)
from iw.domain.association.pipeline import AssociationPipeline
from iw.domain.association.samplers import (
    AntiSimilarSampler,
    MidBandSampler,
    RandomSampler,
    get_sampler,
)

__all__ = [
    "distill_corpus_pool",
    "RandomSampler",
    "AntiSimilarSampler",
    "MidBandSampler",
    "get_sampler",
    "build_association_prompt",
    "parse_deliverable_to_proposal",
    "AssociationProposal",
    "JudgeVerdict",
    "AssociationPipeline",
]
