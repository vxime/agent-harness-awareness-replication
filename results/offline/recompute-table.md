# Recompute table — L0 offline audit (Step 1 + Step 3)

Archive: manu2/scac-dynamic-agent-harness @ d98e3610e880ab06421b4e53bb0cd892c1b19170 (frozen clone, read-only).
Paths: (a) authors' analysis scripts re-run offline; (b) independent per-decision recomputation
from retained artifacts (host.json / snapshot.json monitor facts) using the frozen observable oracle

## Study 1 (216 decisions)

| quantity | reported | authors' script rerun | independent recompute | match |
|---|---|---|---|---|
| mean regret arm A (ms) | 4,826.45 | see note | 4,826.45 | YES |
| mean regret arm B (ms) | 4,251.54 | see note | 4,251.54 | YES |
| mean regret arm C (ms) | 131.12 | see note | 131.12 | YES |
| completions arm A | 47/72 | — | 47/72 | YES |
| completions arm B | 50/72 | — | 50/72 | YES |
| completions arm C | 69/72 | — | 69/72 | YES |
| mean regret arm C, claude-sonnet-5 (ms) | 75.50 | — | 75.50 | YES |
| mean regret arm C, gemini-3.7-flash (ms) | 242.35 | — | 242.35 | YES |
| mean regret arm C, gpt-5.6-sol (ms) | 75.50 | — | 75.50 | YES |

Per-decision check (Study 1): recomputed regret at P=10,000 vs recorded `policy_regret` for all 216 decisions: max abs diff 0 ms; 216 exact, 216 within 1e-6.
Authors'-script rerun condition summary is byte-identical in values to the committed `paper/analysis/toolroute_v1_analysis.json` (A 4,826.4478 / B 4,251.5426 / C 131.1190 ms; completions 47/50/69).

## Study 2 (27 decisions)

| quantity | reported | authors' script rerun | independent recompute | match |
|---|---|---|---|---|
| mean regret arm A (ms) | 6,734.30 | see note | 6,734.30 | YES |
| mean regret arm B (ms) | 8,956.37 | see note | 8,956.37 | YES |
| mean regret arm C (ms) | 0.00 | see note | 0.00 | YES |
| live completions arm A | 6/9 | — | 6/9 | YES |
| live completions arm B | 5/9 | — | 5/9 | YES |
| live completions arm C | 9/9 | — | 9/9 | YES |

Per-decision check (Study 2): recomputed regret at P=10,000 vs recorded `policy_regret` for all 27 episodes: max abs diff 0 ms; 27 exact, 27 within 1e-6.
Authors'-script rerun (path-adjusted copy, logic untouched) condition summary equals the committed `paper/analysis/toolroute_otel_transport_v0_2_analysis.json` exactly (A 6,734.3033 / B 8,956.3667 / C 0.0 ms; live completions 6/5/9).

## Step 3 — Study 2 arm C zero decomposition (all 9 decisions)

Regret components under the frozen oracle at P=10,000. `exact zero` means the recomputed float is 0.0, not a rounded small value.

| model | regime | chosen | chosen cost = EWMA + fail-comp + circuit-comp | best cost | regret | wait? |
|---|---|---|---|---|---|---|
| gemini-3.7-flash | connection_error | tool_alpha | 1.34 = 1.34 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.34 | 0.0000 | no |
| gpt-5.6-sol | http_error | tool_beta | 0.84 = 0.84 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 0.84 | 0.0000 | no |
| claude-sonnet-5 | connection_error | tool_beta | 0.99 = 0.99 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 0.99 | 0.0000 | no |
| gemini-3.7-flash | latency | tool_beta | 1.12 = 1.12 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.12 | 0.0000 | no |
| gemini-3.7-flash | http_error | tool_beta | 0.82 = 0.82 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 0.82 | 0.0000 | no |
| claude-sonnet-5 | latency | tool_alpha | 1.38 = 1.38 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.38 | 0.0000 | no |
| gpt-5.6-sol | connection_error | tool_alpha | 1.15 = 1.15 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.15 | 0.0000 | no |
| claude-sonnet-5 | http_error | tool_alpha | 1.36 = 1.36 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.36 | 0.0000 | no |
| gpt-5.6-sol | latency | tool_beta | 1.95 = 1.95 + 0.00 (rate 0.000) + 0.00 (CLOSED) | 1.95 | 0.0000 | no |

In every arm-C episode the chosen route is the observable-best route; its cost is its latency EWMA alone (0.82-1.95 ms) with zero failure component (rate 0, successes 3/3) and zero circuit component (CLOSED). The faulted other route carries failure rate 1.0 plus an OPEN circuit in the six connection_error/http_error episodes (cost 20,000.80-20,005.30 ms), and is latency-only in the three latency episodes (EWMA 302.64-303.69 ms, rate 0, CLOSED). No arm-C decision is a wait. The zero is therefore exact and is carried by zero unsuccessful calls and zero open circuits on the chosen route, as pre-registered.
