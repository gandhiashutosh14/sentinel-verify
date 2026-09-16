# SENTINEL simulation: field (synthetic compliance claims with costly visits)

Generated 2026-09-16 22:53 UTC at revision 27035d8 with `sentinel simulate --world worlds/field.json --budgets 4 12 24 --ticks 200 --seeds 20 --out reports/field.md`.

Invented world modelled loosely on field verification of compliance claims: a visit is expensive, a false accusation (acting on a compliant plot) costs more than a missed problem in this loss table, and satellite-style feed evidence arrives often but is only moderately accurate. Nothing here describes a real programme.

180 synthetic claims, 200 ticks, 20 seeds per policy. Every policy sees the same beliefs and feed evidence; only the simulator knows the true states, which it uses to score the action each belief implies at every tick. Lower loss is better. These are results on an invented world, not measurements of any real system.

## Verification budget 4 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| decision-voi **(best)** | 306.33 | 18.40 | 0.317 | 0.397 | 200 |
| entropy-voi | 313.80 | 19.38 | 0.320 | 0.397 | 200 |
| random | 327.33 | 22.14 | 0.306 | 0.371 | 200 |
| oldest-first | 330.15 | 17.08 | 0.303 | 0.376 | 200 |
| score-sorted | 376.14 | 25.03 | 0.355 | 0.438 | 200 |
| never | 377.06 | 27.57 | 0.354 | 0.438 | 0 |

## Verification budget 12 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| entropy-voi **(best)** | 203.43 | 12.68 | 0.205 | 0.231 | 666 |
| oldest-first | 209.14 | 13.57 | 0.183 | 0.186 | 621 |
| decision-voi | 220.10 | 20.33 | 0.229 | 0.276 | 673 |
| random | 248.48 | 15.75 | 0.229 | 0.251 | 601 |
| score-sorted | 343.22 | 24.29 | 0.336 | 0.414 | 800 |
| never | 377.06 | 27.57 | 0.354 | 0.438 | 0 |

## Verification budget 24 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| entropy-voi **(best)** | 122.87 | 11.01 | 0.120 | 0.120 | 1326 |
| decision-voi | 130.18 | 13.42 | 0.131 | 0.145 | 1317 |
| oldest-first | 153.22 | 7.60 | 0.135 | 0.138 | 1246 |
| random | 187.53 | 13.32 | 0.170 | 0.183 | 1212 |
| score-sorted | 309.55 | 16.49 | 0.309 | 0.395 | 1503 |
| never | 377.06 | 27.57 | 0.354 | 0.438 | 0 |

## Reading the table

`decision-voi` ranks by expected reduction in decision loss per unit cost and never spends on a claim whose action no verification result could change. `entropy-voi` ranks by expected entropy reduction, so it keeps re-checking uncertain claims whose action is already settled by the loss table. `score-sorted` mimics sorting findings by a risk score; `oldest-first` mimics a freshness crawl; `never` shows what priors and free feed evidence achieve alone. Spread across seeds is the population standard deviation of the per-seed mean loss; differences inside that spread are not evidence of anything.
