# L2 live subset — analysis (2026-11-06)

Run: 81/81 calls completed, 0 failures, 0 retries (max attempts = 1), no stop
rule triggered. Model: an OpenAI-compatible gateway endpoint labelled `gpt-6-luna` only (response model field
confirms `gpt-6-luna` on all 81). Window 2026-11-06T07:59:55Z–08:03:20Z.
All 81 replies parsed exactly (no token-search fallbacks, no unparseable, no
`wait` choices). Scoring: frozen L0 oracle, P = 10,000, offline against each
instance's archived canonical facts (see `PROTOCOL.md`). Machine-readable
metrics: `analysis-metrics.json`; per-call records: `per-instance-results.json`.

Population note (bounded comparison): the paper's pooled Study 2 is 3 models ×
1 instance per cell; this run is 1 gateway-labelled model × the same 3 archived
instances per cell. Pooled per-arm n = 9 in both. Nothing below is a re-run of
the paper's three-model panel.

## 1. Replication block (REP) vs the paper's pooled Study 2

| Arm | This run: mean regret (ms) | Paper pooled | This run: completions | Paper |
|---|---|---|---|---|
| A | 6,734.30 | 6,734.30 | 6/9 | 6/9 |
| B | 6,734.02 | 8,956.37 | 6/9 | 5/9 |
| C | 0.00 | 0.00 | 9/9 | 9/9 |

**Verdict (pre-registered rule): PATTERN_REPLICATED** — C mean regret (0.00) ≤
10% of B mean, C completions 9/9 ≥ 8/9, C mean < A mean.

Detail behind the pooled numbers:

- Our model's physical choices agree with the archived decision of the same
  instance in **26/27** REP calls (A 9/9, B 8/9, C 9/9). Arm A is
  decision-identical to the paper's pooled arm A, which is why its mean
  matches to the cent.
- The single disagreement is `gpt-07-connection-b` (arm B): the archived
  GPT-5.6 Sol decision chose the faulted `tool_beta` (regret 20,001.09);
  `gpt-6-luna` chose `tool_alpha` (regret 0). That one archived blunder is
  exactly the B-arm gap: paper B sum − our B sum = 20,001.09 + rounding.
- In arm C the model picked the canonical best route in all 9 instances —
  regret exactly 0.00, as in the paper.

## 2. Attribution probe — pre-registered verdict: **MIXED_OR_UNDECIDABLE**

Population S = A/B calls on instances where physical `tool_beta` is the unique
canonical best (n = 10 per treatment; the instances carrying 85.8% of the
paper's Study 2 A/B regret).

| Metric (protocol §) | REP | SWAP | ANON |
|---|---|---|---|
| Chose physical tool_alpha on S | **10/10** (`default_REP`) | 0/10 (`physFollow_SWAP`) | **10/10** (`physDefault_ANON`) |
| Chose label `tool_alpha` on S | 10/10 | **10/10** (`labelFollow_SWAP`) | — (no such label) |
| Mean regret on S (ms) | 12,121.49 | **0.00** | 12,121.49 |
| Chose first-listed option, all A/B (n=18) | 10/18 | 12/18 | 12/18 |
| Arm C mean regret (ms) | 0.00 | 0.00 | 0.00 |
| C on beta-faulted instances under SWAP (n=4) | — | **0.00** (`C_SWAP_badbeta`) | — |

Rule application (first match wins, as frozen in the protocol):

1. LABEL_EFFECT_DOMINANT — requires `physDefault_ANON` ≤ 0.7. It is 1.0.
   **Does not fire**, despite `labelFollow_SWAP` = 10/10 and
   `C_SWAP_badbeta` = 0.00 both pointing at the label.
2. PHYSICAL_DEFAULT — requires `physFollow_SWAP` ≥ 0.7. It is 0/10. No.
3. POSITION_EFFECT — requires first-listed share ≥ 0.7 in all treatments.
   Shares are 0.56 / 0.67 / 0.67. No.
4. → **MIXED_OR_UNDECIDABLE.**

### What the probe did decide (descriptive, instance-matched)

The formal verdict is "mixed" because the two probe treatments expose **two
different surface cues**, each sufficient to carry the default on its own:

- **The label string dominates when present.** Under SWAP, choices on S follow
  the string `tool_alpha` 10/10 — onto the *other physical route* — and S
  regret collapses from 12,121.49 to exactly 0.00. On alpha-best instances the
  same string-following costs regret instead (see arm means below). The model
  is not reading anything physical in arms A/B; it is following the label.
- **Anonymisation does not remove the default.** Under ANON, choices on S land
  on physical `tool_alpha` 10/10 and S regret is *instance-identical* to REP
  (same 10 values). With the alpha/beta strings gone, the surviving cue is the
  narrative order: by construction (string replacement), the prompt always
  introduces the physical alpha route first ("route-X and route-Y expose the
  same read-only record API"), and in arm B its telemetry line also stays
  first. On S the model picked the first-introduced route's code 10/10 —
  including the 2 cases per arm where that code was listed *second* in the
  Options line — so it is not an Options-position effect.
- **In SWAP the two cues conflict and the string wins.** The swapped task line
  introduces `tool_beta` (= physical alpha) first, yet the model chose the
  `tool_alpha` string 10/10 on S.
- **Arm C reads content under every treatment.** C regret is exactly 0.00 in
  all 27 C calls, including the 4 SWAP instances where the faulted route
  carries the `tool_alpha` label (`C_SWAP_badbeta` = 0.00; the model chose
  `tool_beta` = the healthy physical route, following the snapshot's facts
  over the label default). Whatever drives the A/B default does not survive
  the presence of the verified snapshot.

Full arm means across treatments (mean regret ms / completions of 9):

| Treatment | A | B | C |
|---|---|---|---|
| REP | 6,734.30 / 6 | 6,734.02 / 6 | 0.00 / 9 |
| SWAP | 6,700.95 / 6 | 2,255.76 / 8 | 0.00 / 9 |
| ANON | 8,956.48 / 5 | 8,956.20 / 5 | 0.00 / 9 |

Exceptions worth naming: in SWAP arm B, two connection instances
(`gemini-07`, `gpt-07`) broke the string default and chose label `tool_beta`
(= best physical alpha, regret 0) — the only 2 of 18 SWAP A/B calls not
choosing the `tool_alpha` label. In ANON, two http instances (`sonnet-01` arm
A, `sonnet-04` arm B) chose the physical beta route's code where beta was
faulted (regret ≈ 20,000 each) — in both, beta's code was first-listed in the
Options line; these are the only 2 of 18 ANON A/B calls not choosing physical
alpha. With a stochastic gateway default temperature, 16/18 vs 18/18 should
not be over-read.

### Reading for the article (bounded to this run)

- The L0 open question was "label effect or information absence?" The probe
  rules that pair too coarse and returns MIXED by design. But a narrower claim
  **is** decided: the baseline default is **not** what ignorance alone
  produces. An indifferent chooser under ignorance would split roughly evenly;
  instead the choice is perfectly predictable from presentation cues in all
  three treatments (string → flipped physical choice; anonymised → same
  physical choice as REP, instance for instance). Baseline regret in A/B is a
  **systematic presentation default** — carried by the label string when
  labels are meaningful, and by narrative first-mention when they are not.
- Consequently the A/B→C contrast in the paper measures, in part, the value of
  breaking that presentation default with verified facts — and arm C here
  shows the snapshot does break it even when the label default is pointed at
  the faulted route (SWAP C). This *strengthens* the snapshot's mechanism
  claim while *reframing* the baseline: the 6,734–8,956 ms of baseline regret
  is not "the cost of missing information" in the abstract; it is the cost of
  a default that any truthful envelope happens to override.
- Bounds: one gateway-labelled model, one run at gateway-default decoding,
  n = 9–10 per population, the paper's own 3 regimes and instances. The
  two-cue decomposition (string vs first-mention) is descriptive of this run;
  separating first-mention from any residual physical cue would need an ANON
  variant that also permutes narrative order, which this protocol did not
  include (see the deviations in `run-receipt.md`).

## 3. Cost

Measured usage over the 81 analysis calls: 17,844 prompt + 2,937 completion =
20,781 tokens. At the third-party tracked prices previously recorded for this label (input $0.20/M, output $1.20/M) that is ≈ **US$0.007** —
under one cent. This is an estimate from tracked prices, not a gateway bill.
(The 1 pre-run smoke call used 16 tokens and is excluded.)
