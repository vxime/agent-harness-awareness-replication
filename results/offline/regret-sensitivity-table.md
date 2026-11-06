# Regret sensitivity to the penalty constant P — L0 offline audit (Step 2)

Frozen rules: route cost = latency_EWMA + P x failure_rate + P x [circuit=OPEN]; the wait rule is NOT rescaled (wait regret = 500 + 10,000 - best_P); observable-best is re-selected under the same P for every decision. Completion rates do not depend on P (they come from recorded outcomes) and are unchanged across all rows: Study 1 A 47/72, B 50/72, C 69/72; Study 2 A 6/9, B 5/9, C 9/9.

## Study 1 (216 decisions)

| P (ms) | mean regret A | mean regret B | mean regret C | B->C drop | A->C drop |
|---|---|---|---|---|---|
| 10,000 | 4,826.45 | 4,251.54 | 131.12 | 96.9% | 97.3% |
| 5,000 | 2,839.57 | 2,503.86 | 256.12 | 89.8% | 91.0% |
| 1,000 | 1,250.06 | 1,105.71 | 356.12 | 67.8% | 71.5% |

## Study 2 (27 decisions)

| P (ms) | mean regret A | mean regret B | mean regret C | B->C drop | A->C drop |
|---|---|---|---|---|---|
| 10,000 | 6,734.30 | 8,956.37 | 0.00 | 100.0% | 100.0% |
| 5,000 | 3,400.97 | 4,511.92 | 0.00 | 100.0% | 100.0% |
| 1,000 | 734.30 | 956.37 | 0.00 | 100.0% | 100.0% |
