"""
Run every policy on the same seeded world and score them.

Scoring is done by the simulator, which knows the truth. At every tick, after verification,
each claim's action is decided from its belief and scored against its true state with the
class loss table. Reported per policy: mean realised decision loss per tick (the number the
scheduler exists to reduce), wrong-action rate, verification spend, and the same numbers on the
final tick only.
"""
from __future__ import annotations

import json
import random
import statistics
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from .belief import decide
from .policies import POLICIES
from .world import World, WorldSpec

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RunResult:
    policy: str
    seed: int
    ticks: int
    budget: float
    mean_loss_per_tick: float
    wrong_action_rate: float
    final_wrong_action_rate: float
    verifications: int
    spend: float


def score_world(world: World) -> tuple[float, int]:
    loss, wrong = 0.0, 0
    for c in world.claims:
        action = decide(c.belief.p_true(world.now), c.cls)
        if action == "act" and not c.true_state:
            loss += c.cls.loss_act_when_false
            wrong += 1
        elif action == "accept" and c.true_state:
            loss += c.cls.loss_accept_when_true
            wrong += 1
    return loss, wrong


def run(spec: WorldSpec, policy_name: str, *, seed: int, ticks: int, budget: float) -> RunResult:
    world = World(spec, seed)
    policy = POLICIES[policy_name]
    rng = random.Random(seed * 7919 + 17)
    losses, wrongs = [], []
    n = len(world.claims)
    for _ in range(ticks):
        world.tick()
        for claim in policy(world.claims, world.now, budget, rng):
            world.verify(claim)
        loss, wrong = score_world(world)
        losses.append(loss)
        wrongs.append(wrong / n)
    return RunResult(policy=policy_name, seed=seed, ticks=ticks, budget=budget,
                     mean_loss_per_tick=statistics.fmean(losses), wrong_action_rate=statistics.fmean(wrongs),
                     final_wrong_action_rate=wrongs[-1], verifications=world.verifications, spend=world.spend)


def compare(spec: WorldSpec, *, seeds: List[int], ticks: int, budget: float,
            policies: List[str] | None = None) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for name in policies or list(POLICIES):
        rs = [run(spec, name, seed=s, ticks=ticks, budget=budget) for s in seeds]
        losses = [r.mean_loss_per_tick for r in rs]
        out[name] = {
            "mean_loss_per_tick": statistics.fmean(losses),
            "loss_stdev_across_seeds": statistics.pstdev(losses) if len(losses) > 1 else 0.0,
            "wrong_action_rate": statistics.fmean(r.wrong_action_rate for r in rs),
            "final_wrong_action_rate": statistics.fmean(r.final_wrong_action_rate for r in rs),
            "verifications_per_run": statistics.fmean(r.verifications for r in rs),
            "spend_per_run": statistics.fmean(r.spend for r in rs),
        }
    return out


def sweep(spec: WorldSpec, *, seeds: List[int], ticks: int, budgets: List[float]) -> Dict[float, Dict[str, Dict[str, float]]]:
    return {b: compare(spec, seeds=seeds, ticks=ticks, budget=b) for b in budgets}


# ----------------------------------------------------------------------
def _revision() -> str:
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
        status = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT, text=True)
        dirty = [l for l in status.splitlines() if l.strip() and "reports/" not in l]
        return sha + (" (uncommitted changes present)" if dirty else "")
    except Exception:  # noqa: BLE001
        return "unknown"


def render(spec: WorldSpec, results: Dict[float, Dict[str, Dict[str, float]]], seeds: List[int], ticks: int, command: str) -> str:
    n = sum(spec.counts.values())
    lines = [f"# SENTINEL simulation: {spec.name}", "",
             f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} at revision {_revision()} with `{command}`.",
             "", spec.description, "",
             f"{n} synthetic claims, {ticks} ticks, {len(seeds)} seeds per policy. Every policy sees the same beliefs and feed "
             "evidence; only the simulator knows the true states, which it uses to score the action each belief implies at "
             "every tick. Lower loss is better. These are results on an invented world, not measurements of any real system.", ""]
    for budget, table in results.items():
        best = min(table, key=lambda k: table[k]["mean_loss_per_tick"])
        lines += [f"## Verification budget {budget:g} per tick", "",
                  "| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |",
                  "|---|---:|---:|---:|---:|---:|"]
        for name, m in sorted(table.items(), key=lambda kv: kv[1]["mean_loss_per_tick"]):
            mark = " **(best)**" if name == best else ""
            lines.append(f"| {name}{mark} | {m['mean_loss_per_tick']:.2f} | {m['loss_stdev_across_seeds']:.2f} | "
                         f"{m['wrong_action_rate']:.3f} | {m['final_wrong_action_rate']:.3f} | {m['verifications_per_run']:.0f} |")
        lines.append("")
    lines += ["## Reading the table", "",
              "`decision-voi` ranks by expected reduction in decision loss per unit cost and never spends on a claim whose "
              "action no verification result could change. `entropy-voi` ranks by expected entropy reduction, so it keeps "
              "re-checking uncertain claims whose action is already settled by the loss table. `score-sorted` mimics "
              "sorting findings by a risk score; `oldest-first` mimics a freshness crawl; `never` shows what priors and "
              "free feed evidence achieve alone. Spread across seeds is the population standard deviation of the per-seed "
              "mean loss; differences inside that spread are not evidence of anything."]
    return "\n".join(lines) + "\n"
