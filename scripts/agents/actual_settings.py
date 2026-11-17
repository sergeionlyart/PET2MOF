#!/usr/bin/env python3
"""Print the model/effort/sandbox that Codex actually applied for a thread.

Reads the client-side rollout file ~/.codex/sessions/**/rollout-*-<thread_id>.jsonl
(`turn_context` records). Only non-secret setting fields are read and printed.
Limitation: this is what the Codex client applied and sent; server-side routing is not visible.
"""
import json, sys, pathlib

def actual(thread_id: str) -> dict:
    root = pathlib.Path.home() / ".codex" / "sessions"
    files = sorted(root.rglob(f"rollout-*-{thread_id}.jsonl"))
    if not files:
        return {"rollout_found": False}
    out = {"rollout_found": True, "turns": [], "agent_tool_calls": 0}
    for line in files[-1].open(encoding="utf-8"):
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        p = o.get("payload", {}) or {}
        # Collaboration tools (spawn_agent, wait_agent, ...): a call means delegated, unrecorded work.
        if (o.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call")
                and "agent" in (p.get("name") or "")):
            out["agent_tool_calls"] += 1
        if o.get("type") == "session_meta":
            out["cli_version"] = p.get("cli_version")
            out["originator"] = p.get("originator")
        elif o.get("type") == "turn_context":
            sp = p.get("sandbox_policy") or {}
            out["turns"].append({"model": p.get("model"), "effort": p.get("effort"),
                                 "sandbox": sp.get("type"), "network_access": sp.get("network_access"),
                                 "approval_policy": p.get("approval_policy")})
    if out["turns"]:
        out.update({k: out["turns"][-1][k] for k in ("model", "effort", "sandbox", "network_access")})
    return out

if __name__ == "__main__":
    print(json.dumps(actual(sys.argv[1]), ensure_ascii=False))
