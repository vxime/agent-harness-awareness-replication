# Protocol — L0 offline archive audit + L2 live subset

Both levels were frozen before execution on 2026-11-06: the L0 audit followed
the pre-registered experiment plan, and the L2 protocol (Part 2) was written
and frozen before the first analysis call. Deviations are recorded inside
each part and in `run-receipt.md`; none are hidden.

## Part 1 — L0 offline archive audit protocol

Scope: the authors' frozen archive only (`manu2/scac-dynamic-agent-harness`
@ `d98e3610e880ab06421b4e53bb0cd892c1b19170`; frozen manifests
`toolroute_api_paper.v1.0.json` for Study 1 and
`toolroute_otel_transport_pilot.v0.2.json` for Study 2; finalization hashes
verified on read). **Zero model calls.** Nothing is re-collected; every check
runs on the retained artifacts.

Two independent recomputation paths, required to agree:

- **Path (a)** — the authors' own analysis scripts, re-run offline on the
  retained artifacts.
- **Path (b)** — our per-decision recomputation from the raw host/snapshot
  quantities of every retained decision, using the authors' frozen
  observable oracle (`observable_monitor_cost_v0.6`):
  - `failure_rate = (window - successes) / window` (0.5 if window == 0; this
    branch never triggers in the 243 decisions — window_n is always 3);
  - `cost_P(route) = latency_EWMA + failure_rate x P + (P if circuit == OPEN)`;
  - `best_P = min` over the two routes, re-selected under the same P;
  - `regret_P(route) = cost_P(route) - best_P`;
  - `regret_P(wait) = 500 + 10,000 - best_P` — the frozen wait rule is
    **never rescaled** with P.

Steps:

1. **Headline recomputation (P = 10,000).** Per-decision recomputed regret vs
   recorded `policy_regret` for all 243 decisions (Study 1: 216, Study 2:
   27), plus both studies' headline tables (arm means, completions,
   per-model C means) against the paper at published precision.
2. **Penalty-constant sensitivity.** Reprice every decision at the two
   pre-registered alternative constants P ∈ {5,000, 1,000} ms (the wait rule
   unchanged, observable-best re-selected per pricing) and report the B→C
   and A→C reductions per pricing; for Study 2, whose arm C is 0, report
   absolute B−C gaps as well. Completion rates are recorded outcomes and do
   not depend on P.
3. **Study 2 zero decomposition.** For arm C's 9 decisions, decompose the
   recomputed cost into latency / failure / circuit components to establish
   whether the reported 0 is exact or a rounding artefact.
4. **Route-label concentration.** In arms A/B, measure how much of the total
   regret sits in decisions where the canonical best route is uniquely beta
   but alpha was chosen (per study, per arm), as the retained-artifact form
   of the paper's self-flagged label confound. Attribution (label effect vs
   information absence) is explicitly **not** decidable at this level; the
   deciding probe is Part 2.

Deviations at this level:

- **D1 (author scripts' cosmetic crash).** Both author analysis scripts
  crash on a trailing `relative_to` path print *after* writing their
  outputs. Values were taken from the written outputs and cross-checked
  line-by-line against the versions committed in the archive; identical.
- **D2 (path-adjusted copy).** The Study 2 author script hardcodes in-repo
  output paths; a copy with exactly two path constants changed (logic
  untouched) was used to honour the read-only constraint on the clone. The
  authors' scripts themselves are not redistributed in this package;
  path (b) above is fully self-contained in
  `code/offline-audit/scripts/offline_audit.py`.
- **D3 (environment).** The Study 1 author script needs `reportlab`; it was
  run in a throwaway temporary venv. System Python untouched.

## Part 2 — L2 live subset protocol (public edition)

The protocol below is the frozen pre-run document, with only the endpoint
description generalised and file references mapped to this package's layout.

Date: 2026-11-06. Authorisation: the pre-registered experiment plan, "L2
authorisation amendment (recorded 2026-11-06T07:56:24Z)". The owner assigned a
single model — an OpenAI-compatible gateway endpoint labelled **`gpt-6-luna`**
(underlying identity not independently verifiable) — for all 81 calls. This is
a recorded substitution relative to the paper's printed trio (GPT-5.6 Sol /
Claude Sonnet 5 / Gemini 3.7 Flash): the gateway carries no Claude and no
Gemini label at all, and no other provider account was available. All readings are bounded to "the
gateway-labelled gpt-6-luna endpoint" (underlying identity not independently
verifiable). **No other model may be used; on endpoint failure or quota
exhaustion the run stops and reports partial results — no silent substitution.**

## Design

Study 2 geometry at single-model shape, 81 calls in 3 treatment blocks of 27:

| Block | Calls | Content |
|---|---|---|
| REP | 27 | Verbatim archived Study 2 prompts (replication block) |
| SWAP | 27 | Same instances, route labels globally exchanged + option order reversed |
| ANON | 27 | Same instances, route labels replaced by per-episode random neutral codes |

Cells: 3 regimes (connection_error / http_error / latency) × 3 arms
(A = no envelope, B = neutral envelope, C = verified snapshot) × 3 reps.
**Rep = archived episode instance**: for cell (regime, arm) the 3 reps are the 3
archived episode directories of that cell (one per source model: gpt-5.6-sol /
claude-sonnet-5 / gemini-3.7-flash), so each pooled arm has n=9 and the pooled
fault-side composition per cell is identical to the paper's pooled Study 2
(per arm: 5 of 9 instances have physical tool_beta as the unique canonical best;
arms A+B together: 10, matching the population behind the paper's 17/18 figure).
Each rep is scored against its own directory's `snapshot.json` facts.

Call order is fixed: REP (seq 1–27), SWAP (28–54), ANON (55–81); within a block,
regime × arm × rep in the order of `call-specs.json`. Timestamps are recorded
per call.

## Prompt provenance

Prompts are the archive's preserved texts, verbatim — no reconstruction.
For (dir, arm): the dir's own-condition prompt is its `provider-request.json`
text; the other two arms come from the same dir's `condition-inputs.json`.
Pre-run check C1 (passed): provider-request text equals
`condition-inputs[own arm].prompt` for all 27 dirs. Check C3 (passed): the task
line is identical across all instances. Each call is a single user message with
the prompt text, mirroring all three archived adapters (no system prompt in any
of them).

## Transformations (probe block)

Applied to the verbatim base prompt of the same (instance, arm):

- **SWAP**: (1) global string exchange `tool_alpha` ↔ `tool_beta` over the whole
  prompt (task line, Options line, telemetry lines — so in arm C the snapshot's
  facts stay attached to the same *physical* route, now carrying the other
  label); then (2) reverse the presentation order of the two route labels in
  the Options line (wait keeps its position). Scoring mapping: label
  `tool_alpha` ↦ physical `tool_beta`, label `tool_beta` ↦ physical
  `tool_alpha`, `wait` ↦ `wait`.
- **ANON**: replace `tool_alpha` / `tool_beta` throughout by neutral codes
  `route-<letter><digit>` (letters from GHJKMNPQRT, digits 2–9), drawn per call
  with RNG seed 20261106, the physical-route↔code assignment itself randomised
  per call; option order and all facts unchanged from the original. The mapping
  is recorded per call in `call-specs.json` / `raw-results.json`.

## Decoding

Follows the archive's OpenAI-adapter preserved requests (the API family of this
run): single user message, `max_completion_tokens = 1024`, **temperature unset
(gateway default)** — the OpenAI and Anthropic preserved requests record no
temperature (only the Gemini adapter recorded 0.0). Repetitions are therefore
independent samples at the gateway default; this is a recorded protocol choice,
not an oversight. Model label requested: `gpt-6-luna` only.

## Parsing

The reply must be exactly one listed action label. Parse rule: strip
whitespace; if the reply is exactly one of the shown labels → that choice. Else
search the reply for whole-token occurrences of the shown labels; if exactly
one distinct label occurs → that choice. Otherwise (none, or ≥2 distinct
labels) → **unparseable**: scored as `wait` for regret (no dispatch happened),
completion = 0, and counted separately per block. Every raw reply is retained.

## Scoring (offline, frozen L0 oracle)

Scoring reuses the L0 frozen oracle verbatim (`observable_monitor_cost_v0.6`,
P = 10,000): route cost = latency_EWMA + failure_rate × 10,000 + 10,000 if
circuit OPEN; regret(action) = cost(action) − min cost; regret(wait) =
500 + 10,000 − best. The model's chosen label is first mapped back to the
physical route via the call's recorded mapping.

Completion (offline form of the paper's live-completion definition): choosing a
route whose canonical window is all-success (successes == window_n == 3)
completes; choosing a route with successes == 0 does not; `wait` and
unparseable do not. Pre-run check C2 (passed): this rule reproduces the
archived live `action-result` success flag for all 27 archived decisions, so it
is the paper's definition as realised in the archive, not a new invention.

No Toxiproxy / live transport is re-enacted: choices are scored against the
frozen canonical facts. The paper's live transport layer is out of scope for
this run (recorded scope note, per the authorisation amendment).

## Pre-registered metrics and verdict rules

### Replication block (REP), pooled per arm (n=9), bounded comparison to the
paper's pooled Study 2 (A 6,734.30 / B 8,956.37 / C 0.00 ms; completions 6/5/9).
Bounded because the populations differ: paper = 3 models × 1 instance each;
here = 1 gateway-labelled model × the same 3 instances per cell.

- **PATTERN_REPLICATED**: C mean regret ≤ 10% of B mean regret, C completions
  ≥ 8/9, and C mean < A mean.
- **PARTIAL_PATTERN**: C is the best arm on both mean regret and completions
  but misses a threshold above.
- **NOT_REPLICATED**: otherwise.

### Attribution probe (SWAP / ANON) — the L0 open question (ha-c7 / ha-c15)

Population S: A/B-arm calls on instances where physical tool_beta is the
unique canonical best (n=10 per treatment — the instances carrying 85.8% of the
paper's Study 2 A/B regret). Metrics:

- `default_REP` — share of S in REP choosing physical tool_alpha (= label
  tool_alpha). Paper pooled value: 10/10.
- `labelFollow_SWAP` — share of S in SWAP choosing the label `tool_alpha`
  (which there denotes physical tool_beta, the best route).
- `physFollow_SWAP` — share of S in SWAP choosing physical tool_alpha (there
  labelled `tool_beta`).
- `physDefault_ANON` — share of S in ANON choosing physical tool_alpha.
- `firstShare_T` — share over all A/B calls (n=18) in treatment T choosing the
  first-listed route in the Options line.
- `regret_S_T` — mean regret over S per treatment.
- C-arm integrity: mean regret of arm C per treatment; and `C_SWAP_badbeta`,
  mean regret over the 4 arm-C instances where physical tool_beta is the
  faulted/slow route under SWAP (there the faulted route carries the
  `tool_alpha` label: a content-reading model still scores ≈0, a
  label-defaulting model scores ≈20,000).

Verdict (first matching rule wins):

1. **LABEL_EFFECT_DOMINANT** — `labelFollow_SWAP` ≥ 0.7 AND
   `physDefault_ANON` ≤ `default_REP` − 0.3 AND `C_SWAP_badbeta` < 1,000 ms.
   Reading: the baseline default follows the alpha label string; anonymising
   destroys it; the snapshot (arm C content) is still read correctly under
   relabelling, so the A/B→C contrast partly prices the breaking of a label
   default.
2. **PHYSICAL_DEFAULT (label-independent)** — `physFollow_SWAP` ≥ 0.7 AND
   `physDefault_ANON` ≥ 0.7. Reading: choices track the physical alpha route
   despite relabelling and anonymisation; the default is not carried by the
   alpha/beta strings (position / mention-order candidates remain).
3. **POSITION_EFFECT** — `firstShare_T` ≥ 0.7 in all three treatments AND
   neither rule 1 nor 2 fires. Reading: choices follow presentation position.
4. **MIXED_OR_UNDECIDABLE** — anything else; metrics are reported without a
   forced attribution.

Thresholds are set against n=10 (0.7 = 7/10) and n=18; all shares are reported
with their counts so the reader can re-judge.

### Effect on the L0 composite verdict

L0 composite was PARTIAL with attribution unresolved. This run can move the
attribution component to DECIDED (rules 1–3) or leave it unresolved (rule 4);
it cannot change the L0 accounting or pricing-sensitivity results. The
replication block speaks to whether the paper's pooled pattern appears at all
in this single-model shape; it is not a re-run of the paper's three-model
panel and will not be described as one.

## Stop rules

- HTTP 429, quota/billing errors, or 3 consecutive failed calls → **stop
  immediately**, keep all completed calls (results are written incrementally),
  report the completed count and the stop reason. No model substitution, ever.
- A single transient network error on one call → retry that call once.
- One minimal smoke call to `gpt-6-luna` precedes the run and is not analysed.

## Files

- `call-specs.json` — the 81 specs (prompts, mappings, facts) built by
  `code/live-l2/scripts/prep_specs.py`. The specs file is not redistributed in
  this package (it embeds the authors' archived prompt texts); regenerate it
  from the authors' archive. The checks report ships as
  `results/live/prep-report.json` (checks C1/C2/C3).
- `raw-results.json` — one record per call (written incrementally); shipped
  here as `results/live/per-instance-results.json` with prompt texts removed.
- `analysis.md` — analysis write-up (`results/live/analysis.md`); the receipt
  is `run-receipt.md` in this package.
