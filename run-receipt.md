Public edition of the two test receipts for this topic (L0 offline archive
audit + L2 live subset), merged into one document. All numbers, verdicts,
deviations and limitations are preserved verbatim in substance. Sanitisation
applied to this edition: the model endpoint is described generically as an
OpenAI-compatible gateway endpoint labelled `gpt-6-luna` (underlying identity
unverifiable); local file paths and internal project references are replaced
by this package's layout. No result was changed.

---

# Receipt 1 — L0 offline archive audit (2026-11-06)

Scope executed: the pre-registered L0 level of the experiment plan only (PROTOCOL.md, Part 1). Zero model calls were made. The L2 live subset was **not** run (deviation D4 below). Verdicts are bounded to the authors' frozen archive and to our parameterisation of the sensitivity analysis; nothing here re-collects any model decision.

## Verdict

**Composite: PARTIAL** — the accounting layer reproduces exactly; the interpretation layer is only partly settled.

- Headline accounting (ha-c3, ha-c4, ha-c5): **REPRODUCED, strongest form.** Every one of the 243 retained decisions recomputes to the recorded `policy_regret` with max abs diff 0.0, and both studies' headline tables match the paper at published precision via two independent paths (the authors' own analysis scripts and our per-decision recomputation from raw host/snapshot quantities).
- Pricing sensitivity (ha-c6): **CONFIRMED AND QUANTIFIED.** The −96.9% headline is materially pricing-dependent: about 29 percentage points of it are the 10,000 ms penalty pricing. The effect itself survives all three pre-registered pricings (67.8% at 1,000 ms), and the completion-rate contrast does not depend on pricing at all.
- Route-label concentration (ha-c7): **STRENGTHENED as a concern, attribution NOT RESOLVED.** Baseline regret is almost entirely concentrated in decisions where the canonical best route was beta and the model defaulted to alpha. Whether that default is a label/presentation effect or an information-absence effect cannot be separated from retained artifacts; the Step 4 probe design (below) is the deciding experiment and belongs to the L2 model decision.

## Archive state used

- Repository: `github.com/manu2/scac-dynamic-agent-harness`, read-only clone at commit `d98e3610e880ab06421b4e53bb0cd892c1b19170` (cloned 2026-11-06T07:39:38Z, working tree clean throughout).
- Frozen manifests: `toolroute_api_paper.v1.0.json` (Study 1), `toolroute_otel_transport_pilot.v0.2.json` (Study 2). Finalization hashes verified on read.

## Step 1 — headline recomputation (MATCH)

| Study | Quantity | Reported | Recomputed |
|---|---|---|---|
| 1 | Mean regret A / B / C (ms) | 4,826.45 / 4,251.54 / 131.12 | 4,826.45 / 4,251.54 / 131.12 |
| 1 | Completions A / B / C | 47/72 / 50/72 / 69/72 | identical |
| 1 | Per-model C means (ms) | 75.50 / 75.50 / 242.35 | identical |
| 2 | Mean regret A / B / C (ms) | 6,734.30 / 8,956.37 / 0.00 | identical |
| 2 | Completions A / B / C | 6/9 / 5/9 / 9/9 | identical |

Per-decision check: 216/216 (Study 1) and 27/27 (Study 2) recomputed regrets exactly equal the recorded values (max abs diff = 0.0). Full tables: `results/offline/recompute-table.md`; machine-readable results: `results/offline/results.json`; per-decision diff: `results/evidence/recomputation-diff.json`; scripts: `code/offline-audit/scripts/offline_audit.py`.

## Step 2 — penalty-constant sensitivity (PARTIAL vs pre-registered expectation)

Frozen wait rule unchanged (`500 + 10,000 − best cost`); only the two cost penalties (unsuccessful-call rate and open-circuit) were repriced. Observable-best re-selected under each pricing.

Study 1, B→C mean-regret reduction: **96.9%** at 10,000 ms → **89.8%** at 5,000 ms → **67.8%** at 1,000 ms (A→C: 97.3% → 91.0% → 71.5%). Two mechanisms: (i) A/B means are mostly penalty mass and shrink roughly with the constant; (ii) C's mean *rises* as pricing falls (131.12 → 256.12 → 356.12 ms) because C's entire residual regret is its 3 wait decisions, and the frozen wait score `10,500 − best_P` grows as `best_P` shrinks.

Study 2: C is exactly 0 at all three pricings, so the percentage reduction is degenerate (100% throughout, uninformative). The absolute B−C gap shrinks with pricing: 8,956.37 → 4,511.92 → 956.37 ms.

Pre-registered expectation (drop shrinks as constants fall, completions stand) holds for Study 1; for Study 2 the percentage form cannot express it — recorded as PARTIAL, with absolute gaps reported instead.

## Step 3 — Study 2 zero decomposition (MATCH)

Arm C's 9 decisions are exact float 0.0, not rounding: in each, the chosen route is the unique observable-best; its cost is latency EWMA only (0.82–1.95 ms) with unsuccessful-call rate 0 (3/3 successes) and circuit CLOSED; no waits. The counterfactual route in the 6 connection/http episodes prices at 20,000.80–20,005.30 (rate 1.0 + OPEN); in the 3 latency episodes it is pure delay (EWMA 302.64–303.69, rate 0, CLOSED).

## Step 6 — route-label concentration (first-party, from retained artifacts)

Correction of scope for the paper's "17/18 (94.4%)": that figure describes **Study 2** arms A/B, and we reproduce it exactly (alpha chosen 17/18). In Study 2, the 10 decisions where the canonical best is uniquely beta: **10/10 chose alpha**, carrying **85.8%** of total A/B regret (A arm 100%, B arm 75.2%).

Study 1 is more extreme: alpha chosen in 140/144 A/B decisions; of the 78 decisions where the canonical best is uniquely beta, 75 chose alpha, carrying **98.9%** of total A/B regret (A 97.9%, **B 100.0%**).

Bounded reading: in arms without verified state, nearly all measured regret sits in "defaulted to alpha while beta was canonically best" decisions. This bounds, but does not decide, the attribution question — a model that cannot see operational facts and a model with a label default produce the same retained trace here. Deciding requires the Step 4 probe.

## Step 4 — route-label probe (design only, not executed)

- **SWAP arm**: identical tasks, fault schedules and envelopes; route labels exchanged and option order independently permuted per episode.
- **ANON arm**: per-episode neutral random labels (no persistent alpha/beta identity).
- Shape: Study 2 geometry, 2 treatments × 27 = **54 calls** if run with the paper's model trio shape. It decides whether baseline regret follows the *label* (presentation artefact) or the *information condition* (snapshot effect).
- Recommendation recorded for the receipt review: decide this probe **together with** the plain Study 2 replication (27 calls) as one model-assignment decision — the plain replication alone cannot answer the attribution question, which is now the article's central open point.

## Deviations

- **D1 (author scripts' cosmetic crash).** Both author analysis scripts crash on a trailing `relative_to` path print *after* writing their outputs. Values were taken from the written outputs and cross-checked line-by-line against the versions committed in the archive; identical.
- **D2 (path-adjusted copy).** The Study 2 author script hardcodes in-repo output paths; a copy with exactly two path constants changed (logic untouched, diff retained in scripts/) was used to honour the read-only constraint on the clone.
- **D3 (environment).** Study 1 author script needs `reportlab`; run in a throwaway temporary venv. System Python untouched. The oracle branch `window=0 → rate 0.5` never triggers in any of the 243 decisions (window_n is always 3) — noted, no action.
- **D4 (L2 skipped, per stop condition 2).** No owner-approved model assignment exists; no model was substituted silently. The live subset, and with it the Step 4 probe execution, awaits the owner's model decision.

## Claim outcomes

- ha-c3 / ha-c4 / ha-c5: reproduced exactly from frozen artifacts → see new first-party claim ha-c13.
- ha-c6: confirmed and quantified → ha-c14.
- ha-c7: concentration quantified and stronger than the paper's own framing; attribution unresolved → ha-c15.
- ha-c1 / ha-c2 / ha-c8 / ha-c10 / ha-c11 / ha-c12: unaffected by this audit (design, scope and archive-availability claims; c12's call counts re-verified arithmetically).
- ha-c9: superseded in strength by ha-c13 (full per-decision recomputation replaces rounded-entry spot checks).

## New first-party claims added

- **ha-c13** — full recomputation identity (243/243 decisions, max abs diff 0.0; headline tables at published precision).
- **ha-c14** — pricing sensitivity numbers (Study 1 B→C 96.9 / 89.8 / 67.8% across 10,000 / 5,000 / 1,000 ms; C-mean inversion mechanism; Study 2 absolute gaps 8,956.37 / 4,511.92 / 956.37 ms).
- **ha-c15** — label concentration (Study 1: 75/78 beta-best decisions chose alpha, 98.9% of A/B regret; Study 2: 10/10, 85.8%; attribution unresolved).

Evidence pack and reader-handoff assessment revisions were deferred to the writing stage with the first-party Brief revision.

---

# Receipt 2 — L2 live subset: Study 2 replication shape + label probe (2026-11-06)

Addendum to Receipt 1 (L0). Executed under the L2 authorisation amendment in the pre-registered experiment plan: the owner assigned a single model — an OpenAI-compatible gateway endpoint labelled **`gpt-6-luna`** (underlying identity unverifiable) — for all 81 calls, after being shown that the gateway lists no Claude or Gemini label (29 GPT-family labels) and the paper's printed trio therefore cannot be assembled. This is a recorded substitution relative to the paper; every reading below is bounded to "the gateway-labelled gpt-6-luna endpoint" (underlying identity not independently verifiable). No other model was called. Protocol (`PROTOCOL.md`, Part 2) was written and frozen before the first analysis call.

## Execution facts

- 81/81 analysis calls succeeded (plus 1 pre-run smoke, 16 tokens, excluded), 0 failures, 0 retries, no stop rule triggered. Window 2026-11-06T07:59:55Z–08:03:20Z. All 81 responses carry the `gpt-6-luna` label and parse to exactly one valid route label; no waits chosen.
- Prompts: the archive's preserved Study 2 provider requests verbatim (pre-run check C1: 27/27 agreement with condition inputs; zero reconstruction). Per-cell repetitions are the cell's 3 archived episode instances (one per source model) — deviation D-L2-1, pre-registered in the protocol to preserve the paper's pooled fault-side mix.
- Scoring is offline against the L0 frozen oracle (cost at P=10,000; paper completion definition; pre-run check C2: 27/27 reproduction of archived live success flags). The paper's live Toxiproxy/OTel transport layer was **not** re-enacted (deviation D-L2-3); "live" refers to the model decisions only.
- Measured usage: 20,781 tokens total (17,844 in / 2,937 out) ≈ US$0.007 at third-party tracked prices recorded for this label (estimate, not a gateway bill).

## Replication block (27 calls, pooled per-arm n=9) — PATTERN_REPLICATED

| Arm | Our mean regret | Paper pooled | Our completions | Paper |
|---|---|---|---|---|
| A | 6,734.30 ms | 6,734.30 ms | 6/9 | 6/9 |
| B | 6,734.02 ms | 8,956.37 ms | 6/9 | 5/9 |
| C | 0.00 ms | 0.00 ms | 9/9 | 9/9 |

Per-instance agreement with the archived decisions: 26/27 (A 9/9, B 8/9, C 9/9). Arm A matches to the cent because the decisions are identical. The entire B gap traces to one archived instance (`gpt-07-connection-b`, a single 20,001.09 ms miss) that this endpoint did not repeat. Arm C chose the canonical best in all 9, regret exactly 0.

## Probe block (54 calls: SWAP + ANON) — formal verdict MIXED_OR_UNDECIDABLE, with a decisive sub-finding

Pre-registered analysis subset S = A/B instances where beta is uniquely canonically best (n=10 per treatment):

- **REP**: physical alpha chosen 10/10 (matches the paper's pooled 10/10). Subset mean regret 12,121.49 ms.
- **SWAP** (labels exchanged, facts unchanged, option order permuted): choices followed the `tool_alpha` **string** 10/10 — i.e. flipped to the other physical route — and subset regret fell to exactly **0.00**, because the alpha label now sat on the canonically best route.
- **ANON** (labels anonymised per episode, mention order preserved): physical alpha still chosen **10/10**, per-instance regret identical to REP (12,121.49).
- Position alone does not explain it (first-listed choice shares 10/18, 12/18, 12/18 across treatments, below the protocol's 0.7 threshold).
- **Arm C regret is 0.00 under all three treatments**, including the 4 SWAP instances where the label default pointed at the faulty route (`C_SWAP_badbeta` mean 0.00): given the verified snapshot, the model followed the facts against the label pull.

Under the frozen verdict rules this is MIXED_OR_UNDECIDABLE: LABEL_EFFECT_DOMINANT fails its ANON clause, PHYSICAL_DEFAULT and POSITION_EFFECT also fail. The load-bearing limitation is D-L2-4: ANON anonymised label identity but preserved narrative mention order (the prompt always introduces the physical-alpha route first), so ANON measured the first-mention cue, not a cue-free baseline.

Bounded interpretation (what the article may claim): a **pure information-absence reading of baseline regret is excluded**. The baseline default is deterministic and per-instance predictable — not noise under ignorance — and behaves as a *presentation default* with (at least) two stacked cues: meaningful label identity first (SWAP: the label string overrode even permuted option order), narrative first mention second (ANON). The verified snapshot overrides both cues in arm C, which concretely strengthens the paper's mechanism claim, while re-characterising what the baseline regret mostly *is*: substantially the price of a presentation default, not only the price of missing telemetry. Full separation of the first-mention cue would need an order-permuted ANON variant; it was not in the approved protocol and was not run.

## Deviations

- **D-L2-1** Repetitions = the 3 archived instances per cell (one per source model), not 3 fresh samples of one instance. Pre-registered in the protocol (a single-instance design would fix the best route in half the cells and break the probe).
- **D-L2-2** Decoding: no temperature set (gateway default), request shape per the archive's OpenAI adapter (`max_completion_tokens=1024`, no recorded temperature). Repetitions are random samples; small splits must not be over-read.
- **D-L2-3** Transport layer not re-enacted; offline scoring vs frozen canonical facts (agreed scope in the amendment).
- **D-L2-4** ANON preserved narrative mention order (and, in arm B, telemetry line order) — see above; the first-mention cue is not separated.
- **D-L2-5** Model substitution (single gateway-labelled gpt-6-luna for the paper's three-provider trio) — owner-decided and recorded in the amendment; not a run-time deviation.

## Claim outcomes

- New first-party claim **ha-c16**: the replication block (pattern replicated at single-model shape; B gap traced to one archived instance).
- New first-party claim **ha-c17**: the probe block (SWAP label-following 10/10 → subset regret 0.00; ANON persistence 10/10; arm C 0.00 under all treatments incl. label-trap instances; formal verdict MIXED_OR_UNDECIDABLE; bounded interpretation).
- **ha-c15** revised: concentration reproduces live on this endpoint (REP A/B chose the alpha label 18/18); attribution narrowed per ha-c17, formally undecided on the first-mention cue.
- ha-c13 / ha-c14 unaffected. The L0 composite verdict **PARTIAL stands, narrowed**: every pre-registered question is now answered except the first-mention residue of the attribution question.

## Status

TESTING_COMPLETE (final). Evidence pack and reader-handoff assessment revisions remained scheduled for the writing stage with the first-party Brief revision.
