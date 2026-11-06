#!/usr/bin/env python3
"""L2 prep (zero model calls): build the 81 call specs from the frozen archive
and run the pre-registered sanity checks.

- Instance = one archived Study 2 episode directory (27 total = 3 source
  models x 3 regimes x 3 conditions). For cell (regime, arm), the 3 reps are
  the 3 archived dirs of that cell (one per source model).
- Prompt for (dir, arm): provider-request.json text if arm == dir's own
  condition, else condition-inputs.json[arm].prompt from the same dir.
- Scoring facts: the dir's snapshot.json tools.
Checks:
  C1 provider-request text == condition-inputs[own arm].prompt for all 27.
  C2 offline completion rule (tool with successes==window_n -> success;
     successes==0 -> failure; wait -> no completion) reproduces the archived
     action-result success flag for all 27 archived decisions.
  C3 the task line is identical across all 81 base prompts.
Output: ../call-specs.json (81 specs with REP/SWAP/ANON prompt texts and
label<->physical mappings), ../prep-report.json.
"""
from __future__ import annotations

import json
import os
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve()
L2_DIR = HERE.parents[1]
ARCHIVE = Path(os.environ.get("SST_ARCHIVE_DIR", HERE.parents[3] / "archive"))
S2_ROOT = ARCHIVE / "experiments/api-otel-transport-v0.2/g2-calibrations/toolroute-otel-transport"
ANON_SEED = 20261106


def extract_request_text(req: dict) -> str:
    body = req["body"]
    adapter = req["adapter"]
    if adapter == "gemini_generate_content_v1":
        return body["contents"][0]["parts"][0]["text"]
    if adapter in ("anthropic_messages_v1", "openai_chat_completions_v1"):
        msg = body["messages"][0]
        content = msg["content"]
        if isinstance(content, list):
            return "".join(part.get("text", "") for part in content)
        return content
    raise ValueError(adapter)


def swap_labels(text: str) -> str:
    """Global tool_alpha <-> tool_beta string exchange."""
    return (text.replace("tool_alpha", "\x00A\x00")
                .replace("tool_beta", "tool_alpha")
                .replace("\x00A\x00", "tool_beta"))


def swap_options_order(text: str) -> str:
    """Reverse the two route labels in the 'Options:' line (wait stays put)."""
    m = re.search(r"Options: ([^\n]+)", text)
    assert m, text[:100]
    opts = [o.strip() for o in m.group(1).split(",")]
    routes = [o for o in opts if o != "wait"]
    others = [o for o in opts if o == "wait"]
    assert len(routes) == 2
    new_opts = list(reversed(routes)) + others
    return text[:m.start(1)] + ", ".join(new_opts) + text[m.end(1):]


def main() -> None:
    dirs = []
    for d in sorted(S2_ROOT.iterdir()):
        if not d.is_dir() or not (d / "manifest.json").exists():
            continue
        man = json.loads((d / "manifest.json").read_text())
        pr = man.get("provider_run", {})
        if not pr.get("episode_id"):
            continue
        ci = json.loads((d / "condition-inputs.json").read_text())
        req = json.loads((d / "provider-request.json").read_text())
        snap = json.loads((d / "snapshot.json").read_text())
        dec = json.loads((d / "model-decision.json").read_text())
        ar = json.loads((d / "action-result.json").read_text())
        dirs.append({
            "dir": d.name, "episode_id": pr["episode_id"], "source_model": pr["model_id"],
            "regime": man["regime"], "own_condition": man["condition"],
            "faulted_tool": man["faulted_tool"], "option_order": man.get("option_order", []),
            "prompts": {c: ci[c]["prompt"] for c in "ABC"},
            "request_text": extract_request_text(req),
            "tools": snap["tools"],
            "archived_action": dec["selected_action"],
            "archived_success": bool(ar["event"]["payload"]["success"]),
        })
    assert len(dirs) == 27, len(dirs)

    # ---- C1
    c1_fail = [d["episode_id"] for d in dirs
               if d["request_text"] != d["prompts"][d["own_condition"]]]
    # ---- C2
    def offline_completion(tools: dict, action: str) -> bool:
        if action == "wait":
            return False
        t = tools[action]
        return int(t["successes"]) == int(t["window_n"]) and int(t["window_n"]) > 0
    c2_fail = [d["episode_id"] for d in dirs
               if offline_completion(d["tools"], d["archived_action"]) != d["archived_success"]]
    # ---- C3
    task_lines = {d["prompts"]["A"].split("\n")[0] for d in dirs}
    # cells
    cells = {}
    for d in dirs:
        key = (d["regime"], d["own_condition"])
        cells.setdefault(key, []).append(d)
    assert all(len(v) == 3 for v in cells.values()) and len(cells) == 9

    rng = random.Random(ANON_SEED)
    code_letters = "GHJKMNPQRT"
    specs = []
    seq = 0
    for treatment in ("REP", "SWAP", "ANON"):
        for regime in ("connection_error", "http_error", "latency"):
            for arm in "ABC":
                for rep_idx, d in enumerate(sorted(cells[(regime, arm)],
                                                   key=lambda x: x["source_model"])):
                    base = d["prompts"][arm]
                    if treatment == "REP":
                        prompt = base
                        mapping = {"tool_alpha": "tool_alpha", "tool_beta": "tool_beta",
                                   "wait": "wait"}
                        shown = list(d["option_order"])
                    elif treatment == "SWAP":
                        prompt = swap_options_order(swap_labels(base))
                        mapping = {"tool_alpha": "tool_beta", "tool_beta": "tool_alpha",
                                   "wait": "wait"}
                        m = re.search(r"Options: ([^\n]+)", prompt)
                        shown = [o.strip() for o in m.group(1).split(",")]
                    else:  # ANON
                        code_a = f"route-{rng.choice(code_letters)}{rng.randint(2, 9)}"
                        code_b = f"route-{rng.choice(code_letters)}{rng.randint(2, 9)}"
                        while code_b == code_a:
                            code_b = f"route-{rng.choice(code_letters)}{rng.randint(2, 9)}"
                        # randomise which physical route gets code_a
                        if rng.random() < 0.5:
                            assign = {"tool_alpha": code_a, "tool_beta": code_b}
                        else:
                            assign = {"tool_alpha": code_b, "tool_beta": code_a}
                        prompt = (base.replace("tool_alpha", "\x00A\x00")
                                      .replace("tool_beta", assign["tool_beta"])
                                      .replace("\x00A\x00", assign["tool_alpha"]))
                        mapping = {assign["tool_alpha"]: "tool_alpha",
                                   assign["tool_beta"]: "tool_beta", "wait": "wait"}
                        m = re.search(r"Options: ([^\n]+)", prompt)
                        shown = [o.strip() for o in m.group(1).split(",")]
                    seq += 1
                    specs.append({
                        "seq": seq, "treatment": treatment, "regime": regime, "arm": arm,
                        "rep": rep_idx, "instance_dir": d["dir"],
                        "episode_id": d["episode_id"], "source_model": d["source_model"],
                        "faulted_tool": d["faulted_tool"],
                        "tools": d["tools"],
                        "prompt": prompt,
                        "label_to_physical": mapping,
                        "shown_options": shown,
                        "valid_labels": sorted(mapping.keys()),
                    })
    assert len(specs) == 81, len(specs)
    (L2_DIR / "call-specs.json").write_text(json.dumps(specs, indent=1) + "\n")
    report = {
        "C1_request_text_mismatches": c1_fail,
        "C2_completion_rule_mismatches": c2_fail,
        "C3_distinct_task_lines": sorted(task_lines),
        "n_specs": len(specs),
        "anon_seed": ANON_SEED,
    }
    (L2_DIR / "prep-report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
