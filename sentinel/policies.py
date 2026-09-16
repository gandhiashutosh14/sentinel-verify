"""
Scheduling policies. Each takes the claims and the current tick and returns the claims to
verify this tick, spending at most `budget` cost units. All policies see the same beliefs;
none sees the true state.
"""
from __future__ import annotations

import random
from typing import Callable, List

from .belief import decision_voi, entropy_voi
from .world import Claim

Policy = Callable[[List[Claim], float, float, random.Random], List[Claim]]


def _take_within_budget(ranked: List[Claim], budget: float) -> List[Claim]:
    chosen, spent = [], 0.0
    for c in ranked:
        if spent + c.cls.verify_cost <= budget:
            chosen.append(c)
            spent += c.cls.verify_cost
    return chosen


def decision_voi_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    """Greedy by expected decision-loss reduction per unit cost; skips claims with zero value."""
    scored = [(decision_voi(c.belief, now) / c.cls.verify_cost, c) for c in claims]
    ranked = [c for v, c in sorted(scored, key=lambda t: -t[0]) if v > 0]
    return _take_within_budget(ranked, budget)


def entropy_voi_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    """Greedy by expected entropy reduction per unit cost: the uncertainty-of-information baseline."""
    scored = [(entropy_voi(c.belief, now) / c.cls.verify_cost, c) for c in claims]
    ranked = [c for v, c in sorted(scored, key=lambda t: -t[0]) if v > 0]
    return _take_within_budget(ranked, budget)


def score_sorted_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    """Highest current p(true) first: the EPSS/CVSS-sorted baseline."""
    ranked = sorted(claims, key=lambda c: -c.belief.p_true(now))
    return _take_within_budget(ranked, budget)


def oldest_first_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    """Longest since last verification first: the freshness-crawl baseline."""
    ranked = sorted(claims, key=lambda c: c.belief.verified_at)
    return _take_within_budget(ranked, budget)


def random_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    ranked = list(claims)
    rng.shuffle(ranked)
    return _take_within_budget(ranked, budget)


def never_policy(claims: List[Claim], now: float, budget: float, rng: random.Random) -> List[Claim]:
    """Verify nothing: decisions rest on priors and feed evidence alone."""
    return []


POLICIES = {
    "decision-voi": decision_voi_policy,
    "entropy-voi": entropy_voi_policy,
    "score-sorted": score_sorted_policy,
    "oldest-first": oldest_first_policy,
    "random": random_policy,
    "never": never_policy,
}
