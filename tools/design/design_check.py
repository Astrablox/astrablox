#!/usr/bin/env python3
"""Gate for a scene's gameplay.md against game/DESIGN.md (docs/v0.3-contract.md §11, design).

Usage:
  design_check.py game/scenes/<id>/gameplay.md [--design game/DESIGN.md] [--text]

Checks, and exits 1 on any failure:
  - every line under "## Systems used" names a section that exists in DESIGN.md (matched by the
    section reference `§5.2` / `5.2` / the heading text) — a system used but not specified is a defect;
  - every "### <encounter>" block under "## Encounters" carries the four fields the contract names:
    Enemies, Space (or the scene's "## Space" section), Mechanics, and a feel target ("Feel" / "Feel target");
  - every enemy named in an encounter appears as a "### " heading in DESIGN.md's enemies section
    (case-insensitive word match) — an enemy without a spec cannot be built by creatures or code;
  - "## Feel" and "## Minute by minute" are present and not placeholders (no angle-bracket text left).
Warnings (do not fail): a DESIGN.md enemy never used by any scene encounter.
Prints JSON (or --text) with every finding addressed by line.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys


def sections(text: str):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^(#{2,3})\s+(.*)", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip(), i))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("gameplay"); ap.add_argument("--design", default=None); ap.add_argument("--text", action="store_true")
    a = ap.parse_args()
    gp = pathlib.Path(a.gameplay); root = gp.resolve().parents[3] if len(gp.resolve().parents) > 3 else pathlib.Path.cwd()
    design = pathlib.Path(a.design) if a.design else root / "game/DESIGN.md"
    if not design.exists():
        design = pathlib.Path("game/DESIGN.md")
    g = gp.read_text(encoding="utf-8"); d = design.read_text(encoding="utf-8") if design.exists() else ""
    findings, warnings = [], []
    if not d:
        findings.append({"line": 0, "problem": f"DESIGN.md not found at {design}"})
    dsecs = sections(d)
    dnums = {re.match(r"^(\d+(?:\.\d+)?)", h).group(1) for _, h, _ in dsecs if re.match(r"^\d", h)}
    dheads = {h.lower() for _, h, _ in dsecs}
    enemy_heads = []
    in_enemies = False
    for lvl, h, ln in dsecs:
        if lvl == 2:
            in_enemies = "enem" in h.lower()
        elif lvl == 3 and in_enemies:
            enemy_heads.append(re.sub(r"^\d+(\.\d+)?\s*", "", h).lower())
    gsecs = sections(g)
    lines = g.splitlines()
    def body(title):
        for idx, (lvl, h, ln) in enumerate(gsecs):
            if lvl == 2 and h.lower().startswith(title):
                nxt = next((s for s in gsecs[idx + 1:] if s[0] == 2), None)
                end = nxt[2] - 1 if nxt else len(lines)
                return ln, lines[ln:end]
        return None, []
    for title in ("feel", "minute by minute", "systems used", "encounters"):
        ln, b = body(title)
        if ln is None:
            findings.append({"line": 0, "problem": f"section '## {title}' missing"})
        elif not any(l.strip() for l in b) or all(re.match(r"^\s*<.*>\s*$", l) for l in b if l.strip()):
            findings.append({"line": ln, "problem": f"section '## {title}' is empty or still a placeholder"})
    ln, b = body("systems used")
    for i, l in enumerate(b, ln + 1):
        if not l.strip() or l.strip().startswith("<"):
            continue
        refs = re.findall(r"§?\s*(\d+(?:\.\d+)?)", l)
        ok = any(r in dnums for r in refs) or any(h in l.lower() for h in dheads if len(h) > 6)
        if not ok:
            findings.append({"line": i, "problem": f"system line does not name a DESIGN.md section: {l.strip()[:80]}"})
    ln, b = body("encounters")
    used_enemies = set()
    if ln is not None:
        blocks, cur = [], None
        for i, l in enumerate(b, ln + 1):
            if l.startswith("### "):
                cur = {"name": l[4:].strip(), "line": i, "text": []}; blocks.append(cur)
            elif cur is not None:
                cur["text"].append(l)
        if not blocks:
            findings.append({"line": ln, "problem": "no '### <encounter>' blocks under Encounters"})
        space_section = body("space")[0] is not None
        for blk in blocks:
            t = "\n".join(blk["text"]).lower()
            for field in ("enemies", "mechanics"):
                if not re.search(rf"^\s*-\s*{field}\s*:", t, re.M):
                    findings.append({"line": blk["line"], "problem": f"encounter '{blk['name']}' lacks '- {field.capitalize()}:'"})
            if not re.search(r"^\s*-\s*space\s*:", t, re.M) and not space_section:
                findings.append({"line": blk["line"], "problem": f"encounter '{blk['name']}' names no space and the scene has no '## Space'"})
            if not re.search(r"^\s*-\s*feel( target)?\s*:", t, re.M):
                findings.append({"line": blk["line"], "problem": f"encounter '{blk['name']}' has no feel target"})
            m = re.search(r"^\s*-\s*enemies\s*:(.*)$", t, re.M)
            if m:
                for name in enemy_heads:
                    if name in m.group(1):
                        used_enemies.add(name)
                named = [w for w in re.split(r"[,;]| and ", m.group(1)) if w.strip()]
                for w in named:
                    w2 = re.sub(r"^\s*(\d+|one|two|three|four|five|a|an|several|a pack of)\s*", "", w.strip()).strip(" .")
                    if w2 and not any(h in w2 or w2 in h for h in enemy_heads) and w2 not in ("none", "no enemies"):
                        findings.append({"line": blk["line"], "problem": f"enemy '{w2}' in '{blk['name']}' has no '### ' spec in DESIGN.md's enemies section"})
    for name in enemy_heads:
        if name not in used_enemies:
            warnings.append(f"DESIGN.md enemy '{name}' is not used by any encounter in this scene")
    result = {"file": str(gp), "design": str(design), "findings": findings, "warnings": warnings, "verdict": "FAIL" if findings else "PASS"}
    if a.text:
        for f in findings: print(f"L{f['line']}: {f['problem']}")
        for w in warnings: print("warn:", w)
        print("DESIGN CHECK:", result["verdict"])
    else:
        print(json.dumps(result, indent=1))
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
