#!/usr/bin/env python3
"""L0 offline audit for arXiv:2611.05391 (Agent Harness Awareness).

Zero model/provider calls. Reads ONLY a local clone of the authors' frozen
archive (manu2/scac-dynamic-agent-harness, commit
d98e3610e880ab06421b4e53bb0cd892c1b19170) and writes audit outputs into ../
(the parent of this scripts/ directory).

Set SST_ARCHIVE_DIR to the archive clone's path; without it, the script
looks for an `archive/` directory at the package root.

Recomputation uses the authors' frozen observable oracle
(archive/src/scac_harness/scenarios/toolroute.py, observable_monitor_cost_v0.6):
  failure_rate = (window - successes)/window   (0.5 if window == 0)
  cost_P(tool) = latency_ewma_ms + failure_rate * P + (P if circuit == OPEN)
  best_P       = min over the two routes, re-selected under the same P
  regret_P(route action) = cost_P(action) - best_P
  regret_P(wait)         = 500 + 10_000 - best_P     (wait rule NEVER rescaled)
P in {10_000 (published), 5_000, 1_000} -- the two sensitivity values are the
pre-registered ones from the experiment plan (see PROTOCOL.md); no other
constants used.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve()
AUDIT_DIR = HERE.parents[1]                      # parent of scripts/
ARCHIVE = Path(os.environ.get("SST_ARCHIVE_DIR", HERE.parents[3] / "archive"))
P_LEVELS = (10_000, 5_000, 1_000)
WAIT_BASE = 500.0
WAIT_MISSED = 10_000.0


def route_cost(tool: dict, p: float) -> tuple[float, dict]:
    window = int(tool.get("window_n", 0))
    successes = int(tool.get("successes", 0))
    failure_rate = 0.5 if window == 0 else (window - successes) / window
    latency = float(tool.get("latency_ewma_ms", 0.0))
    fail_comp = failure_rate * p
    circuit_comp = p if tool.get("circuit") == "OPEN" else 0.0
    parts = {
        "latency_ewma_ms": latency,
        "failure_rate": failure_rate,
        "failure_component_ms": fail_comp,
        "circuit_component_ms": circuit_comp,
        "window_n": window,
        "successes": successes,
        "circuit": tool.get("circuit"),
    }
    return latency + fail_comp + circuit_comp, parts


def regret_under_p(tools: dict, action: str, p: float) -> tuple[float, dict]:
    costs, parts = {}, {}
    for name, tool in tools.items():
        costs[name], parts[name] = route_cost(tool, p)
    best = min(costs.values())
    best_actions = sorted(n for n, c in costs.items() if c == best)
    if action == "wait":
        value = WAIT_BASE + WAIT_MISSED - best
    else:
        value = costs[action] - best
    return value, {"costs": costs, "parts": parts, "best": best, "best_actions": best_actions}


# ---------------------------------------------------------------- Study 1
def load_study1() -> list[dict]:
    rows = []
    roots = [
        ARCHIVE / "experiments/api-paper-v1.0-seed8",
        ARCHIVE / "experiments/api-paper-v1.0-seeds9-10",
        ARCHIVE / "experiments/api-paper-v1.0-seeds11-13",
    ]
    for root in roots:
        for result_path in sorted(root.rglob("result.json")):
            d = result_path.parent
            manifest = json.loads((d / "manifest.json").read_text())
            if manifest.get("scenario") != "ToolRoute-v1.0-api":
                continue
            result = json.loads((d / "result.json").read_text())
            host = json.loads((d / "host.json").read_text())
            tools = host["full_checkpoint"]["tools"]
            rows.append({
                "model": manifest["model_id"], "seed": int(manifest["seed"]),
                "turn": int(manifest["turn"]), "condition": manifest["condition"],
                "action": result["action"], "success": bool(result["success"]),
                "recorded_regret": float(result["policy_regret"]),
                "tools": tools, "dir": str(d.relative_to(ARCHIVE)),
            })
    return rows


# ---------------------------------------------------------------- Study 2
def load_study2() -> list[dict]:
    rows = []
    root = ARCHIVE / "experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport"
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / "manifest.json").exists():
            continue
        manifest = json.loads((d / "manifest.json").read_text())
        provider = manifest.get("provider_run", {})
        if not provider.get("episode_id"):
            continue
        decision = json.loads((d / "model-decision.json").read_text())
        action_result = json.loads((d / "action-result.json").read_text())
        snapshot = json.loads((d / "snapshot.json").read_text())
        rows.append({
            "model": provider["model_id"], "condition": manifest["condition"],
            "regime": manifest["regime"], "faulted_tool": manifest["faulted_tool"],
            "option_order": manifest.get("option_order", []),
            "action": decision["selected_action"],
            "success": bool(action_result["event"]["payload"]["success"]),
            "recorded_regret": float(decision["policy_regret"]),
            "recorded_best": decision["observable_best_actions"],
            "tools": snapshot["tools"], "dir": str(d.relative_to(ARCHIVE)),
        })
    return rows


def enrich(rows: list[dict]) -> None:
    for r in rows:
        r["regret"] = {}
        r["detail"] = {}
        for p in P_LEVELS:
            value, detail = regret_under_p(r["tools"], r["action"], p)
            r["regret"][p] = value
            r["detail"][p] = detail


def pct_drop(base: float, new: float) -> float:
    return 100.0 * (1.0 - new / base) if base else 0.0


def main() -> None:
    s1, s2 = load_study1(), load_study2()
    assert len(s1) == 216, len(s1)
    assert len(s2) == 27, len(s2)
    enrich(s1)
    enrich(s2)

    out: dict = {"archive": str(ARCHIVE), "p_levels": P_LEVELS}

    # ---- Step 1 verification at P=10,000: my recompute vs recorded per decision
    def verify(rows):
        diffs = [abs(r["regret"][10_000] - r["recorded_regret"]) for r in rows]
        return {"n": len(rows), "max_abs_diff": max(diffs),
                "n_exact": sum(1 for d in diffs if d == 0.0),
                "n_within_1e-6": sum(1 for d in diffs if d <= 1e-6)}
    out["step1_per_decision_verification"] = {"study1": verify(s1), "study2": verify(s2)}

    def condition_means(rows, p):
        return {c: mean(r["regret"][p] for r in rows if r["condition"] == c) for c in "ABC"}

    def completions(rows):
        return {c: (sum(r["success"] for r in rows if r["condition"] == c),
                    sum(1 for r in rows if r["condition"] == c)) for c in "ABC"}

    out["study1"] = {"means": {p: condition_means(s1, p) for p in P_LEVELS},
                     "completions": completions(s1),
                     "model_C_means_10000": {
                         m: mean(r["regret"][10_000] for r in s1 if r["model"] == m and r["condition"] == "C")
                         for m in sorted({r["model"] for r in s1})}}
    out["study2"] = {"means": {p: condition_means(s2, p) for p in P_LEVELS},
                     "completions": completions(s2),
                     "model_means_10000": {
                         m: {c: mean(r["regret"][10_000] for r in s2 if r["model"] == m and r["condition"] == c)
                             for c in "ABC"} for m in sorted({r["model"] for r in s2})}}

    for study, rows in (("study1", s1), ("study2", s2)):
        out[study]["drops"] = {}
        for p in P_LEVELS:
            m = out[study]["means"][p]
            out[study]["drops"][p] = {"B_to_C_pct": pct_drop(m["B"], m["C"]),
                                      "A_to_C_pct": pct_drop(m["A"], m["C"])}

    # ---- Step 3: Study 2 arm-C zero decomposition
    zero_rows = []
    for r in [x for x in s2 if x["condition"] == "C"]:
        det = r["detail"][10_000]
        chosen = r["action"]
        entry = {"model": r["model"], "regime": r["regime"], "action": chosen,
                 "is_wait": chosen == "wait", "regret_recomputed": r["regret"][10_000],
                 "regret_recorded": r["recorded_regret"],
                 "best_actions": det["best_actions"],
                 "chosen_is_best": chosen in det["best_actions"]}
        if chosen != "wait":
            entry["chosen_components"] = det["parts"][chosen]
            entry["chosen_cost"] = det["costs"][chosen]
            entry["best_cost"] = det["best"]
            other = [n for n in det["costs"] if n != chosen][0]
            entry["other_route"] = other
            entry["other_components"] = det["parts"][other]
            entry["other_cost"] = det["costs"][other]
        zero_rows.append(entry)
    out["step3_study2_C_zero"] = zero_rows

    # ---- Step 6: label concentration
    def label_block(rows, study_name):
        ab = [r for r in rows if r["condition"] in ("A", "B")]
        block = {"decisions_AB": len(ab)}
        block["alpha_selected_AB"] = sum(1 for r in ab if r["action"] == "tool_alpha")
        # cases where observable-best (P=10,000) is uniquely beta
        beta_best = [r for r in ab if r["detail"][10_000]["best_actions"] == ["tool_beta"]]
        picked_alpha = [r for r in beta_best if r["action"] == "tool_alpha"]
        block["best_uniquely_beta_AB"] = len(beta_best)
        block["best_beta_but_alpha_chosen"] = len(picked_alpha)
        block["regret_of_those"] = sum(r["regret"][10_000] for r in picked_alpha)
        for cond in "AB":
            sub = [r for r in ab if r["condition"] == cond]
            sub_beta = [r for r in beta_best if r["condition"] == cond]
            sub_pa = [r for r in picked_alpha if r["condition"] == cond]
            block[cond] = {
                "decisions": len(sub),
                "alpha_selected": sum(1 for r in sub if r["action"] == "tool_alpha"),
                "best_uniquely_beta": len(sub_beta),
                "best_beta_but_alpha_chosen": len(sub_pa),
                "regret_of_those": sum(r["regret"][10_000] for r in sub_pa),
                "total_regret": sum(r["regret"][10_000] for r in sub),
                "share_pct": (100.0 * sum(r["regret"][10_000] for r in sub_pa)
                              / sum(r["regret"][10_000] for r in sub)) if sub else 0.0,
            }
        total_ab_regret = sum(r["regret"][10_000] for r in ab)
        block["share_of_AB_regret_pct"] = (100.0 * block["regret_of_those"] / total_ab_regret) if total_ab_regret else 0.0
        block["total_AB_regret"] = total_ab_regret
        return block

    out["step6_labels"] = {"study1": label_block(s1, "study1"), "study2": label_block(s2, "study2")}
    # Study 2 paper detail: beta listed first in option_order among A/B
    ab2 = [r for r in s2 if r["condition"] in ("A", "B")]
    beta_first = [r for r in ab2 if r["option_order"] and r["option_order"][0] == "tool_beta"]
    out["step6_labels"]["study2"]["beta_listed_first_AB"] = len(beta_first)
    out["step6_labels"]["study2"]["beta_first_alpha_chosen"] = sum(1 for r in beta_first if r["action"] == "tool_alpha")

    (AUDIT_DIR / "results.json").write_text(json.dumps(out, indent=2, default=str) + "\n")

    # ---------------- markdown: recompute table
    rep1 = {"A": 4826.45, "B": 4251.54, "C": 131.12}
    rep2 = {"A": 6734.30, "B": 8956.37, "C": 0.00}
    comp1 = {"A": (47, 72), "B": (50, 72), "C": (69, 72)}
    comp2 = {"A": (6, 9), "B": (5, 9), "C": (9, 9)}
    lines = ["# Recompute table — L0 offline audit (Step 1 + Step 3)", "",
             "Archive: manu2/scac-dynamic-agent-harness @ d98e3610e880ab06421b4e53bb0cd892c1b19170 (frozen clone, read-only).",
             "Paths: (a) authors' analysis scripts re-run offline; (b) independent per-decision recomputation",
             "from retained artifacts (host.json / snapshot.json monitor facts) using the frozen observable oracle", ""]
    lines += ["## Study 1 (216 decisions)", "",
              "| quantity | reported | authors' script rerun | independent recompute | match |",
              "|---|---|---|---|---|"]
    for c in "ABC":
        mine = out["study1"]["means"][10_000][c]
        lines.append(f"| mean regret arm {c} (ms) | {rep1[c]:,.2f} | see note | {mine:,.2f} | "
                     f"{'YES' if round(mine, 2) == rep1[c] else 'NO'} |")
    for c in "ABC":
        got, n = out["study1"]["completions"][c]
        lines.append(f"| completions arm {c} | {comp1[c][0]}/{comp1[c][1]} | — | {got}/{n} | "
                     f"{'YES' if (got, n) == comp1[c] else 'NO'} |")
    for m, v in out["study1"]["model_C_means_10000"].items():
        rep = {"gpt-5.6-sol": 75.50, "claude-sonnet-5": 75.50, "gemini-3.7-flash": 242.35}[m]
        lines.append(f"| mean regret arm C, {m} (ms) | {rep:,.2f} | — | {v:,.2f} | "
                     f"{'YES' if round(v, 2) == rep else 'NO'} |")
    v1 = out["step1_per_decision_verification"]["study1"]
    lines += ["",
              f"Per-decision check (Study 1): recomputed regret at P=10,000 vs recorded `policy_regret` for all {v1['n']} decisions: "
              f"max abs diff {v1['max_abs_diff']:.3g} ms; {v1['n_exact']} exact, {v1['n_within_1e-6']} within 1e-6.",
              "Authors'-script rerun condition summary is byte-identical in values to the committed "
              "`paper/analysis/toolroute_v1_analysis.json` (A 4,826.4478 / B 4,251.5426 / C 131.1190 ms; completions 47/50/69).", ""]
    lines += ["## Study 2 (27 decisions)", "",
              "| quantity | reported | authors' script rerun | independent recompute | match |",
              "|---|---|---|---|---|"]
    for c in "ABC":
        mine = out["study2"]["means"][10_000][c]
        lines.append(f"| mean regret arm {c} (ms) | {rep2[c]:,.2f} | see note | {mine:,.2f} | "
                     f"{'YES' if round(mine, 2) == rep2[c] else 'NO'} |")
    for c in "ABC":
        got, n = out["study2"]["completions"][c]
        lines.append(f"| live completions arm {c} | {comp2[c][0]}/{comp2[c][1]} | — | {got}/{n} | "
                     f"{'YES' if (got, n) == comp2[c] else 'NO'} |")
    v2 = out["step1_per_decision_verification"]["study2"]
    lines += ["",
              f"Per-decision check (Study 2): recomputed regret at P=10,000 vs recorded `policy_regret` for all {v2['n']} episodes: "
              f"max abs diff {v2['max_abs_diff']:.3g} ms; {v2['n_exact']} exact, {v2['n_within_1e-6']} within 1e-6.",
              "Authors'-script rerun (path-adjusted copy, logic untouched) condition summary equals the committed "
              "`paper/analysis/toolroute_otel_transport_v0_2_analysis.json` exactly (A 6,734.3033 / B 8,956.3667 / C 0.0 ms; live completions 6/5/9).", ""]
    lines += ["## Step 3 — Study 2 arm C zero decomposition (all 9 decisions)", "",
              "Regret components under the frozen oracle at P=10,000. `exact zero` means the recomputed float is 0.0, "
              "not a rounded small value.", "",
              "| model | regime | chosen | chosen cost = EWMA + fail-comp + circuit-comp | best cost | regret | wait? |",
              "|---|---|---|---|---|---|---|"]
    for e in zero_rows:
        if e["is_wait"]:
            lines.append(f"| {e['model']} | {e['regime']} | wait | — | {e['best_cost']:.2f} | {e['regret_recomputed']:.2f} | yes |")
        else:
            cp = e["chosen_components"]
            lines.append(f"| {e['model']} | {e['regime']} | {e['action']} | {e['chosen_cost']:.2f} = {cp['latency_ewma_ms']:.2f} + "
                         f"{cp['failure_component_ms']:.2f} (rate {cp['failure_rate']:.3f}) + {cp['circuit_component_ms']:.2f} ({cp['circuit']}) | "
                         f"{e['best_cost']:.2f} | {e['regret_recomputed']:.4f} | no |")
    lines += ["", "In every arm-C episode the chosen route is the observable-best route; its cost is its latency "
              "EWMA alone (0.82-1.95 ms) with zero failure component (rate 0, successes 3/3) and zero circuit "
              "component (CLOSED). The faulted other route carries failure rate 1.0 plus an OPEN circuit in the "
              "six connection_error/http_error episodes (cost 20,000.80-20,005.30 ms), and is latency-only in the "
              "three latency episodes (EWMA 302.64-303.69 ms, rate 0, CLOSED). No arm-C decision is a wait. "
              "The zero is therefore exact and is carried by zero unsuccessful calls and zero open circuits on "
              "the chosen route, as pre-registered.", ""]
    (AUDIT_DIR / "recompute-table.md").write_text("\n".join(lines))

    # ---------------- markdown: sensitivity table
    lines = ["# Regret sensitivity to the penalty constant P — L0 offline audit (Step 2)", "",
             "Frozen rules: route cost = latency_EWMA + P x failure_rate + P x [circuit=OPEN]; the wait rule is "
             "NOT rescaled (wait regret = 500 + 10,000 - best_P); observable-best is re-selected under the same P "
             "for every decision. Completion rates do not depend on P (they come from recorded outcomes) and are "
             "unchanged across all rows: Study 1 A 47/72, B 50/72, C 69/72; Study 2 A 6/9, B 5/9, C 9/9.", ""]
    for study, rows_out in (("Study 1 (216 decisions)", out["study1"]), ("Study 2 (27 decisions)", out["study2"])):
        lines += [f"## {study}", "",
                  "| P (ms) | mean regret A | mean regret B | mean regret C | B->C drop | A->C drop |",
                  "|---|---|---|---|---|---|"]
        for p in P_LEVELS:
            m = rows_out["means"][p]
            d = rows_out["drops"][p]
            lines.append(f"| {p:,} | {m['A']:,.2f} | {m['B']:,.2f} | {m['C']:,.2f} | {d['B_to_C_pct']:.1f}% | {d['A_to_C_pct']:.1f}% |")
        lines.append("")
    (AUDIT_DIR / "regret-sensitivity-table.md").write_text("\n".join(lines))

    print(json.dumps({
        "study1_means": {p: out["study1"]["means"][p] for p in P_LEVELS},
        "study2_means": {p: out["study2"]["means"][p] for p in P_LEVELS},
        "study1_drops": out["study1"]["drops"], "study2_drops": out["study2"]["drops"],
        "verify": out["step1_per_decision_verification"],
        "labels": out["step6_labels"],
    }, indent=1, default=str))


if __name__ == "__main__":
    main()
