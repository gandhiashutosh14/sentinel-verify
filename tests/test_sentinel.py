import math
import pathlib
import random

import pytest

from sentinel.belief import (Belief, ClaimClass, decide, decision_voi, entropy_voi, expected_loss, posterior_after)
from sentinel.cli import main
from sentinel.policies import POLICIES, decision_voi_policy
from sentinel.simulate import compare, run, score_world
from sentinel.world import World, WorldSpec

ROOT = pathlib.Path(__file__).resolve().parents[1]
K = ClaimClass("k", prior_alpha=1.0, prior_beta=9.0, decay_rate=0.1, loss_act_when_false=1.0,
               loss_accept_when_true=6.0, verify_cost=1.0)


def test_decay_returns_toward_the_prior_and_only_verification_resets_the_clock():
    b = Belief(K, alpha=20.0, beta=1.0, anchor=0.0, verified_at=0.0)
    assert b.p_true(0.0) == pytest.approx(20 / 21)
    p10, p100 = b.p_true(10.0), b.p_true(100.0)
    assert p100 < p10 < b.p_true(0.0)
    assert p100 == pytest.approx(0.1, abs=0.01)            # back near the class prior
    half_life = math.log(2) / K.decay_rate
    a, _ = b.effective(half_life)
    assert a == pytest.approx(1.0 + 19.0 / 2)
    # feed evidence moves the belief but does not restart the clock
    before = b.verified_at
    b.apply_feed(True, now=30.0)
    assert b.verified_at == before and b.alpha < 20.0
    b.apply_verification(True, now=30.0)
    assert b.verified_at == 30.0


def test_decisions_follow_the_asymmetric_loss_table():
    assert decide(0.5, K) == "act"                         # accepting a true claim costs 6, acting on a false one costs 1
    assert decide(0.05, K) == "accept"
    assert expected_loss(0.2, K) == {"act": pytest.approx(0.8), "accept": pytest.approx(1.2)}


def test_decision_voi_is_zero_when_no_result_could_change_the_action_but_entropy_voi_is_not():
    settled = Belief(K, alpha=1.0, beta=200.0, anchor=0.0, verified_at=0.0)     # p ~ 0.005: accept whatever one check says
    assert decision_voi(settled, 0.0) == 0.0
    assert entropy_voi(settled, 0.0) > 0.0
    borderline = Belief(K, alpha=1.5, beta=8.5, anchor=0.0, verified_at=0.0)    # near the act/accept boundary
    assert decision_voi(borderline, 0.0) > 0.0
    assert decide(posterior_after(borderline, 0.0, True), K) != decide(posterior_after(borderline, 0.0, False), K)


def test_voi_is_never_negative_and_grows_with_staleness_for_a_once_confident_claim():
    b = Belief(K, alpha=1.0, beta=40.0, anchor=0.0, verified_at=0.0)
    values = [decision_voi(b, t) for t in (0.0, 20.0, 60.0, 120.0)]
    assert all(v >= 0 for v in values) and values[-1] > values[0]


def test_verification_update_is_bayesian_under_the_noise_model_and_feed_decays_with_everything_else():
    b = Belief(K, alpha=1.0, beta=9.0, anchor=0.0, verified_at=0.0)
    p_before = b.p_true(0.0)
    b.apply_verification(True, now=0.0)
    assert b.p_true(0.0) == pytest.approx(p_before * K.verify_sensitivity / (p_before * K.verify_sensitivity + (1 - p_before) * (1 - K.verify_specificity)))
    assert b.alpha + b.beta == pytest.approx(11.0)
    # re-anchoring at a feed event does not change the total decay since the verification
    c = Belief(K, alpha=20.0, beta=1.0, anchor=0.0, verified_at=0.0)
    direct = Belief(K, alpha=20.0, beta=1.0, anchor=0.0, verified_at=0.0).p_true(50.0)
    c._collapse(20.0)
    assert c.p_true(50.0) == pytest.approx(direct)
    assert c.staleness(50.0) == 50.0


def test_world_is_deterministic_per_seed_and_policies_respect_the_budget():
    spec = WorldSpec.load(str(ROOT / "worlds" / "exposure.json"))
    a, b = World(spec, 3), World(spec, 3)
    for w in (a, b):
        w.tick()
    assert [c.true_state for c in a.claims] == [c.true_state for c in b.claims]
    assert [c.belief.alpha for c in a.claims] == [c.belief.alpha for c in b.claims]
    rng = random.Random(0)
    for name, policy in POLICIES.items():
        chosen = policy(a.claims, a.now, 5.0, rng)
        assert sum(c.cls.verify_cost for c in chosen) <= 5.0, name
        assert len({c.id for c in chosen}) == len(chosen), name


def test_decision_voi_skips_zero_value_claims_even_with_budget_to_spare():
    spec = WorldSpec.load(str(ROOT / "worlds" / "exposure.json"))
    w = World(spec, 1)
    for c in w.claims:                       # make every claim decisively false
        c.belief.alpha, c.belief.beta, c.belief.anchor, c.belief.verified_at = 1.0, 500.0, w.now, w.now
    assert decision_voi_policy(w.claims, w.now, 1000.0, random.Random(0)) == []


def test_scoring_and_run_shapes():
    spec = WorldSpec.load(str(ROOT / "worlds" / "field.json"))
    r = run(spec, "random", seed=2, ticks=10, budget=8.0)
    assert r.ticks == 10 and r.spend <= 80.0 and 0.0 <= r.wrong_action_rate <= 1.0
    loss, wrong = score_world(World(spec, 2))
    assert loss >= 0 and 0 <= wrong <= len(spec.counts) * 1000


def test_decision_voi_beats_never_and_random_on_the_bundled_worlds():
    # An empirical check on the bundled synthetic worlds, averaged over seeds; not a general theorem.
    for world in ("exposure.json", "field.json"):
        spec = WorldSpec.load(str(ROOT / "worlds" / world))
        table = compare(spec, seeds=list(range(1, 7)), ticks=60, budget=6.0,
                        policies=["decision-voi", "random", "never"])
        assert table["decision-voi"]["mean_loss_per_tick"] < table["random"]["mean_loss_per_tick"], world
        assert table["decision-voi"]["mean_loss_per_tick"] < table["never"]["mean_loss_per_tick"], world


def test_cli_writes_report_and_json(tmp_path):
    out, js = tmp_path / "r.md", tmp_path / "r.json"
    assert main(["simulate", "--world", str(ROOT / "worlds" / "exposure.json"), "--budgets", "3", "--ticks", "15",
                 "--seeds", "2", "--out", str(out), "--json", str(js)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "Verification budget 3" in text and "decision-voi" in text and js.exists()
