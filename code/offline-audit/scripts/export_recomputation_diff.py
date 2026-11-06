#!/usr/bin/env python3
"""Export the per-decision recomputation diff behind results/evidence/
recomputation-diff.json.

For every retained decision in the authors' frozen archive (Study 1: 216,
Study 2: 27), this writes the recorded `policy_regret` next to the regret
recomputed from the raw host/snapshot quantities with the frozen observable
oracle at P = 10,000 (the same code path as offline_audit.py, imported from
this directory). In the recorded run every absolute difference is exactly 0.0.

Requires a local clone of the authors' archive (see offline_audit.py for
SST_ARCHIVE_DIR). Output defaults to
<package root>/results/evidence/recomputation-diff.json; override with
argv[1].
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE))

import offline_audit as oa  # noqa: E402


def main() -> None:
    s1, s2 = oa.load_study1(), oa.load_study2()
    oa.enrich(s1)
    oa.enrich(s2)

    decisions = []
    for study, rows, extra_keys in (
        ("study1", s1, ("seed", "turn")),
        ("study2", s2, ("regime", "faulted_tool")),
    ):
        for r in rows:
            entry = {
                "study": study,
                "archive_dir": r["dir"],
                "model": r["model"],
                "arm": r["condition"],
                "action": r["action"],
                "success": r["success"],
                "recorded_regret_ms": r["recorded_regret"],
                "recomputed_regret_ms": r["regret"][10_000],
                "abs_diff_ms": abs(r["regret"][10_000] - r["recorded_regret"]),
            }
            for k in extra_keys:
                entry[k] = r[k]
            decisions.append(entry)

    diffs = [d["abs_diff_ms"] for d in decisions]
    out = {
        "description": (
            "Per-decision recorded vs recomputed policy_regret (ms) at the "
            "authors' published pricing P = 10,000, recomputed from raw "
            "host/snapshot quantities with the frozen observable oracle "
            "(observable_monitor_cost_v0.6). archive_dir is the decision's "
            "path inside the authors' archive."
        ),
        "archive": "manu2/scac-dynamic-agent-harness @ d98e3610e880ab06421b4e53bb0cd892c1b19170",
        "p_ms": 10_000,
        "n_decisions": len(decisions),
        "max_abs_diff_ms": max(diffs),
        "n_exact": sum(1 for d in diffs if d == 0.0),
        "decisions": decisions,
    }
    target = (Path(sys.argv[1]) if len(sys.argv) > 1
              else HERE.parents[3] / "results" / "evidence" / "recomputation-diff.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {target}: n={len(decisions)} max_abs_diff={max(diffs)} "
          f"n_exact={out['n_exact']}")


if __name__ == "__main__":
    main()
