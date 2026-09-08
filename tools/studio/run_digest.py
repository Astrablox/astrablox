#!/usr/bin/env python3
"""Digest of one run cycle: which reports exist, which producer markers they carry, verdicts, evidence.

Usage:
  run_digest.py [--root <checkout>] [--cycle cycle-003 | --all] [--out <file>]

Reads gamemaster/run.json, state.json, buglist.md and gamemaster/logs/<cycle>/reports/*.md.
For every report: the role it belongs to (by file name, else by the markers it carries), the markers
the AGENTS.md role table expects and which are missing, VERDICT / OUTCOME lines, counts of BLOCKED,
UNOBSERVED, NOT RUN, INCONCLUSIVE, every path the report references and whether it exists on disk.
Writes Markdown to <cycle>/digest.md (or --out) and prints it. Deterministic; reads only.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_studio import role_table, role_name  # noqa: E402

FLAGS = ("BLOCKED", "UNOBSERVED", "NOT RUN", "INCONCLUSIVE", "NEEDS FIXES", "NEEDS DIRECTION", "RETURN")
PATH_RE = re.compile(r"(?<![\w])((?:[A-Za-z]:\\|\.{0,2}/|gamemaster/|artifacts/|logs/)[\w./\\ -]*?\.(?:png|jpg|jpeg|mp4|webm|rbxl|rbxm|json|md|luau|txt))")


def latest_cycle(logs: pathlib.Path) -> pathlib.Path | None:
    cycles = sorted(p for p in logs.glob("cycle-*") if p.is_dir())
    return cycles[-1] if cycles else None


def digest_cycle(root: pathlib.Path, cycle: pathlib.Path, table: dict[str, list[str]]) -> str:
    gm = root / "gamemaster"
    out = [f"# Run digest: {cycle.name}", ""]
    run = gm / "run.json"
    if run.exists():
        r = json.loads(run.read_text(encoding="utf-8-sig"))
        out.append("## Run")
        for k in ("run_id", "mode", "objective", "status", "stop_reason", "continues", "max_continues", "started_utc", "deadline_utc", "next_action", "blocked_reason"):
            if k in r:
                out.append(f"- {k}: {r[k]}")
        out.append("")
    state = gm / "state.json"
    if state.exists():
        try:
            s = json.loads(state.read_text(encoding="utf-8-sig"))
            out.append("## State"); out.append("```json"); out.append(json.dumps(s, indent=1, ensure_ascii=False)[:4000]); out.append("```"); out.append("")
        except Exception as e:
            out.append(f"state.json unreadable: {e}\n")
    bugs = gm / "buglist.md"
    if bugs.exists():
        lines = [l for l in bugs.read_text(encoding="utf-8-sig").splitlines() if l.strip().startswith(("-", "*", "|"))]
        out.append(f"## Buglist: {len(lines)} entries"); out.extend(lines[:40]); out.append("")
    reports = sorted((cycle / "reports").glob("*.md")) if (cycle / "reports").exists() else []
    out.append(f"## Reports: {len(reports)}")
    if not reports:
        out.append("No reports in this cycle: either no role ran, or roles wrote elsewhere. Check session_digest.py.")
    seen_roles = set()
    for rp in reports:
        text = rp.read_text(encoding="utf-8-sig", errors="replace")
        names = sorted({role_name(l) for l in table}, key=len, reverse=True)
        role = next((n for n in names if n in rp.stem), None)
        hits = {lab: sum(1 for m in ms if m in text) for lab, ms in table.items()}
        if role is None:
            best = max(hits, key=hits.get) if hits else None
            role = role_name(best) if best and hits[best] > 1 else None
        # a role with several modes (art-director DIRECTION/REVIEW, studio-developer FIX/AUDIT): judge against the mode whose markers match best
        labels = [lab for lab in table if role_name(lab) == role]
        label = max(labels, key=lambda l: hits[l]) if labels else None
        expected = table.get(label, []) if label else []
        present = [m for m in expected if m in text]
        missing = [m for m in expected if m not in text]
        seen_roles.add(role)
        out.append(f"### {rp.name}  (role: {label or 'unknown'}, {len(text)} chars)")
        if expected:
            out.append(f"- markers present: {', '.join(present) or 'none'}")
            if missing:
                out.append(f"- MISSING markers: {', '.join(missing)}")
        for line in text.splitlines():
            if re.match(r"\s*(VERDICT|OUTCOME|COMPOSITION VERDICT|Level completed|STATUS)\s*:", line):
                out.append(f"- {line.strip()[:200]}")
        flags = {f: len(re.findall(r"\b" + re.escape(f) + r"\b", text)) for f in FLAGS}
        flags = {k: v for k, v in flags.items() if v}
        if flags:
            out.append(f"- flags: {flags}")
        paths = sorted(set(PATH_RE.findall(text)))
        if paths:
            ok, gone = [], []
            for p in paths:
                cand = [root / p, cycle / p, gm / p, pathlib.Path(p)]
                (ok if any(c.exists() for c in cand) else gone).append(p)
            out.append(f"- evidence paths: {len(ok)} exist, {len(gone)} missing")
            for p in gone[:20]:
                out.append(f"  - MISSING: {p}")
        first = next((l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")), "")
        out.append(f"- opens with: {first[:240]}")
        out.append("")
    ran = [r for r in seen_roles if r]
    silent = sorted({role_name(l) for l in table} - set(ran))
    out.append("## Roles with no report in this cycle")
    out.append(", ".join(silent) if silent else "none")
    captures = [p for p in cycle.rglob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".mp4", ".webm")]
    out.append(f"\n## Media under {cycle.name}: {len(captures)} files")
    for p in captures[:30]:
        out.append(f"- {p.relative_to(cycle)} ({p.stat().st_size // 1024} KB)")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None); ap.add_argument("--cycle"); ap.add_argument("--all", action="store_true"); ap.add_argument("--out")
    a = ap.parse_args()
    root = pathlib.Path(a.root or pathlib.Path(__file__).resolve().parents[2])
    table = role_table((root / "AGENTS.md").read_text(encoding="utf-8"))
    logs = root / "gamemaster/logs"
    if not logs.exists():
        sys.exit(f"no {logs}: no run has happened in this checkout")
    cycles = sorted(p for p in logs.glob("cycle-*") if p.is_dir()) if a.all else [logs / a.cycle if a.cycle else latest_cycle(logs)]
    if not cycles or cycles[0] is None or not cycles[0].exists():
        sys.exit("no cycle folder found under gamemaster/logs")
    for c in cycles:
        md = digest_cycle(root, c, table)
        target = pathlib.Path(a.out) if a.out else c / "digest.md"
        target.write_text(md, encoding="utf-8")
        print(md)
        print(f"[written to {target}]")


if __name__ == "__main__":
    main()
