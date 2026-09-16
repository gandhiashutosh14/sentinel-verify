"""
Beliefs, decay, decisions and the value of a verification.

A claim is a binary proposition (this host is exposed; this plot is compliant) with a Beta
belief over it. Two things distinguish this model from a plain Beta-Bernoulli update:

1. Pseudo-counts decay toward the class prior with time, so a confident belief from long ago
   becomes an uncertain one. Feed evidence updates the counts but does not count as a
   verification; only a verification restarts the "last verified" clock that staleness policies
   and reports look at. (Decay itself is exponential, so it can be re-anchored at any evidence
   event without changing the total decay since the last verification.)
2. Actions are chosen by expected loss under an asymmetric loss table, and the value of a
   verification is measured against that decision, not against entropy: a claim whose decision
   would not change whatever the verification returned has zero value, however uncertain it is.

A verification is a noisy test with known sensitivity and specificity. Its posterior is the
Bayesian one under that noise model, folded back into Beta pseudo-counts with one more unit of
total weight, so the scheduler's valuation and the belief store agree.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

ACTIONS = ("act", "accept")          # act = remediate / visit / flag; accept = leave it


@dataclass(frozen=True)
class ClaimClass:
    """Prior and dynamics shared by claims of one kind."""
    name: str
    prior_alpha: float               # class prior pseudo-counts (state = 1)
    prior_beta: float
    decay_rate: float                # per tick; belief half-life = ln 2 / decay_rate
    loss_act_when_false: float       # cost of acting on a claim that is actually false
    loss_accept_when_true: float     # cost of accepting a claim that is actually true
    verify_cost: float
    verify_sensitivity: float = 0.95 # P(verification says true | true)
    verify_specificity: float = 0.95 # P(verification says false | false)
    feed_weight: float = 0.3         # pseudo-count weight of one piece of feed evidence


@dataclass
class Belief:
    cls: ClaimClass
    alpha: float
    beta: float
    anchor: float                    # tick at which (alpha, beta) hold; decay is measured from here
    verified_at: float               # tick of the last verification (or creation)

    @classmethod
    def fresh(cls, klass: ClaimClass, now: float) -> "Belief":
        return cls(klass, klass.prior_alpha, klass.prior_beta, now, now)

    # ------------------------------------------------------------------
    def effective(self, now: float) -> Tuple[float, float]:
        """Pseudo-counts after decaying toward the prior since the anchor."""
        age = max(0.0, now - self.anchor)
        k = math.exp(-self.cls.decay_rate * age)
        a = self.cls.prior_alpha + (self.alpha - self.cls.prior_alpha) * k
        b = self.cls.prior_beta + (self.beta - self.cls.prior_beta) * k
        return a, b

    def p_true(self, now: float) -> float:
        a, b = self.effective(now)
        return a / (a + b)

    def entropy(self, now: float) -> float:
        return _h(self.p_true(now))

    def staleness(self, now: float) -> float:
        return now - self.verified_at

    # ------------------------------------------------------------------
    def _collapse(self, now: float) -> None:
        self.alpha, self.beta = self.effective(now)
        self.anchor = now

    def apply_feed(self, says_true: bool, now: float) -> None:
        """Free evidence: nudge the decayed counts by feed_weight. The verification clock is untouched."""
        self._collapse(now)
        if says_true:
            self.alpha += self.cls.feed_weight
        else:
            self.beta += self.cls.feed_weight

    def apply_verification(self, says_true: bool, now: float) -> None:
        """Costly verification: Bayesian update under the test's noise model, one unit of weight, clock restarts."""
        self._collapse(now)
        n = self.alpha + self.beta + 1.0
        p = posterior_after(self, now, says_true)
        self.alpha, self.beta = p * n, (1 - p) * n
        self.verified_at = now


# ----------------------------------------------------------------------
# Decisions and value of information
# ----------------------------------------------------------------------
def _h(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def expected_loss(p: float, cls: ClaimClass) -> Dict[str, float]:
    return {"act": (1 - p) * cls.loss_act_when_false, "accept": p * cls.loss_accept_when_true}


def decide(p: float, cls: ClaimClass) -> str:
    losses = expected_loss(p, cls)
    return "act" if losses["act"] <= losses["accept"] else "accept"


def min_loss(p: float, cls: ClaimClass) -> float:
    return min(expected_loss(p, cls).values())


def p_verification_says_true(belief: Belief, now: float) -> float:
    p = belief.p_true(now)
    c = belief.cls
    return p * c.verify_sensitivity + (1 - p) * (1 - c.verify_specificity)


def posterior_after(belief: Belief, now: float, says_true: bool) -> float:
    """p(true) after a verification returns `says_true`, under the sensitivity/specificity model."""
    p = belief.p_true(now)
    c = belief.cls
    if says_true:
        q = p_verification_says_true(belief, now)
        return p * c.verify_sensitivity / q if q > 0 else p
    q = 1.0 - p_verification_says_true(belief, now)
    return p * (1 - c.verify_sensitivity) / q if q > 0 else p


def decision_voi(belief: Belief, now: float) -> float:
    """Expected reduction in expected loss from verifying now. Zero when no outcome would change the action."""
    p = belief.p_true(now)
    c = belief.cls
    p_yes, p_no = posterior_after(belief, now, True), posterior_after(belief, now, False)
    if decide(p_yes, c) == decide(p_no, c):
        return 0.0                       # structural zero: the action is settled either way
    q = p_verification_says_true(belief, now)
    after = q * min_loss(p_yes, c) + (1 - q) * min_loss(p_no, c)
    return max(0.0, min_loss(p, c) - after)


def entropy_voi(belief: Belief, now: float) -> float:
    """Expected entropy reduction (the mutual information between the test and the state)."""
    q = p_verification_says_true(belief, now)
    after = q * _h(posterior_after(belief, now, True)) + (1 - q) * _h(posterior_after(belief, now, False))
    return max(0.0, belief.entropy(now) - after)
