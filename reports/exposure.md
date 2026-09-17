# SENTINEL simulation: exposure (synthetic attack-surface findings)

Generated 2026-09-16 22:52 UTC at revision 7337167 with `sentinel simulate --world worlds/exposure.json --budgets 2 5 10 --ticks 200 --seeds 20 --out reports/exposure.md`.

Invented world modelled loosely on external attack-surface findings: many low-prior hostname findings that rarely change, and fewer service findings that change often. Acting on a false finding wastes an analyst hour; accepting a true one is expensive. Nothing here describes a real network.

200 synthetic claims, 200 ticks, 20 seeds per policy. Every policy sees the same beliefs and feed evidence; only the simulator knows the true states, which it uses to score the action each belief implies at every tick. Lower loss is better. These are results on an invented world, not measurements of any real system.

## Verification budget 2 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| decision-voi **(best)** | 181.59 | 15.71 | 0.232 | 0.254 | 322 |
| oldest-first | 194.84 | 13.38 | 0.259 | 0.239 | 360 |
| random | 218.64 | 14.95 | 0.271 | 0.277 | 360 |
| entropy-voi | 252.50 | 18.76 | 0.283 | 0.330 | 400 |
| score-sorted | 316.33 | 22.42 | 0.335 | 0.405 | 200 |
| never | 322.54 | 20.74 | 0.342 | 0.415 | 0 |

## Verification budget 5 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| oldest-first **(best)** | 130.49 | 6.73 | 0.187 | 0.198 | 840 |
| decision-voi | 161.93 | 11.75 | 0.190 | 0.204 | 647 |
| random | 165.20 | 10.39 | 0.220 | 0.232 | 858 |
| entropy-voi | 170.59 | 13.66 | 0.214 | 0.250 | 1000 |
| score-sorted | 305.21 | 24.60 | 0.324 | 0.390 | 600 |
| never | 322.54 | 20.74 | 0.342 | 0.415 | 0 |

## Verification budget 10 per tick

| Policy | Mean loss / tick | ± across seeds | Wrong-action rate | Final wrong-action rate | Verifications / run |
|---|---:|---:|---:|---:|---:|
| oldest-first **(best)** | 103.33 | 5.57 | 0.141 | 0.138 | 1680 |
| decision-voi | 116.40 | 7.11 | 0.136 | 0.146 | 1302 |
| random | 118.24 | 9.64 | 0.166 | 0.159 | 1693 |
| entropy-voi | 129.03 | 10.82 | 0.176 | 0.180 | 1837 |
| score-sorted | 322.27 | 19.76 | 0.330 | 0.405 | 1000 |
| never | 322.54 | 20.74 | 0.342 | 0.415 | 0 |

## Reading the table

`decision-voi` ranks by expected reduction in decision loss per unit cost and never spends on a claim whose action no verification result could change. `entropy-voi` ranks by expected entropy reduction, so it keeps re-checking uncertain claims whose action is already settled by the loss table. `score-sorted` mimics sorting findings by a risk score; `oldest-first` mimics a freshness crawl; `never` shows what priors and free feed evidence achieve alone. Spread across seeds is the population standard deviation of the per-seed mean loss; differences inside that spread are not evidence of anything.
