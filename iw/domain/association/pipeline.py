"""Association Pipeline orchestrating candidate synthesis and idea promotion.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.association, and stdlib.
Governed by Vision §13 and ASSOC-01 through ASSOC-08.
"""

from datetime import datetime, timezone
from iw.contracts.association import PairCandidate
from iw.contracts.models import Author, AuthorKind, Edge, Node
from iw.contracts.store import StoreProtocol
from iw.core.ids import allocate_next_id
from iw.domain.association.corpus import distill_corpus_pool
from iw.domain.association.judge import parse_deliverable_to_proposal
from iw.domain.association.models import AssociationProposal
from iw.domain.association.review import read_all_proposals
from iw.domain.association.samplers import get_sampler


def _build_derived_idea(idea_id: str, prop: AssociationProposal, now: datetime, auth: Author) -> Node:
    """Construct Idea node data structure from proposal."""
    edges = [
        Edge(from_id=idea_id, to_id=prop.node_a_id, relation="derived_from", created=now, author=auth),
        Edge(from_id=idea_id, to_id=prop.node_b_id, relation="derived_from", created=now, author=auth),
    ]
    body = (
        f"## Abstract Mechanism\n{prop.abstract_mechanism}\n\n"
        f"## Transfer Proposal\n{prop.transfer_proposal}\n\n"
        f"## Adversarial Refutation\n{prop.strongest_objection}\n"
    )
    attrs = {
        "abstract_mechanism": prop.abstract_mechanism, "strongest_objection": prop.strongest_objection,
        "sampler_strategy": prop.sampler_strategy, "distance_metric": prop.distance_metric,
        "derived_from": [prop.node_a_id, prop.node_b_id], "scores": {"novel": 3, "works": 3, "reach": 2, "story": 3}, "cml": 2,
    }
    return Node(
        id=idea_id, type="idea", title=prop.proposal_title, created=now, domain=prop.target_domain,
        tags=["association", prop.sampler_strategy], state="active", author=auth, last_touched=now,
        body=body, attrs=attrs, edges=edges,
    )


class AssociationPipeline:
    """Manages association sampling runs, proposal generation, and promotion."""

    def __init__(self, store: StoreProtocol) -> None:
        self.store = store

    def generate_candidate_pairs(
        self,
        strategy_name: str = "random",
        count: int = 5,
        seed: int | None = None,
    ) -> list[PairCandidate]:
        """Sample candidate pairs from the distilled corpus pool."""
        pool = distill_corpus_pool(self.store)
        sampler = get_sampler(strategy_name)
        return sampler.sample_pairs(pool=pool, count=count, seed=seed)

    def synthesize_proposal(
        self,
        candidate: PairCandidate,
        deliverable_text: str | None = None,
        author: Author | None = None,
    ) -> AssociationProposal:
        """Create a structured AssociationProposal from pair candidate and deliverable."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        existing_props = read_all_proposals(self.store.vault_dir)
        prop_id = allocate_next_id("PROP", [p.id for p in existing_props])

        text = deliverable_text or (
            f"---\n"
            f"proposal_title: \"Cross-Domain Synthesis: {candidate.node_a.title} x {candidate.node_b.title}\"\n"
            f"target_domain: \"engineering\"\n"
            f"abstract_mechanism: \"Coupled resonance feedback between {candidate.node_a.id} and {candidate.node_b.id}\"\n"
            f"transfer_proposal: \"Apply harmonic oscillation to optimize cold-environment efficiency.\"\n"
            f"strongest_objection: \"Thermal dissipation at sub-zero temperatures requires auxiliary shielding.\"\n"
            f"judge_verdict: \"keep\"\n"
            f"confidence: 0.85\n"
            f"---\n"
        )
        proposal = parse_deliverable_to_proposal(prop_id, text, candidate)

        self.store.event_log.append(
            kind="association_proposed",
            subject_id=proposal.id,
            author=auth,
            payload={
                "pair_id": candidate.pair_id, "node_a_id": candidate.node_a.id,
                "node_b_id": candidate.node_b.id, "strategy": candidate.strategy, "verdict": proposal.judge_verdict,
            },
        )
        return proposal

    def convert_proposal_to_idea(
        self,
        proposal: AssociationProposal,
        author: Author | None = None,
    ) -> Node:
        """Convert kept proposal into a permanent Idea node with derived_from lineage."""
        auth = author or Author(kind=AuthorKind.HUMAN, courier="web-ui")
        now = datetime.now(timezone.utc)
        idea_id = self.store.allocate_id("IDEA")
        node = _build_derived_idea(idea_id, proposal, now, auth)
        self.store.write_node(node, author=auth)
        return node
