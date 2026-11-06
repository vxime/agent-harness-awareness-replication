#!/usr/bin/env python3
"""L2 analysis: applies protocol.md's pre-registered metrics and verdict rules
to raw-results.json; writes ../analysis-metrics.json and ../analysis.md.
No model calls."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve()
L2_DIR = HERE.parents[1]
sys.path.insert(0, str(HERE.parents[2] / "offline-audit" / "scripts"))
from offline_audit import regret_under_p  # noqa: E402

ARCHIVE = Path(os.environ.get("SST_ARCHIVE_DIR", HERE.parents[3] / "archive"))
S2_ROOT = ARCHIVE / "experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport"
PAPER = {"A": (6734.30, 6), "B": (8956.37, 5), "C": (0.00, 9)}


def share(rs, pred):
    return (sum(1 for r in rs if pred(r)), len(rs))


def main() -> None:
    state = json.loads((L2_DIR / "raw-results.json").read_text())
    recs = state["records"]
    ok = [r for r in recs if r["status"] == "ok"]
    specs = {(s["treatment"], s["episode_id"], s["arm"]): s
             for s in json.loads((L2_DIR / "call-specs.json").read_text())}

    def best_of(r):
        _, det = regret_under_p(specs[(r["treatment"], r["episode_id"], r["arm"])]["tools"],
                                "wait", 10_000)
        return det["best_actions"]

    archived = {}
    for d in S2_ROOT.iterdir():
        if (d / "manifest.json").exists():
            man = json.loads((d / "manifest.json").read_text())
            if man.get("provider_run", {}).get("episode_id"):
                archived[man["provider_run"]["episode_id"]] = json.loads(
                    (d / "model-decision.json").read_text())["selected_action"]

    m: dict = {}
    m["n_records"] = len(recs)
    m["n_ok"] = len(ok)
    m["n_failed"] = len(recs) - len(ok)
    m["stopped_reason"] = state["meta"]["stopped_reason"]
    m["parse_counts"] = {p: sum(1 for r in ok if r["parse"] == p)
                         for p in ("exact", "token", "unparseable")}
    m["wait_choices"] = sum(1 for r in ok if r["chosen_physical"] == "wait")
    m["max_attempts"] = max(r["attempts"] for r in recs)
    m["response_models"] = sorted({r["response_model"] for r in ok})
    m["first_call_at"] = min(r["called_at"] for r in ok)
    m["last_call_at"] = max(r["called_at"] for r in ok)
    m["tokens"] = {
        "prompt": sum(r["usage"]["prompt_tokens"] for r in ok),
        "completion": sum(r["usage"]["completion_tokens"] for r in ok),
    }
    m["tokens"]["total"] = m["tokens"]["prompt"] + m["tokens"]["completion"]
    # reference third-party tracked prices for this label (see run-receipt.md)
    m["cost_usd_tracked_prices"] = (m["tokens"]["prompt"] * 0.20 / 1e6
                                    + m["tokens"]["completion"] * 1.20 / 1e6)

    # ---- REP block pooled
    m["rep"] = {}
    for arm in "ABC":
        sub = [r for r in ok if r["treatment"] == "REP" and r["arm"] == arm]
        m["rep"][arm] = {"mean_regret": mean(r["regret"] for r in sub),
                         "completions": sum(r["completion"] for r in sub), "n": len(sub),
                         "paper_mean": PAPER[arm][0], "paper_completions": PAPER[arm][1]}
    rep = m["rep"]
    if (rep["C"]["mean_regret"] <= 0.1 * rep["B"]["mean_regret"]
            and rep["C"]["completions"] >= 8 and rep["C"]["mean_regret"] < rep["A"]["mean_regret"]):
        m["rep_verdict"] = "PATTERN_REPLICATED"
    elif (rep["C"]["mean_regret"] == min(rep[a]["mean_regret"] for a in "ABC")
          and rep["C"]["completions"] == max(rep[a]["completions"] for a in "ABC")):
        m["rep_verdict"] = "PARTIAL_PATTERN"
    else:
        m["rep_verdict"] = "NOT_REPLICATED"
    m["rep_agreement_with_archived"] = {
        arm: share([r for r in ok if r["treatment"] == "REP" and r["arm"] == arm],
                   lambda r: archived[r["episode_id"]] == r["chosen_physical"])
        for arm in "ABC"}
    m["rep_agreement_with_archived"]["all"] = share(
        [r for r in ok if r["treatment"] == "REP"],
        lambda r: archived[r["episode_id"]] == r["chosen_physical"])

    # ---- all-treatment arm means
    m["arm_means"] = {}
    for t in ("REP", "SWAP", "ANON"):
        m["arm_means"][t] = {}
        for arm in "ABC":
            sub = [r for r in ok if r["treatment"] == t and r["arm"] == arm]
            m["arm_means"][t][arm] = {"mean_regret": mean(r["regret"] for r in sub),
                                      "completions": sum(r["completion"] for r in sub)}

    # ---- attribution
    S = {t: [r for r in ok if r["treatment"] == t and r["arm"] in ("A", "B")
             and best_of(r) == ["tool_beta"]] for t in ("REP", "SWAP", "ANON")}
    att: dict = {}
    att["n_S"] = {t: len(S[t]) for t in S}
    att["default_REP"] = share(S["REP"], lambda r: r["chosen_physical"] == "tool_alpha")
    att["labelFollow_SWAP"] = share(S["SWAP"], lambda r: r["chosen_label"] == "tool_alpha")
    att["physFollow_SWAP"] = share(S["SWAP"], lambda r: r["chosen_physical"] == "tool_alpha")
    att["physDefault_ANON"] = share(S["ANON"], lambda r: r["chosen_physical"] == "tool_alpha")
    att["regret_S"] = {t: mean(r["regret"] for r in S[t]) for t in S}
    att["firstShare"] = {}
    for t in ("REP", "SWAP", "ANON"):
        ab = [r for r in ok if r["treatment"] == t and r["arm"] in ("A", "B")]
        att["firstShare"][t] = share(ab, lambda r: r["chosen_label"] == r["shown_options"][0])
    badbeta = [r for r in ok if r["treatment"] == "SWAP" and r["arm"] == "C"
               and r["faulted_tool"] == "tool_beta"]
    att["C_SWAP_badbeta"] = {"n": len(badbeta),
                             "mean_regret": mean(r["regret"] for r in badbeta)}
    att["C_mean_regret"] = {t: m["arm_means"][t]["C"]["mean_regret"] for t in ("REP", "SWAP", "ANON")}

    def frac(pair):
        return pair[0] / pair[1] if pair[1] else 0.0
    if (frac(att["labelFollow_SWAP"]) >= 0.7
            and frac(att["physDefault_ANON"]) <= frac(att["default_REP"]) - 0.3
            and att["C_SWAP_badbeta"]["mean_regret"] < 1000):
        att["verdict"] = "LABEL_EFFECT_DOMINANT"
    elif frac(att["physFollow_SWAP"]) >= 0.7 and frac(att["physDefault_ANON"]) >= 0.7:
        att["verdict"] = "PHYSICAL_DEFAULT (label-independent)"
    elif all(frac(att["firstShare"][t]) >= 0.7 for t in ("REP", "SWAP", "ANON")):
        att["verdict"] = "POSITION_EFFECT"
    else:
        att["verdict"] = "MIXED_OR_UNDECIDABLE"
    m["attribution"] = att

    (L2_DIR / "analysis-metrics.json").write_text(json.dumps(m, indent=1) + "\n")
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
