"""Association Proposal persistence and sampler telemetry calculation.

Layer 2 Domain module. Depends on iw.contracts, iw.domain.association.models, and stdlib.
Governed by Vision §13 and ASSOCREV-01 through ASSOCREV-06.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from iw.contracts.models import EventRecord
from iw.domain.association.models import AssociationProposal


def _proposal_to_dict(prop: AssociationProposal) -> dict[str, Any]:
    """Convert proposal object into JSON-serializable dictionary."""
    return {
        "id": prop.id, "pair_id": prop.pair_id, "node_a_id": prop.node_a_id,
        "node_b_id": prop.node_b_id, "node_a_title": prop.node_a_title, "node_b_title": prop.node_b_title,
        "sampler_strategy": prop.sampler_strategy, "distance_metric": prop.distance_metric,
        "proposal_title": prop.proposal_title, "target_domain": prop.target_domain,
        "abstract_mechanism": prop.abstract_mechanism, "transfer_proposal": prop.transfer_proposal,
        "strongest_objection": prop.strongest_objection, "judge_verdict": prop.judge_verdict,
        "confidence": prop.confidence, "created_at": prop.created_at.isoformat(),
        "reviewed": prop.reviewed, "review_decision": prop.review_decision,
        "derived_idea_id": prop.derived_idea_id,
    }


def read_all_proposals(vault_dir: Path) -> list[AssociationProposal]:
    """Read all proposals from vault associations.jsonl."""
    log_file = vault_dir / "associations.jsonl"
    if not log_file.is_file():
        return []

    proposals: list[AssociationProposal] = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            raw = json.loads(line)
            proposals.append(
                AssociationProposal(
                    id=raw["id"], pair_id=raw["pair_id"], node_a_id=raw["node_a_id"],
                    node_b_id=raw["node_b_id"], node_a_title=raw["node_a_title"],
                    node_b_title=raw["node_b_title"], sampler_strategy=raw["sampler_strategy"],
                    distance_metric=float(raw["distance_metric"]), proposal_title=raw["proposal_title"],
                    target_domain=raw["target_domain"], abstract_mechanism=raw["abstract_mechanism"],
                    transfer_proposal=raw["transfer_proposal"], strongest_objection=raw["strongest_objection"],
                    judge_verdict=raw["judge_verdict"], confidence=float(raw["confidence"]),
                    created_at=datetime.fromisoformat(raw["created_at"]),
                    reviewed=bool(raw.get("reviewed", False)), review_decision=raw.get("review_decision"),
                    derived_idea_id=raw.get("derived_idea_id"),
                )
            )
    return proposals


def append_proposal(vault_dir: Path, prop: AssociationProposal) -> None:
    """Append a newly synthesized proposal to associations.jsonl."""
    log_file = vault_dir / "associations.jsonl"
    data = _proposal_to_dict(prop)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")


def mark_proposal_reviewed(
    vault_dir: Path,
    proposal_id: str,
    decision: str,
    derived_idea_id: str | None = None,
) -> None:
    """Update review status in associations.jsonl."""
    proposals = read_all_proposals(vault_dir)
    updated: list[AssociationProposal] = []
    marked = False
    for p in proposals:
        if p.id == proposal_id and not marked:
            marked = True
            updated.append(
                AssociationProposal(
                    id=p.id, pair_id=p.pair_id, node_a_id=p.node_a_id, node_b_id=p.node_b_id,
                    node_a_title=p.node_a_title, node_b_title=p.node_b_title,
                    sampler_strategy=p.sampler_strategy, distance_metric=p.distance_metric,
                    proposal_title=p.proposal_title, target_domain=p.target_domain,
                    abstract_mechanism=p.abstract_mechanism, transfer_proposal=p.transfer_proposal,
                    strongest_objection=p.strongest_objection, judge_verdict=p.judge_verdict,
                    confidence=p.confidence, created_at=p.created_at, reviewed=True,
                    review_decision=decision, derived_idea_id=derived_idea_id,
                )
            )
        else:
            updated.append(p)

    log_file = vault_dir / "associations.jsonl"
    with open(log_file, "w", encoding="utf-8") as f:
        for p in updated:
            f.write(json.dumps(_proposal_to_dict(p)) + "\n")


def compute_sampler_telemetry(events: list[EventRecord]) -> dict[str, dict[str, Any]]:
    """Compute yield statistics per sampler strategy from event stream."""
    stats: dict[str, dict[str, Any]] = {
        "random": {"sampled": 0, "kept": 0, "discarded": 0, "yield_pct": 0.0},
        "anti_similar": {"sampled": 0, "kept": 0, "discarded": 0, "yield_pct": 0.0},
        "mid_band": {"sampled": 0, "kept": 0, "discarded": 0, "yield_pct": 0.0},
    }
    for e in events:
        if e.kind == "association_reviewed":
            strategy = e.payload.get("strategy", "random")
            decision = e.payload.get("decision", "discard")
            if strategy not in stats:
                stats[strategy] = {"sampled": 0, "kept": 0, "discarded": 0, "yield_pct": 0.0}
            stats[strategy]["sampled"] += 1
            if decision == "keep":
                stats[strategy]["kept"] += 1
            else:
                stats[strategy]["discarded"] += 1

    for s_name, data in stats.items():
        if data["sampled"] > 0:
            data["yield_pct"] = round((data["kept"] / data["sampled"]) * 100, 1)

    return stats
