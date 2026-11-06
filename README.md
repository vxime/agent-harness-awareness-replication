# Agent Harness Awareness — Replication & Audit Package

Replication materials for the article
《Agent 工具健康快照复测：−96.9% Regret 里约 29 个百分点来自定价，基线 98.9% 压在默认路线上》
("Re-testing the agent tool-health snapshot: about 29 points of the −96.9%
regret reduction are pricing, and 98.9% of baseline regret sits on one
default route"), published on [vxi.me](https://vxi.me).

The article audits the tool-health snapshot claims of:

> Manu Agrawal & Shrey Nagpal, *Agent Harness Awareness: Turning Verified
> Telemetry into Operational Control for Tool-Using Agents*,
> arXiv:2611.05391v1 (submitted 2026-09-13, announced 2026-11-05).

The paper argues that tool-using agents suffer "operational blindness": the
host knows each tool route's current health (latency EWMA, failure rate,
circuit state) but the deciding model does not, so the paper feeds the model
a host-verified Substrate State Telemetry (SST) snapshot inside the call
envelope. Its headline: in Study 1 (216 decisions), moving from a
neutral-envelope baseline (arm B) to the snapshot arm (arm C) cuts mean
dispatch regret from 4,251.54 ms to 131.12 ms (−96.9%); in the live Study 2
(27 decisions), B→C cuts regret from 8,956.37 ms to exactly 0.

Uniquely among the papers this series audits, the authors ship a **frozen
public evaluation archive** (`manu2/scac-dynamic-agent-harness`, pinned at
commit `d98e3610e880ab06421b4e53bb0cd892c1b19170`) whose retained artifacts
recompute every headline number **offline, at zero API cost**. That made a
two-tier audit possible: an exact offline recomputation (L0), and a small
live subset (L2) that replays Study 2's shape and adds a label probe the
paper itself did not run.

## What was run

**L0 — offline archive audit** (`code/offline-audit/`, zero model calls).
Every retained decision (243 = 216 + 27) was recomputed from its raw
host/snapshot quantities with the authors' frozen observable oracle, and
cross-checked against the authors' own analysis scripts.

- **Accounting: REPRODUCED, strongest form.** All 243 recomputed regrets
  equal the recorded `policy_regret` exactly (max abs diff 0.0); both
  headline tables match the paper at published precision
  (`results/evidence/recomputation-diff.json`).
- **Pricing sensitivity: CONFIRMED AND QUANTIFIED.** Regret is a
  *constructed* cost carrying two frozen 10,000 ms penalty constants.
  Repricing at 5,000 / 1,000 ms moves the Study 1 B→C reduction
  96.9% → 89.8% → 67.8% — **about 29 percentage points of the headline are
  penalty pricing**. The effect itself survives all three pricings, and the
  completion-rate contrast (69.4% → 95.8%) does not depend on pricing at
  all (`results/evidence/pricing-sensitivity.json`).
- **Label concentration: STRONGER than the paper's own framing.** In Study 1
  arms A/B, of the 78 decisions where the canonical best route is uniquely
  beta, 75 chose alpha — carrying **98.9%** of total A/B regret (arm B
  alone: 100.0%). The paper's "17/18 (94.4%)" figure describes Study 2,
  where the pattern also holds (10/10, 85.8% of A/B regret).

**L2 — live subset** (`code/live-l2/`, 81 calls, protocol frozen before the
first call). The paper's model trio (GPT-5.6 Sol / Claude Sonnet 5 / Gemini
3.7 Flash) could not be assembled on the gateway available to the lab — it
lists no Claude or Gemini label — so, as a recorded substitution, all 81
calls used **one OpenAI-compatible gateway endpoint labelled `gpt-6-luna`**
(underlying identity unverifiable; every L2 reading is bounded to that
label). Design: Study 2's 3 arms × 3 regimes, each cell filled by its 3
archived episode instances — a 27-call replication block, plus a 54-call
label probe (SWAP: route labels exchanged; ANON: labels anonymised per
episode). Scoring is offline against the L0 frozen oracle; the paper's
Toxiproxy/OTel transport layer was **not** re-enacted.

- **Replication: PATTERN_REPLICATED.** Arm A 6,734.30 ms / 6/9 and arm C
  0.00 ms / 9/9 match the paper exactly; arm B 6,734.02 ms / 6/9 vs the
  paper's 8,956.37 / 5/9, the entire gap traced to one archived instance
  (a single 20,001.09 ms miss) this endpoint did not repeat. Per-instance
  agreement with the archive: 26/27.
- **Probe: formal verdict MIXED_OR_UNDECIDABLE, with a decisive
  sub-finding.** On the subset where beta is uniquely best (n=10 per
  treatment): the original presentation chose physical alpha 10/10 (subset
  mean regret 12,121.49 ms); under SWAP the choices followed the
  `tool_alpha` **string** 10/10 — flipping physical route — and subset
  regret fell to exactly 0.00; under ANON physical alpha was still chosen
  10/10, per-instance identical to the original. Arm C scored 0.00 under
  all three treatments, including the 4 SWAP instances where the label
  default pointed at the faulty route.
- **Bounded interpretation.** A *pure information-absence* reading of the
  baseline regret is **excluded**: the baseline default is deterministic
  and per-instance predictable — a *presentation default* with a confirmed
  label-identity cue, plus a candidate positional cue (narrative first
  mention) that this design did not separate (ANON preserved mention
  order). The verified snapshot overrides the default in arm C. Formal
  attribution stays undecided on that residue.

**Composite verdict: PARTIAL** — every pre-registered question is answered
except the first-mention residue of the attribution question. Full numbers,
deviations (L0: D1–D3; L2: D-L2-1…D-L2-5) and limitations are in
`run-receipt.md`; every claim is mapped in `claim-status-table.md`.

**Not run**: a live replication of Study 1 (offline-audited only); the
paper's three-model panel (unavailable, see above); any order-permuted
ANON variant (outside the approved 81-call protocol); the paper's
transport layer.

## 中文摘要

本包是博客文章《Agent 工具健康快照复测：−96.9% Regret 里约 29 个百分点来自定价，基线 98.9% 压在默认路线上》的公开复现材料，审计对象为 Agrawal 与 Nagpal 的工具健康快照（SST）论文（arXiv:2611.05391v1）。验证分两级：L0 零调用离线审计把作者冻结档案的全部 243 个决策逐个复算，与记录值精确相等（最大差 0.0），并量化了头条数字的定价敏感性——惩罚常数从 10,000 ms 降到 1,000 ms 时，Study 1 的 B→C 降幅由 96.9% 缩到 67.8%，约 29 个百分点来自定价；同时一手测得基线 regret 高度集中于「beta 最优却选了 alpha」的决策（承载 A/B 总 regret 的 98.9%）。L2 活体子集因网关上凑不齐论文的三模型面板，按记录在案的替换口径，用单一网关标注端点 gpt-6-luna 跑完 81 次调用（Study 2 形状复刻 27 次 + 标签探针 54 次）：复刻块模式复现（A/C 与论文一致，B 的差距全部来自归档实例的一次失误未被重蹈）；探针的正式判读为 MIXED_OR_UNDECIDABLE，但「纯信息缺失」读法被排除——基线默认是可逐实例预测的呈现默认（标签身份线索已证，首次提及线索只是候选、未分离），已验证快照在三种呈现下都能压过它（C 臂 regret 恒为 0.00）。复合判读为 PARTIAL。离线部分可按下方说明零 API 成本完整复算。

## Layout

- `PROTOCOL.md` — the frozen protocols: Part 1, the L0 audit protocol
  (two independent recomputation paths, repricing, concentration
  measurement); Part 2, the L2 pre-registered protocol (design, prompt
  provenance, transformations, scoring, verdict rules, stop rules)
- `run-receipt.md` — the two run receipts merged (L0 + L2), public edition:
  all numbers, verdicts, deviations and limitations
- `claim-status-table.md` — every article claim (ha-c1…ha-c17) mapped to
  its evidence grade and post-test status
- `code/offline-audit/scripts/` — `offline_audit.py` (the L0 recomputation)
  and `export_recomputation_diff.py` (regenerates the per-decision diff)
- `code/live-l2/scripts/` — `prep_specs.py` (builds the 81 call specs and
  the C1–C3 pre-run checks), `run_l2.py` (the runner), `analyze_l2.py`
  (pre-registered metrics and verdict rules)
- `results/offline/` — the audit's `results.json` and the recompute /
  sensitivity tables
- `results/live/` — `analysis-metrics.json`, the analysis write-up,
  `prep-report.json`, and `per-instance-results.json` (all 81 calls;
  prompt texts removed — see below)
- `results/evidence/` — `recomputation-diff.json` (all 243 decisions:
  recorded vs recomputed regret) and `pricing-sensitivity.json`
  (the three-pricing matrix)

## Reproducing

### L0 — offline, zero API cost

You need only Python 3 (standard library) and a clone of the authors'
archive:

```bash
git clone https://github.com/manu2/scac-dynamic-agent-harness archive
git -C archive checkout d98e3610e880ab06421b4e53bb0cd892c1b19170
export SST_ARCHIVE_DIR=$PWD/archive

python3 code/offline-audit/scripts/offline_audit.py
# writes results.json, recompute-table.md, regret-sensitivity-table.md
# into code/offline-audit/

python3 code/offline-audit/scripts/export_recomputation_diff.py
# writes results/evidence/recomputation-diff.json
# (243 decisions; expect max_abs_diff_ms = 0.0, n_exact = 243)
```

### L2 — live subset (needs your own API access)

The runner talks to any OpenAI-compatible endpoint. The recorded run used
a gateway endpoint labelled `gpt-6-luna`; a different endpoint is a
different run, not a reproduction of this one.

```bash
export SST_ARCHIVE_DIR=$PWD/archive
export SST_API_KEY=...            # your key; read from the environment only
export SST_BASE_URL=...           # optional; default https://api.openai.com/v1
export SST_MODEL_LABEL=gpt-6-luna # optional; the label to request
pip install openai

python3 code/live-l2/scripts/prep_specs.py   # writes call-specs.json + prep-report.json into code/live-l2/
python3 code/live-l2/scripts/run_l2.py       # 81 calls; writes raw-results.json incrementally
python3 code/live-l2/scripts/analyze_l2.py   # writes analysis-metrics.json into code/live-l2/
```

Notes on shipped data:

- `results/live/per-instance-results.json` carries every per-call field of
  the recorded run **except the prompt texts**. The prompts are the
  archive's preserved Study 2 provider requests — third-party content that
  lives in the authors' archive and is regenerated locally by
  `prep_specs.py` (checks C1–C3 in `results/live/prep-report.json` passed:
  prompt provenance verified 27/27, the offline completion rule reproduces
  the archived live success flags 27/27). For the same reason,
  `call-specs.json` is not redistributed here.
- The authors' own analysis scripts are not redistributed either; L0 path
  (a) used them from the archive at the pinned commit, and path (b) —
  the self-contained recomputation in `code/offline-audit/` — is the
  reproducible one. (The Study 2 author script needed a copy with exactly
  two output-path constants changed to run against a read-only clone;
  deviation D2 in `run-receipt.md`.)
- Internal working notes and run logs of the lab are not part of this
  package; everything they fed into is preserved in the receipts, the
  analysis write-up and the result files above.

## Boundaries

All L2 readings are bounded to one gateway-labelled endpoint
(`gpt-6-luna`, underlying identity unverifiable), one run at
gateway-default decoding, and the archived Study 2 instance set
(n = 9 per arm, n = 10 on the probe subset). Study 1 was audited offline
only. The first-mention cue is a candidate, not an established mechanism;
the formal attribution verdict is MIXED_OR_UNDECIDABLE. The paper's
numbers on its own three-model panel are neither confirmed nor refuted
beyond what the receipts state.

## Relationship to the paper and license

This package is an independent audit. The audited paper and the authors'
evaluation archive remain © their authors; this package contains no text
or data from them beyond short numeric citations, the archive's decision
identifiers, and derived per-decision comparisons. Our own code, receipts
and analysis are released under the MIT License (see `LICENSE`).
Copyright (c) 2026 vxime.
