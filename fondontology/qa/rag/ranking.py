"""Model-independent ranking stages with deterministic identities and tie breaking."""

from __future__ import annotations

import math


def reciprocal_rank_fusion(channels: dict[str, list[str]], *, limit: int,
                           rank_constant: int = 60) -> list[tuple[str, float]]:
    if type(limit) is not int or limit < 1 or type(rank_constant) is not int or rank_constant < 1:
        raise ValueError("RRF budgets must be positive integers")
    scores = {}
    for identifiers in channels.values():
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("RRF channel contains duplicate candidates")
        for rank, identifier in enumerate(identifiers, 1):
            scores[identifier] = scores.get(identifier, 0.0) + 1.0 / (rank_constant + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]


def validate_rerank_scores(scores, candidate_count: int) -> list[tuple[int, float]]:
    if (not isinstance(scores, list) or len(scores) != candidate_count
            or any(not isinstance(item, (list, tuple)) or len(item) != 2
                   or type(item[0]) is not int or item[0] < 0 or item[0] >= candidate_count
                   or type(item[1]) not in (int, float) or not math.isfinite(item[1])
                   for item in scores)
            or len({item[0] for item in scores}) != candidate_count):
        raise ValueError("Reranker must score every candidate exactly once with finite scores")
    return sorted(scores, key=lambda item: (-item[1], item[0]))
