"""Adversarial Judge and Association Deliverable parsing utilities.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.association.models, and stdlib.
Governed by Vision §13 and ASSOC-04, ASSOC-06, ASSOC-07.
"""

from datetime import datetime, timezone
import re
from typing import Any
import uuid
import yaml

from iw.contracts.association import PairCandidate
from iw.domain.association.models import AssociationProposal


def build_association_prompt(candidate: PairCandidate) -> str:
    """Format pair candidate into structured two-stage creativity and judge prompt."""
    return (
        f"PAIR ANALYSIS CANDIDATE ({candidate.strategy} | dist={candidate.distance_metric})\n\n"
        f"PARENT A: [{candidate.node_a.id}] {candidate.node_a.title} ({candidate.node_a.domain})\n"
        f"Excerpt: {candidate.node_a.excerpt}\n\n"
        f"PARENT B: [{candidate.node_b.id}] {candidate.node_b.title} ({candidate.node_b.domain})\n"
        f"Excerpt: {candidate.node_b.excerpt}\n\n"
        "Execute Stage 1 Abstraction, Stage 2 Third-Domain Transfer, and Adversarial Judge Refutation."
    )


def _extract_yaml_or_text(text: str) -> dict[str, Any]:
    """Extract frontmatter or key-value fields from deliverable text."""
    if "---" in text:
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                parsed = yaml.safe_load(parts[1])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
    return {}


def parse_deliverable_to_proposal(
    proposal_id: str,
    deliverable_text: str,
    candidate: PairCandidate,
) -> AssociationProposal:
    """Parse raw agent deliverable markdown into structured AssociationProposal."""
    meta = _extract_yaml_or_text(deliverable_text)

    title = meta.get("proposal_title") or f"Synthesized Idea from {candidate.node_a.id} & {candidate.node_b.id}"
    domain = meta.get("target_domain") or "cross-domain"
    mechanism = meta.get("abstract_mechanism") or "Abstract functional coupling mechanism."
    transfer = meta.get("transfer_proposal") or deliverable_text.strip()
    objection = meta.get("strongest_objection") or "Unverified manufacturing scalability or cost barrier."
    verdict = str(meta.get("judge_verdict") or "keep").lower().strip()
    if verdict not in ("keep", "discard"):
        verdict = "keep"

    confidence = float(meta.get("confidence", 0.75))

    return AssociationProposal(
        id=proposal_id,
        pair_id=candidate.pair_id,
        node_a_id=candidate.node_a.id,
        node_b_id=candidate.node_b.id,
        node_a_title=candidate.node_a.title,
        node_b_title=candidate.node_b.title,
        sampler_strategy=candidate.strategy,
        distance_metric=candidate.distance_metric,
        proposal_title=title,
        target_domain=domain,
        abstract_mechanism=mechanism,
        transfer_proposal=transfer,
        strongest_objection=objection,
        judge_verdict=verdict,
        confidence=confidence,
        created_at=datetime.now(timezone.utc),
        reviewed=False,
    )
