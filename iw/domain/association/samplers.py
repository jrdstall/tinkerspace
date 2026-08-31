"""Competing Sampler algorithms for Association Pairing.

Layer 2 Domain module. Depends on iw.contracts and stdlib.
Governed by Vision §13 and SAMPLER-04, SAMPLER-05, SAMPLER-06.
"""

import itertools
import random
from typing import Callable

from iw.contracts.association import (
    AssociationSamplerProtocol,
    DistilledRecord,
    PairCandidate,
)


def calculate_structural_distance(a: DistilledRecord, b: DistilledRecord) -> float:
    """Calculate structural and semantic distance between two records (0.0 to 1.0)."""
    if a.id == b.id:
        return 0.0

    domain_dist = 0.5 if a.domain.lower() != b.domain.lower() else 0.0
    type_dist = 0.3 if a.type.lower() != b.type.lower() else 0.0

    tags_a, tags_b = set(t.lower() for t in a.tags), set(t.lower() for t in b.tags)
    tag_union = tags_a | tags_b
    if not tag_union:
        tag_dist = 0.2
    else:
        tag_dist = 0.2 * (1.0 - (len(tags_a & tags_b) / len(tag_union)))

    return min(1.0, domain_dist + type_dist + tag_dist)


class RandomSampler(AssociationSamplerProtocol):
    """Control arm sampler choosing pairs uniformly at random (SAMPLER-04)."""

    def sample_pairs(
        self,
        pool: list[DistilledRecord],
        count: int = 5,
        seed: int | None = None,
    ) -> list[PairCandidate]:
        """Sample pairs randomly across the pool."""
        if len(pool) < 2:
            return []

        rng = random.Random(seed)
        all_possible = list(itertools.combinations(pool, 2))
        rng.shuffle(all_possible)
        selected = all_possible[:count]

        candidates: list[PairCandidate] = []
        for i, (a, b) in enumerate(selected, start=1):
            dist = calculate_structural_distance(a, b)
            candidates.append(
                PairCandidate(
                    pair_id=f"PAIR-RND-{i:02d}",
                    node_a=a,
                    node_b=b,
                    strategy="random",
                    distance_metric=round(dist, 2),
                )
            )
        return candidates


class AntiSimilarSampler(AssociationSamplerProtocol):
    """Strategy maximizing domain and structural distance (SAMPLER-05)."""

    def sample_pairs(
        self,
        pool: list[DistilledRecord],
        count: int = 5,
        seed: int | None = None,
    ) -> list[PairCandidate]:
        """Sample pairs with highest structural distance."""
        if len(pool) < 2:
            return []

        rng = random.Random(seed)
        all_possible = list(itertools.combinations(pool, 2))
        rng.shuffle(all_possible)

        scored = [(calculate_structural_distance(a, b), a, b) for a, b in all_possible]
        scored.sort(key=lambda item: item[0], reverse=True)
        selected = scored[:count]

        candidates: list[PairCandidate] = []
        for i, (dist, a, b) in enumerate(selected, start=1):
            candidates.append(
                PairCandidate(
                    pair_id=f"PAIR-ANT-{i:02d}",
                    node_a=a,
                    node_b=b,
                    strategy="anti_similar",
                    distance_metric=round(dist, 2),
                )
            )
        return candidates


class MidBandSampler(AssociationSamplerProtocol):
    """Strategy selecting pairs with moderate structural overlap (SAMPLER-06)."""

    def sample_pairs(
        self,
        pool: list[DistilledRecord],
        count: int = 5,
        seed: int | None = None,
    ) -> list[PairCandidate]:
        """Sample pairs with distance in the middle band (0.3 to 0.8)."""
        if len(pool) < 2:
            return []

        rng = random.Random(seed)
        all_possible = list(itertools.combinations(pool, 2))
        rng.shuffle(all_possible)

        scored = [(calculate_structural_distance(a, b), a, b) for a, b in all_possible]
        mid_band = [item for item in scored if 0.25 <= item[0] <= 0.85]
        if not mid_band:
            mid_band = scored

        selected = mid_band[:count]
        candidates: list[PairCandidate] = []
        for i, (dist, a, b) in enumerate(selected, start=1):
            candidates.append(
                PairCandidate(
                    pair_id=f"PAIR-MID-{i:02d}",
                    node_a=a,
                    node_b=b,
                    strategy="mid_band",
                    distance_metric=round(dist, 2),
                )
            )
        return candidates


def get_sampler(strategy_name: str) -> AssociationSamplerProtocol:
    """Resolve sampler strategy by name."""
    clean = strategy_name.lower().replace("-", "_")
    if clean == "anti_similar":
        return AntiSimilarSampler()
    if clean == "mid_band":
        return MidBandSampler()
    return RandomSampler()
