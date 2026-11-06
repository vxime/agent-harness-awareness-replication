#!/usr/bin/env python3
"""L2 runner: 81 calls to one OpenAI-compatible endpoint, per PROTOCOL.md.

Configuration is via environment variables:
  SST_API_KEY     API key for the endpoint (required; never printed)
  SST_BASE_URL    base URL of an OpenAI-compatible endpoint
                  (default: https://api.openai.com/v1)
  SST_MODEL_LABEL model label to request (default: gpt-6-luna, the label used
                  for the run recorded in this package; the underlying model
                  identity behind a gateway label is not independently
                  verifiable, and all readings are bounded to the label)

- Credentials: read from SST_API_KEY; never printed.
- Results are rewritten to ../raw-results.json after EVERY call.
- Stop rules: 429 / quota-billing error / 3 consecutive failures -> stop.
  One transient network error per call -> retry once. No model substitution.
- Scoring: imports the L0 frozen oracle (offline_audit.regret_under_p, P=10,000)
  and the protocol's offline completion rule.
Requires the `openai` Python package.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
L2_DIR = HERE.parents[1]
sys.path.insert(0, str(HERE.parents[2] / "offline-audit" / "scripts"))

from offline_audit import regret_under_p  # noqa: E402  (frozen L0 oracle)
from openai import OpenAI  # noqa: E402
import openai as openai_module  # noqa: E402

MODEL = os.environ.get("SST_MODEL_LABEL", "gpt-6-luna")
BASE_URL = os.environ.get("SST_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("SST_API_KEY")
MAX_COMPLETION_TOKENS = 1024
OUT = L2_DIR / "raw-results.json"


def completion_of(tools: dict, action: str | None) -> bool:
    if action is None or action == "wait":
        return False
    t = tools[action]
    return int(t["successes"]) == int(t["window_n"]) and int(t["window_n"]) > 0


def parse_choice(reply: str | None, valid_labels: list[str]) -> str | None:
    if reply is None:
        return None
    text = reply.strip()
    if text in valid_labels:
        return text
    found = set()
    for lab in valid_labels:
        if re.search(r"(?<![A-Za-z0-9_\-])" + re.escape(lab) + r"(?![A-Za-z0-9_\-])", text):
            found.add(lab)
    if len(found) == 1:
        return found.pop()
    return None


def dump(state: dict) -> None:
    OUT.write_text(json.dumps(state, indent=1, ensure_ascii=False) + "\n")


def main() -> None:
    if not API_KEY:
        raise SystemExit("SST_API_KEY is not set; refusing to run without credentials.")
    specs = json.loads((L2_DIR / "call-specs.json").read_text())
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120.0)

    state = {
        "meta": {
            "model_label": MODEL, "base_url": BASE_URL,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "temperature": "unset (gateway default)",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "stopped_reason": None, "completed": 0,
        },
        "records": [],
    }
    if OUT.exists():
        prev = json.loads(OUT.read_text())
        done = {r["seq"] for r in prev["records"] if r.get("status") == "ok"}
        state["records"] = [r for r in prev["records"] if r.get("status") == "ok"]
        state["meta"]["resumed_from"] = len(done)
    done_seqs = {r["seq"] for r in state["records"]}
    dump(state)

    consecutive_failures = 0
    for spec in specs:
        if spec["seq"] in done_seqs:
            continue
        rec = {
            "seq": spec["seq"], "treatment": spec["treatment"], "regime": spec["regime"],
            "arm": spec["arm"], "rep": spec["rep"], "instance_dir": spec["instance_dir"],
            "episode_id": spec["episode_id"], "source_model": spec["source_model"],
            "faulted_tool": spec["faulted_tool"],
            "label_to_physical": spec["label_to_physical"],
            "shown_options": spec["shown_options"],
            "prompt": spec["prompt"],
            "status": None, "attempts": 0, "raw_reply": None,
            "chosen_label": None, "chosen_physical": None, "parse": None,
            "regret": None, "completion": None, "usage": None,
            "response_model": None, "finish_reason": None,
            "called_at": None, "error": None,
        }
        stop = False
        for attempt in (1, 2):
            rec["attempts"] = attempt
            rec["called_at"] = datetime.now(timezone.utc).isoformat()
            try:
                resp = client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": spec["prompt"]}],
                    max_completion_tokens=MAX_COMPLETION_TOKENS,
                )
                rec["raw_reply"] = resp.choices[0].message.content
                rec["finish_reason"] = resp.choices[0].finish_reason
                rec["response_model"] = resp.model
                if resp.usage is not None:
                    rec["usage"] = {
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens,
                    }
                rec["status"] = "ok"
                rec["error"] = None
                break
            except openai_module.RateLimitError as exc:
                rec["status"] = "failed"
                rec["error"] = f"RateLimitError: {str(exc)[:300]}"
                stop = True
                break
            except openai_module.APIStatusError as exc:
                body = str(exc).lower()
                rec["status"] = "failed"
                rec["error"] = f"APIStatusError {exc.status_code}: {str(exc)[:300]}"
                if exc.status_code == 429 or any(
                        k in body for k in ("quota", "insufficient", "billing", "balance", "credit")):
                    stop = True
                break
            except (openai_module.APIConnectionError, openai_module.APITimeoutError) as exc:
                rec["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                if attempt == 1:
                    time.sleep(3)
                    continue
                rec["status"] = "failed"
                break
            except Exception as exc:  # unknown: treat as failure, count toward stop
                rec["status"] = "failed"
                rec["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
                break

        if rec["status"] == "ok":
            consecutive_failures = 0
            label = parse_choice(rec["raw_reply"], spec["valid_labels"])
            if label is None:
                rec["parse"] = "unparseable"
                physical = "wait"  # protocol: scored as wait
            else:
                rec["parse"] = "exact" if (rec["raw_reply"] or "").strip() == label else "token"
                physical = spec["label_to_physical"][label]
            rec["chosen_label"] = label
            rec["chosen_physical"] = physical
            regret, _detail = regret_under_p(spec["tools"], physical, 10_000)
            rec["regret"] = regret
            rec["completion"] = completion_of(spec["tools"], physical if label else None)
        else:
            consecutive_failures += 1

        state["records"].append(rec)
        state["meta"]["completed"] = sum(1 for r in state["records"] if r["status"] == "ok")
        dump(state)
        print(f"seq {spec['seq']:2d} {spec['treatment']} {spec['regime'][:4]} arm {spec['arm']} "
              f"rep {spec['rep']}: {rec['status']} label={rec['chosen_label']} "
              f"phys={rec['chosen_physical']} regret={rec['regret']} err={rec['error']}",
              flush=True)

        if stop:
            state["meta"]["stopped_reason"] = f"stop rule at seq {spec['seq']}: {rec['error']}"
            dump(state)
            print("STOPPED:", state["meta"]["stopped_reason"], flush=True)
            return
        if consecutive_failures >= 3:
            state["meta"]["stopped_reason"] = f"3 consecutive failures at seq {spec['seq']}"
            dump(state)
            print("STOPPED:", state["meta"]["stopped_reason"], flush=True)
            return

    state["meta"]["stopped_reason"] = None
    state["meta"]["finished_at"] = datetime.now(timezone.utc).isoformat()
    dump(state)
    print("DONE all specs.", flush=True)


if __name__ == "__main__":
    main()
