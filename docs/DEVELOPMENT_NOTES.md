# Development notes

How this project was built. It was written from scratch on 2026-09-17; there is no earlier
history.

## Why this project exists

"Value-of-information verification scheduling under freshness decay" is a research direction in
the author's portfolio backlog, aimed at attack-surface monitoring and field verification. The
first release is the smallest honest version: a simulator, the mechanism, the obvious baselines,
and a report that says what happened. No employer code or data was used; both worlds are invented.

## First release, 2026-09-17

The release was scoped as a small verified increment, with everything simulated labelled as such.

### Design decisions

- Beliefs decay exponentially toward a class prior. Because the decay is exponential, it can be
  re-anchored at any evidence event without changing the total decay since the last verification,
  which is what lets feed evidence update a belief without touching the last-verified clock.
- Verification is a noisy test with known sensitivity and specificity. Its posterior is the
  Bayesian one under that model, folded back into Beta counts with one more unit of weight, so the
  value the scheduler computes and the update the store applies agree.
- Value of information is measured against the decision, not against entropy, and is a
  structural zero when both possible results lead to the same action.
- Every policy sees the same beliefs; only the simulator knows the truth and scores the actions.

### What the tests caught

- The first `apply_feed` collapsed the decay state and then set the verification clock to "now",
  which is precisely the behaviour the design forbids. Caught by the clock-semantics test; fixed
  by separating the decay anchor from the last-verified time.
- The first value-of-information used a pseudo-count posterior that ignored the test's noise. For
  a confidently-false claim the expected posterior entropy came out *higher* than the prior
  entropy, so the entropy objective clamped to zero and the test failed. Fixed by using the
  Bayesian posterior under the sensitivity/specificity model for both objectives.
- `decision_voi` returned 3e-18 instead of 0 for a settled claim, and the policy treats any
  positive value as worth a check. Fixed by returning an exact zero when both outcomes lead to the
  same action.

### What the simulation showed

The decision-relevant objective wins at the smallest budget in both worlds and loses at larger
budgets, to oldest-first in one world and to the entropy objective in the other. The cause is
that the greedy one-step value ignores the flip hazard. This was not the expected result and is
reported as found; no parameter was tuned to change it.

### Verification

| Check | Result |
|---|---|
| `pytest -q` | 10 passed |
| `sentinel simulate --world worlds/exposure.json --budgets 2 5 10 --ticks 200 --seeds 20` | `reports/exposure.md` |
| `sentinel simulate --world worlds/field.json --budgets 4 12 24 --ticks 200 --seeds 20` | `reports/field.md` |

### What is and is not claimed

Two invented worlds, deterministic seeds, one greedy mechanism and five baselines. The numbers
describe those worlds. They say nothing about any real network, compliance programme or dataset,
and the README states the case where the mechanism loses.
