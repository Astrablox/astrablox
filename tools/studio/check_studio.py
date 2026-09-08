#!/usr/bin/env python3
"""Static consistency gate for the studio: roles, registrations, markers, skills, references, caps.

Usage:
  check_studio.py [--root <checkout>] [--json]

Exit 1 when any error is found. Checks:
  - every [agents."<name>"] in .codex/config.toml has a config_file that exists, parses as TOML,
    and carries name (== key), description, developer_instructions, a valid model_reasoning_effort;
  - every role file in .codex/agents/ is registered, and vice versa;
  - every lane in the AGENTS.md lane table (except lead) has a registered lane file, and the contract's
    base report markers plus the lane's extra markers appear verbatim in its developer_instructions;
  - AGENTS.md stays under the Codex project-doc cap (32 KiB, warning above 28 KiB);
  - every .agents/skills/<name>/SKILL.md has frontmatter with name and description;
  - every `.agents/skills/<name>` and `tools/...` path mentioned in AGENTS.md, roles and skills exists,
    and every `$skill-name` a role or skill loads is an existing skill;
  - .codex/hooks.json parses and its command scripts exist.
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys, tomllib

EFFORTS = {"low", "medium", "high", "xhigh", "max"}
CAP, WARN = 32 * 1024, 28 * 1024


def frontmatter(text: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def marker_key(cell: str) -> list[str]:
    """Markers as the producer parses them: text up to and including the first colon, or the first token."""
    keys = []
    for part in [p.strip().strip("`").strip() for p in cell.split(",")]:
        if not part:
            continue
        if ":" in part:
            keys.append(part[: part.index(":") + 1])
        else:
            keys.append(part.split(" / ")[0].split()[0])
    return keys


BASE_MARKERS = ["DELIVERED:", "EVIDENCE:", "ASSUMPTIONS:", "WEAKEST:", "OPEN:", "STATUS:"]


def role_table(agents_md: str) -> dict[str, list[str]]:
    """Lane table of AGENTS.md (header '| Lane | Session | Owns | Extra markers |') -> {session: [markers]}.

    The lead has no lane file (AGENTS.md is its file) and is skipped. Every other lane must return the
    contract's base markers (docs/contract.md §5) plus the extra markers its row lists; a '/' in
    the markers cell separates alternative marker sets (dev: FIX or AUDIT), all of which must exist."""
    rows, inside = {}, False
    for line in agents_md.splitlines():
        if not line.startswith("|"):
            inside = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "Lane":
            inside = True
            continue
        if not inside or len(cells) != 4 or set(cells[0]) <= {"-"}:
            continue
        session = cells[1].strip("` ")
        if session == "lead" or cells[0].lower() == "lead" or "session" in session:
            continue
        extra = []
        for alt in cells[3].split(" / "):
            extra += marker_key(alt)
        base = [] if session == "dev" else list(BASE_MARKERS)
        rows[session] = base + [m for m in extra if m not in base]
    return rows


def role_name(label: str) -> str:
    """Session name is the lane file name in v1.0; kept for callers that pass labels with modes."""
    return re.sub(r"\s*\(.*\)$", "", label).strip("` ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    root = pathlib.Path(a.root or pathlib.Path(__file__).resolve().parents[2])
    errors, warnings = [], []

    cfg_path = root / ".codex/config.toml"
    cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    registered = cfg.get("agents", {})
    roles: dict[str, dict] = {}
    for name, entry in registered.items():
        if not isinstance(entry, dict) or "config_file" not in entry:
            continue
        if not entry.get("description"):
            errors.append(f"config.toml: agent {name} has no description")
        p = root / ".codex" / entry["config_file"]
        if not p.exists():
            errors.append(f"config.toml: agent {name} config_file missing: {p}")
            continue
        try:
            t = tomllib.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{p.name}: TOML parse error: {e}")
            continue
        for field in ("name", "description", "developer_instructions"):
            if not t.get(field):
                errors.append(f"{p.name}: missing {field}")
        if t.get("name") and t["name"] != name:
            errors.append(f"{p.name}: name {t['name']!r} differs from registration {name!r}")
        eff = t.get("model_reasoning_effort")
        if eff is not None and eff not in EFFORTS:
            errors.append(f"{p.name}: model_reasoning_effort {eff!r} not in {sorted(EFFORTS)}")
        roles[name] = t
    for p in sorted((root / ".codex/agents").glob("*.toml")):
        if p.stem not in registered:
            errors.append(f"{p.name}: role file not registered in config.toml")

    agents_md_path = root / "AGENTS.md"
    agents_md = agents_md_path.read_text(encoding="utf-8")
    size = len(agents_md.encode("utf-8"))
    if size > CAP:
        errors.append(f"AGENTS.md is {size} bytes, over the {CAP} byte cap: Codex drops the tail silently")
    elif size > WARN:
        warnings.append(f"AGENTS.md is {size} bytes; cap is {CAP}")
    table = role_table(agents_md)
    table_roles = {role_name(label) for label in table}
    for label, markers in table.items():
        name = role_name(label)
        if name not in roles:
            errors.append(f"AGENTS.md table: row {label!r} is not a registered role")
            continue
        text = roles[name].get("developer_instructions", "")
        for mk in markers:
            if mk not in text:
                errors.append(f"AGENTS.md table: marker {mk!r} for {label} not found in its developer_instructions")
    for name in roles:
        if name not in table_roles and not roles[name].get("description", "").startswith("Judge subagent:"):
            errors.append(f"AGENTS.md table: registered agent {name!r} is neither a lane in the table nor a 'Judge subagent:'")

    skills_dir = root / ".agents/skills"
    skills = {}
    for d in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        sk = d / "SKILL.md"
        if not sk.exists():
            errors.append(f"skill {d.name}: SKILL.md missing")
            continue
        fm = frontmatter(sk.read_text(encoding="utf-8"))
        if fm.get("name") != d.name:
            errors.append(f"skill {d.name}: frontmatter name {fm.get('name')!r} differs from folder")
        if not fm.get("description"):
            errors.append(f"skill {d.name}: no description in frontmatter")
        skills[d.name] = fm

    texts = {"AGENTS.md": agents_md}
    texts.update({f".codex/agents/{n}.toml": t.get("developer_instructions", "") + " " + t.get("description", "") for n, t in roles.items()})
    for d in skills:
        for f in (skills_dir / d).rglob("*.md"):
            texts[str(f.relative_to(root))] = f.read_text(encoding="utf-8")
    ref_re = re.compile(r"(?<![\w/])((?:\.agents/skills|tools)/[\w./-]+)")
    for src, text in texts.items():
        for ref in set(ref_re.findall(text)):
            ref = ref.rstrip(".")
            target = root / ref
            if not target.exists() and not any(root.glob(ref + "*")):
                errors.append(f"{src}: references {ref} which does not exist")
        for sk in set(re.findall(r"\$([a-z][a-z0-9]*(?:-[a-z0-9]+)+)", text)):
            if sk not in skills:
                errors.append(f"{src}: loads skill ${sk} which does not exist (skills: {', '.join(sorted(skills))})")
    hooks = root / ".codex/hooks.json"
    if hooks.exists():
        try:
            h = json.loads(hooks.read_text(encoding="utf-8"))
            for event, groups in h.get("hooks", {}).items():
                for g in groups:
                    for hk in g.get("hooks", []):
                        cmd = hk.get("command", "")
                        parts = cmd.split()
                        if len(parts) >= 2 and not (root / parts[1]).exists():
                            errors.append(f"hooks.json: {event} command script {parts[1]} missing")
        except Exception as e:
            errors.append(f"hooks.json: {e}")

    result = {"roles": len(roles), "skills": len(skills), "agents_md_bytes": size,
              "errors": errors, "warnings": warnings, "ok": not errors}
    if a.json:
        print(json.dumps(result, indent=1))
    else:
        print(f"roles={len(roles)} skills={len(skills)} AGENTS.md={size}B")
        for w in warnings:
            print("WARN", w)
        for e in errors:
            print("ERROR", e)
        print("OK" if not errors else f"FAILED ({len(errors)} errors)")
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
