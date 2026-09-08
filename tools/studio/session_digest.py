#!/usr/bin/env python3
"""Readable trajectories from Codex session JSONL files: what each thread actually did.

Usage:
  session_digest.py [--sessions ~/.codex/sessions] [--workspace <checkout>] [--after 2026-09-08] [--out <file>] [--types] [--full]
  session_digest.py --thread <session id or file-name fragment> --raw      # one thread, nothing truncated

Reads rollout-*.jsonl under the sessions root (Codex writes ~/.codex/sessions/YYYY/MM/DD/), keeps
the sessions whose session_meta cwd is the workspace (default: this checkout), and writes per
session: id, start, model, parent thread when present, user messages, the sequence of tool calls
(name + argument summary), outputs that look like errors, spawned agents, compactions, last token
count. --full prints every call instead of the compressed sequence; --raw prints, untruncated, the
full text of every user message (a spawned role's brief is its first user message) and the full
arguments of every spawn_agent call, which is the only way to see what a role was actually given;
--thread keeps one session by id or file-name fragment; --types only lists the record types seen
(use it first when Codex changed its format). Reads only.
Format: envelope {timestamp, type, payload}; types session_meta, turn_context, response_item
(message, reasoning, function_call, function_call_output, custom_tool_call, web_search_call),
event_msg (user_message, agent_message, token_count, task_started, task_complete, exec_command_end,
compacted, ...). Verified against the txcript/heddle format notes for Codex 0.15x; unknown types are
counted, never dropped silently.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, json, pathlib, sys

ERR_WORDS = ("error", "Error", "ERROR", "Traceback", "failed", "exit_code\": 1", "exit code 1", "not found", "denied")


def summarize_args(name: str, raw) -> str:
    try:
        args = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        return str(raw)[:120]
    if not isinstance(args, dict):
        return str(args)[:120]
    keys = ("cmd", "command", "code", "path", "file_path", "query", "agent", "name", "message", "prompt", "studio_id", "mode")
    parts = []
    for k in keys:
        if k in args:
            v = args[k]
            v = " ".join(v) if isinstance(v, list) else str(v)
            parts.append(f"{k}={v[:100]!r}")
    if not parts:
        parts.append(json.dumps(args)[:120])
    return ", ".join(parts)


def load(path: pathlib.Path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def digest(path: pathlib.Path, full: bool, raw: bool = False) -> tuple[dict, str]:
    meta = {"file": str(path), "id": None, "cwd": None, "start": None, "model": None, "parent": None}
    calls, outputs, users, agents_msgs, spawns, compactions, tokens, types = [], {}, [], 0, [], 0, None, collections.Counter()
    raw_spawns = []
    for rec in load(path):
        t = rec.get("type"); p = rec.get("payload") or {}
        types[t] += 1
        if t == "session_meta":
            meta.update(id=p.get("id"), cwd=p.get("cwd"), start=p.get("timestamp") or rec.get("timestamp"))
            meta["parent"] = p.get("parent_thread_id") or rec.get("parent_thread_id")
            meta["cli"] = p.get("cli_version")
        elif t == "turn_context":
            meta["model"] = p.get("model") or meta["model"]
        elif t == "response_item":
            pt = p.get("type"); types[f"response_item/{pt}"] += 1
            if pt == "function_call":
                name = p.get("name", "?")
                calls.append({"name": name, "args": summarize_args(name, p.get("arguments")), "call_id": p.get("call_id"), "ts": rec.get("timestamp")})
                if name in ("spawn_agent", "spawn_agents_on_csv"):
                    spawns.append(summarize_args(name, p.get("arguments")))
                    raw_spawns.append(p.get("arguments") if isinstance(p.get("arguments"), str) else json.dumps(p.get("arguments"), ensure_ascii=False))
            elif pt == "function_call_output":
                out = p.get("output"); out = out if isinstance(out, str) else json.dumps(out)
                outputs[p.get("call_id")] = out
            elif pt == "custom_tool_call":
                calls.append({"name": p.get("name", "custom"), "args": str(p.get("input", ""))[:120], "call_id": p.get("call_id"), "ts": rec.get("timestamp")})
            elif pt == "message":
                role = p.get("role")
                text = " ".join(c.get("text", "") for c in p.get("content", []) if isinstance(c, dict))
                if role == "user":
                    users.append(text.strip() if raw else text.strip()[:300])
                elif role == "assistant":
                    agents_msgs += 1
        elif t == "event_msg":
            et = p.get("type"); types[f"event_msg/{et}"] += 1
            if et == "token_count":
                tokens = (p.get("info") or {}).get("total_token_usage") or (p.get("info") or {}).get("last_token_usage") or tokens
            elif et == "compacted":
                compactions += 1
        elif t == "compacted":
            compactions += 1
    lines = [f"## Session {meta['id'] or path.stem}", f"- file: {path}", f"- start: {meta['start']}  model: {meta['model']}  cli: {meta.get('cli')}", f"- cwd: {meta['cwd']}"]
    if meta["parent"]:
        lines.append(f"- parent thread: {meta['parent']}")
    lines.append(f"- tool calls: {len(calls)}, assistant messages: {agents_msgs}, compactions: {compactions}, tokens: {tokens}")
    if spawns:
        lines.append("- spawned: " + " | ".join(s[:160] for s in spawns))
    if raw:
        for i, u in enumerate(users):
            lines.append(f"- user[{i}] (full):\n```\n{u}\n```")
        for i, sp in enumerate(raw_spawns):
            lines.append(f"- spawn[{i}] arguments (full):\n```\n{sp}\n```")
    else:
        for i, u in enumerate(users[:6]):
            lines.append(f"- user[{i}]: {u}")
    counts = collections.Counter(c["name"] for c in calls)
    lines.append("- calls by tool: " + ", ".join(f"{k}×{v}" for k, v in counts.most_common()))
    errs = [c for c in calls if any(w in (outputs.get(c["call_id"]) or "")[:2000] for w in ERR_WORDS)]
    lines.append(f"- calls whose output looks like an error: {len(errs)}")
    for c in errs[:15]:
        lines.append(f"  - {c['name']}({c['args'][:100]}) → {(outputs.get(c['call_id']) or '')[:160]!r}")
    lines.append("- sequence:")
    if full:
        for c in calls:
            lines.append(f"  - {c['ts']} {c['name']}({c['args']}) → {len(outputs.get(c['call_id']) or '')} chars")
    else:
        run_name, run_len = None, 0
        for c in calls + [{"name": None}]:
            if c["name"] == run_name:
                run_len += 1; continue
            if run_name:
                lines.append(f"  - {run_name}" + (f" ×{run_len}" if run_len > 1 else ""))
            run_name, run_len = c["name"], 1
    lines.append("- record types: " + ", ".join(f"{k}:{v}" for k, v in sorted(types.items())))
    return meta, "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", default=str(pathlib.Path.home() / ".codex/sessions"))
    ap.add_argument("--workspace", default=None); ap.add_argument("--after"); ap.add_argument("--out"); ap.add_argument("--types", action="store_true"); ap.add_argument("--full", action="store_true")
    ap.add_argument("--any-workspace", action="store_true", help="do not filter by cwd")
    ap.add_argument("--thread", help="keep one session: its id or a fragment of its file name")
    ap.add_argument("--raw", action="store_true", help="print user messages and spawn_agent arguments untruncated")
    a = ap.parse_args()
    sessions = pathlib.Path(a.sessions).expanduser()
    if not sessions.exists():
        sys.exit(f"no sessions folder at {sessions}")
    workspace = pathlib.Path(a.workspace or pathlib.Path(__file__).resolve().parents[2]).resolve()
    after = dt.datetime.fromisoformat(a.after) if a.after else None
    files = sorted(sessions.rglob("rollout-*.jsonl"))
    if after:
        files = [f for f in files if dt.datetime.fromtimestamp(f.stat().st_mtime) >= after]
    if a.thread:
        files = [f for f in files if a.thread in f.name]
        if not files:
            sys.exit(f"no session file matches {a.thread!r}")
    if a.types:
        total = collections.Counter()
        for f in files:
            for rec in load(f):
                t = rec.get("type"); p = rec.get("payload") or {}
                total[f"{t}/{p.get('type')}" if isinstance(p, dict) and p.get("type") else str(t)] += 1
        print(json.dumps(total, indent=1)); return
    out = [f"# Session digest for {workspace}", ""]
    kept = 0
    for f in files:
        meta, text = digest(f, a.full, a.raw)
        cwd = meta.get("cwd")
        if not a.any_workspace and not a.thread and (not cwd or pathlib.Path(cwd).resolve() != workspace):
            continue
        kept += 1; out.append(text)
    out.insert(1, f"{kept} of {len(files)} session files belong to this workspace" + (f" (after {a.after})" if a.after else ""))
    md = "\n".join(out)
    if a.out:
        pathlib.Path(a.out).write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
