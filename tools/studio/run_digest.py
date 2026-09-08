#!/usr/bin/env python3
"""Digest of one scene's run: task cards, reports against the lead's markers, evidence, builds, bus.

Usage:
  run_digest.py [--root <checkout>] [--scene <id>] [--out <file>]

Reads board/tasks/*.md (front matter: id, lane, scene, status, claimed_by, ...), board/reports/<id>.md,
board/scenes/*.json, board/queue.log, game/scenes/<id>/card.md and builds/*/CHANGES.md.
For every report: the markers the lead expects for that lane (contract base markers plus the lane's
extra markers from the AGENTS.md lane table) and which are missing, STATUS line, BLOCKED and RETURNED
counts, every path the report references and whether it exists. Writes Markdown to
studio/scenes/<id>/digest.md (or --out) and prints it. Deterministic; reads only.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_studio import role_table  # noqa: E402

PATH_RE = re.compile(r"(?<![\w])((?:[A-Za-z]:\\|\.{0,2}/|board/|builds/|assets/|game/|studio/|renders/|work/|out/)[\w./\\ -]*?\.(?:png|jpg|jpeg|webp|mp4|webm|rbxl|rbxm|glb|gltf|json|md|luau|txt|ogg|mp3|wav|blend))")


def front_matter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    out = {}
    block = m.group(1) if m else text.split("\n\n", 1)[0]
    for line in block.splitlines():
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None); ap.add_argument("--scene"); ap.add_argument("--out")
    a = ap.parse_args()
    root = pathlib.Path(a.root or pathlib.Path(__file__).resolve().parents[2])
    table = role_table((root / "AGENTS.md").read_text(encoding="utf-8"))
    board = root / "board"
    if not board.exists():
        sys.exit(f"no {board}: the studio has not run in this checkout")
    tasks = []
    for p in sorted((board / "tasks").glob("*.md")) if (board / "tasks").exists() else []:
        fm = front_matter(p.read_text(encoding="utf-8-sig", errors="replace")); fm["_file"] = p; tasks.append(fm)
    scene = a.scene
    if not scene:
        scenes = [t.get("scene") for t in tasks if t.get("scene")]
        scene = scenes[-1] if scenes else None
    tasks = [t for t in tasks if not scene or t.get("scene") == scene]
    out = [f"# Run digest: scene {scene or '(all)'}", ""]
    state = board / "STATE.md"
    if state.exists():
        out.append("## STATE.md"); out.append(state.read_text(encoding="utf-8-sig")[:3000]); out.append("")
    card = root / "game/scenes" / (scene or "_") / "card.md"
    if card.exists():
        out.append("## Scene card"); out.append(card.read_text(encoding="utf-8-sig")[:3000]); out.append("")
    by_status = {}
    for t in tasks:
        by_status.setdefault(t.get("status", "?"), []).append(t)
    out.append(f"## Tasks: {len(tasks)}  " + ", ".join(f"{k}={len(v)}" for k, v in sorted(by_status.items())))
    for t in tasks:
        out.append(f"- {t.get('id')} [{t.get('lane')}] {t.get('status')} claimed_by={t.get('claimed_by', '')}")
    out.append("")
    out.append("## Reports")
    for t in tasks:
        rp = board / "reports" / f"{t.get('id')}.md"
        if not rp.exists():
            if t.get("status") in ("done", "blocked"):
                out.append(f"### {t.get('id')} [{t.get('lane')}]: REPORT MISSING though status is {t.get('status')}")
            continue
        text = rp.read_text(encoding="utf-8-sig", errors="replace")
        expected = table.get(t.get("lane"), [])
        missing = [m for m in expected if m not in text]
        out.append(f"### {rp.name} [{t.get('lane')}] ({len(text)} chars)")
        if missing:
            out.append(f"- MISSING markers: {', '.join(missing)}")
        for line in text.splitlines():
            if re.match(r"\s*(STATUS|WEAKEST)\s*:", line):
                out.append(f"- {line.strip()[:220]}")
        flags = {f: len(re.findall(r"\b" + f + r"\b", text)) for f in ("BLOCKED", "RETURNED", "UNOBSERVED", "NOT RUN")}
        flags = {k: v for k, v in flags.items() if v}
        if flags:
            out.append(f"- flags: {flags}")
        paths = sorted(set(PATH_RE.findall(text)))
        if paths:
            gone = [p for p in paths if not any(c.exists() for c in (root / p, pathlib.Path(p)))]
            out.append(f"- evidence paths: {len(paths) - len(gone)} exist, {len(gone)} missing")
            for p in gone[:20]:
                out.append(f"  - MISSING: {p}")
        out.append("")
    sc = board / "scenes"
    if sc.exists():
        out.append("## Scene claims")
        for p in sorted(sc.glob("*.json")):
            try:
                d = json.loads(p.read_text(encoding="utf-8")); out.append(f"- {d.get('scene')}: {d.get('status')} by {d.get('by', '')} since {d.get('since', '')}")
            except Exception:
                out.append(f"- {p.name}: unreadable")
        out.append("")
    builds = sorted((root / "builds").glob("*/CHANGES.md")) if (root / "builds").exists() else []
    out.append(f"## Builds: {len(builds)}")
    for b in builds[-5:]:
        out.append(f"### {b.parent.name}"); out.append(b.read_text(encoding="utf-8-sig")[:800])
    ql = board / "queue.log"
    if ql.exists():
        lines = ql.read_text(encoding="utf-8-sig").splitlines()
        out.append(f"\n## Bus: {len(lines)} signals, last 20"); out.extend(lines[-20:])
    md = "\n".join(out) + "\n"
    target = pathlib.Path(a.out) if a.out else root / "studio/scenes" / (scene or "all") / "digest.md"
    target.parent.mkdir(parents=True, exist_ok=True); target.write_text(md, encoding="utf-8")
    print(md); print(f"[written to {target}]")


if __name__ == "__main__":
    main()
