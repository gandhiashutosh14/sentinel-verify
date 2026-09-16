"""
A simulated world of claims with hidden true states that change over time.

The simulator knows the truth; the scheduler only sees beliefs, feed evidence and the results
of the verifications it pays for. Everything is synthetic and seeded. A "world" file declares
the claim classes, how many claims of each, how often true states flip, and how much feed
evidence arrives per tick.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .belief import Belief, ClaimClass


@dataclass
class Claim:
    id: str
    cls: ClaimClass
    true_state: bool
    belief: Belief


@dataclass
class WorldSpec:
    name: str
    description: str
    classes: List[ClaimClass]
    counts: Dict[str, int]
    flip_rate: Dict[str, float]          # per-tick probability that a claim's true state flips
    feed_rate: float                     # expected pieces of feed evidence per tick
    feed_accuracy: float                 # P(feed evidence agrees with the true state)

    @classmethod
    def load(cls, path: str) -> "WorldSpec":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        classes = [ClaimClass(**c) for c in d["classes"]]
        return cls(name=d["name"], description=d.get("description", ""), classes=classes,
                   counts={k: int(v) for k, v in d["counts"].items()},
                   flip_rate={k: float(v) for k, v in d["flip_rate"].items()},
                   feed_rate=float(d["feed_rate"]), feed_accuracy=float(d["feed_accuracy"]))


class World:
    def __init__(self, spec: WorldSpec, seed: int):
        self.spec = spec
        self.rng = random.Random(seed)
        self.now = 0.0
        self.claims: List[Claim] = []
        by_name = {c.name: c for c in spec.classes}
        for name, n in spec.counts.items():
            k = by_name[name]
            prior = k.prior_alpha / (k.prior_alpha + k.prior_beta)
            for i in range(n):
                true = self.rng.random() < prior
                self.claims.append(Claim(f"{name}-{i:04d}", k, true, Belief.fresh(k, 0.0)))
        self.verifications = 0
        self.spend = 0.0

    # ------------------------------------------------------------------
    def tick(self) -> None:
        """Advance time: true states may flip; free feed evidence arrives."""
        self.now += 1.0
        for c in self.claims:
            if self.rng.random() < self.spec.flip_rate[c.cls.name]:
                c.true_state = not c.true_state
        n_feed = self._poisson(self.spec.feed_rate)
        for _ in range(n_feed):
            c = self.rng.choice(self.claims)
            agrees = self.rng.random() < self.spec.feed_accuracy
            c.belief.apply_feed(c.true_state if agrees else not c.true_state, self.now)

    def verify(self, claim: Claim) -> bool:
        """Pay the claim's verification cost and observe a noisy reading of its true state."""
        k = claim.cls
        if claim.true_state:
            says = self.rng.random() < k.verify_sensitivity
        else:
            says = not (self.rng.random() < k.verify_specificity)
        claim.belief.apply_verification(says, self.now)
        self.verifications += 1
        self.spend += k.verify_cost
        return says

    def _poisson(self, lam: float) -> int:
        # Knuth; fine for the small rates used here
        limit, k, p = pow(2.718281828459045, -lam), 0, 1.0
        while True:
            p *= self.rng.random()
            if p < limit:
                return k
            k += 1
