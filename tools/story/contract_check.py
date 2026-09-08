#!/usr/bin/env python3
"""contract_check.py: the objective gate of the story lane (docs/contract.md §11).

What it does: parses a scene's `script.md` and `contract.md` and reports every structural fault that
would reach another lane as a missing name or a half-written quest. It checks form only. It cannot
tell whether a quest is worth playing, whether an NPC is a person or whether a line sounds like this
world; that is what the criteria in `.codex/agents/story.toml` and the fresh judge are for. A scene
that passes this gate is not finished, but a scene that fails it is not deliverable.

Errors (exit 1):
  - a required section is missing from either file;
  - a quest without a place, trigger, goal, choice, consequence or reward, or with an empty one;
  - a quest whose choice carries fewer than two options, or whose consequence options do not match
    its choice options one to one;
  - an NPC without a place, a schedule or lines; a schedule line that does not name when, where and
    what they are doing; a line entry with no quoted line;
  - a point of interest without a place, a story or a visible change;
  - any place named by a quest, an NPC, a schedule entry or a point that the contract does not
    declare; any NPC in the script that the contract does not declare;
  - a name declared twice anywhere in the contract, or two quests, NPCs or points sharing a name.

Warnings (exit 0): a contract entry whose name never appears in the script; an unknown field on an
entry; a name that looks like a placeholder.

Usage:
  contract_check.py game/scenes/<id>                 # both files in the scene folder
  contract_check.py <script.md> <contract.md>        # explicit pair
  contract_check.py game/scenes/<id> --text          # compact human list instead of JSON
JSON goes to stdout by default; exit 1 when the errors list is not empty.

The format both files use is defined once, in `.codex/agents/story.toml` under "The two files and
their format", and this tool enforces exactly that definition. If the two ever disagree, the lane
file is the source and this tool is wrong.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

SCRIPT_SECTIONS = ("Theme", "Place", "NPCs", "Quests", "Points of interest", "Journal")
SCRIPT_PROSE = ("Theme", "Place", "Journal")
CONTRACT_SECTIONS = ("Places", "NPCs", "Props", "Sounds", "Events")

ENTRY_KINDS = {"NPC": "NPCs", "Quest": "Quests", "Point": "Points of interest"}
FIELDS = {
    "NPC": {"scalar": ("Place",), "list": ("Schedule", "Lines")},
    "Quest": {"scalar": ("Place", "Trigger", "Goal", "Reward"), "list": ("Choice", "Consequence")},
    "Point": {"scalar": ("Place", "Story", "Change"), "list": ()},
}

H2 = re.compile(r"^##\s+(.+?)\s*$")
H3 = re.compile(r"^###\s+([A-Za-z ]+?):\s*(.+?)\s*$")
FIELD = re.compile(r"^([A-Z][A-Za-z ]{0,24}):\s*(.*)$")  # any `Field:` line; unknown ones are reported as warnings
BULLET = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
SEP = re.compile(r"\s+[—–]\s+|\s+-\s+")
QUOTED = re.compile(r"[\"«“][^\"»”]+[\"»”]")
NONE = re.compile(r"^\s*(none|—|-)\s*$", re.I)
PLACEHOLDER = re.compile(r"^(tbd|todo|\.\.\.|<.*>|name|place\s*[a-z]?)$", re.I)


class Doc:
    """A markdown file split into `## sections`, each keeping its lines with their numbers."""

    def __init__(self, path: pathlib.Path):
        self.path = path
        self.sections: dict[str, list[tuple[int, str]]] = {}
        self.order: list[str] = []
        current = None
        for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            m = H2.match(raw)
            if m:
                current = m.group(1)
                self.sections.setdefault(current, [])
                self.order.append(current)
                continue
            if current is not None:
                self.sections[current].append((n, raw))

    def body(self, name: str) -> list[tuple[int, str]]:
        return self.sections.get(name, [])

    def is_none(self, name: str) -> bool:
        text = [l for _, l in self.body(name) if l.strip()]
        return len(text) == 1 and bool(NONE.match(text[0]))

    def has_text(self, name: str) -> bool:
        return any(l.strip() for _, l in self.body(name))


class Report:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def error(self, path, line, where, rule, message):
        self.errors.append({"file": str(path), "line": line, "where": where, "rule": rule, "message": message})

    def warn(self, path, line, where, rule, message):
        self.warnings.append({"file": str(path), "line": line, "where": where, "rule": rule, "message": message})


def split_name(text: str) -> tuple[str, str]:
    """`- Name — what it is` -> ("Name", "what it is"). No separator: the whole line is the name."""
    parts = SEP.split(text, maxsplit=1)
    return (parts[0].strip(), parts[1].strip() if len(parts) > 1 else "")


def parse_entries(doc: Doc, section: str, kind: str, rep: Report) -> list[dict]:
    """`### <kind>: <name>` blocks with their `Field:` values; list fields collect the bullets under them."""
    entries: list[dict] = []
    current: dict | None = None
    field: str | None = None
    for n, raw in doc.body(section):
        h3 = H3.match(raw)
        if h3:
            found, name = h3.group(1).strip(), h3.group(2).strip()
            if found != kind:
                rep.error(doc.path, n, f"{section}", "unknown-entry", f"entry '{found}:' in section '{section}'; this section holds '{kind}:' entries")
                current, field = None, None
                continue
            current = {"kind": kind, "name": name, "line": n, "scalar": {}, "list": {}, "unknown": []}
            entries.append(current)
            field = None
            continue
        if current is None:
            continue
        f = FIELD.match(raw.strip())
        if f:
            field = f.group(1)
            value = f.group(2).strip()
            allowed = FIELDS[kind]
            if field in allowed["scalar"]:
                current["scalar"][field] = (n, value)
            elif field in allowed["list"]:
                current["list"].setdefault(field, [])
                if value:
                    current["list"][field].append((n, value))
            else:
                current["unknown"].append((n, field))
                field = None
            continue
        b = BULLET.match(raw)
        if b and field and field in FIELDS[kind]["list"]:
            current["list"].setdefault(field, []).append((n, b.group(1)))
    return entries


def parse_contract(doc: Doc, rep: Report) -> dict[str, list[dict]]:
    declared: dict[str, list[dict]] = {s: [] for s in CONTRACT_SECTIONS}
    seen: dict[str, tuple[str, int]] = {}
    for section in CONTRACT_SECTIONS:
        if section not in doc.sections:
            rep.error(doc.path, 0, section, "section-missing", f"contract has no '## {section}' section")
            continue
        if doc.is_none(section):
            continue
        if not doc.has_text(section):
            rep.error(doc.path, 0, section, "section-empty", f"'## {section}' is empty; write its entries or the single word none")
            continue
        for n, raw in doc.body(section):
            b = BULLET.match(raw)
            if not b:
                continue
            name, rest = split_name(b.group(1))
            if not name:
                rep.error(doc.path, n, section, "name-missing", "entry with no name")
                continue
            if not rest:
                rep.error(doc.path, n, f"{section}: {name}", "description-missing", "name with no description; every entry says what the lane must deliver")
            if PLACEHOLDER.match(name):
                rep.warn(doc.path, n, f"{section}: {name}", "placeholder-name", "name reads as a placeholder")
            if name in seen:
                other_section, other_line = seen[name]
                rep.error(doc.path, n, f"{section}: {name}", "name-duplicate", f"'{name}' already declared in '{other_section}' at line {other_line}; names are the handles other lanes use verbatim and must mean one thing")
                continue
            seen[name] = (section, n)
            declared[section].append({"name": name, "line": n, "description": rest})
    return declared


def check_entry_fields(entry: dict, doc: Doc, rep: Report) -> None:
    kind, where = entry["kind"], f"{entry['kind']}: {entry['name']}"
    for f in FIELDS[kind]["scalar"]:
        if f not in entry["scalar"]:
            rep.error(doc.path, entry["line"], where, "field-missing", f"no '{f}:'")
        elif not entry["scalar"][f][1]:
            rep.error(doc.path, entry["scalar"][f][0], where, "field-empty", f"'{f}:' is empty")
    for f in FIELDS[kind]["list"]:
        if f not in entry["list"]:
            rep.error(doc.path, entry["line"], where, "field-missing", f"no '{f}:'")
        elif not entry["list"][f]:
            rep.error(doc.path, entry["line"], where, "field-empty", f"'{f}:' has no entries")
    for n, f in entry["unknown"]:
        rep.warn(doc.path, n, where, "field-unknown", f"'{f}:' is not a field of a {kind} entry and is not checked")


def check_quest(entry: dict, doc: Doc, rep: Report) -> None:
    where = f"Quest: {entry['name']}"
    choice = entry["list"].get("Choice", [])
    consequence = entry["list"].get("Consequence", [])
    options, opt_lines = [], {}
    for n, text in choice:
        name, cost = split_name(text)
        if not cost:
            rep.error(doc.path, n, where, "choice-cost-missing", f"option '{name}' does not say what it costs; an option that costs nothing is not a side of a choice")
        if name in options:
            rep.error(doc.path, n, where, "choice-duplicate", f"option '{name}' listed twice")
            continue
        options.append(name)
        opt_lines[name] = n
    if choice and len(options) < 2:
        rep.error(doc.path, entry["line"], where, "choice-single", "the choice offers one option; a quest the player cannot decide has no choice in it")
    answered = []
    for n, text in consequence:
        name, effect = split_name(text)
        if not effect:
            rep.error(doc.path, n, where, "consequence-empty", f"'{name}' has no consequence written; say what changes, where it is seen and when")
        if name not in options and options:
            rep.error(doc.path, n, where, "consequence-unknown-option", f"'{name}' is not one of the options of this quest's choice")
            continue
        answered.append(name)
    for name in options:
        if name not in answered:
            rep.error(doc.path, opt_lines[name], where, "consequence-missing", f"option '{name}' has no consequence; a choice whose sides lead to the same world is not a choice")


def check_npc(entry: dict, doc: Doc, rep: Report) -> list[tuple[int, str]]:
    where = f"NPC: {entry['name']}"
    places: list[tuple[int, str]] = []
    for n, text in entry["list"].get("Schedule", []):
        parts = [p.strip() for p in SEP.split(text)]
        if len(parts) < 3 or not all(parts[:3]):
            rep.error(doc.path, n, where, "schedule-incomplete", "a schedule entry names when, in which place, and what they are doing there")
            continue
        places.append((n, parts[1]))
    for n, text in entry["list"].get("Lines", []):
        if not QUOTED.search(text):
            rep.error(doc.path, n, where, "line-unquoted", "a line entry carries the spoken line in quotes")
    return places


def check_scene(script_path: pathlib.Path, contract_path: pathlib.Path) -> dict:
    rep = Report()
    result = {
        "script": str(script_path),
        "contract": str(contract_path),
        "counts": {},
        "errors": rep.errors,
        "warnings": rep.warnings,
        "status": "FAIL",
    }
    for p in (script_path, contract_path):
        if not p.exists():
            rep.error(p, 0, "", "file-missing", "file does not exist")
    if rep.errors:
        return result

    script, contract = Doc(script_path), Doc(contract_path)
    for section in SCRIPT_SECTIONS:
        if section not in script.sections:
            rep.error(script.path, 0, section, "section-missing", f"script has no '## {section}' section")
    for section in SCRIPT_PROSE:
        if section in script.sections and not script.has_text(section):
            rep.error(script.path, 0, section, "section-empty", f"'## {section}' is empty")

    declared = parse_contract(contract, rep)
    place_names = {e["name"] for e in declared["Places"]}
    npc_names = {e["name"] for e in declared["NPCs"]}

    entries: dict[str, list[dict]] = {}
    for kind, section in ENTRY_KINDS.items():
        entries[kind] = parse_entries(script, section, kind, rep) if section in script.sections else []
        seen: dict[str, int] = {}
        for e in entries[kind]:
            if e["name"] in seen:
                rep.error(script.path, e["line"], f"{kind}: {e['name']}", "name-duplicate", f"a second {kind} with this name (first at line {seen[e['name']]})")
            seen[e["name"]] = e["line"]
            check_entry_fields(e, script, rep)

    used_places: list[tuple[int, str, str]] = []
    for kind in ENTRY_KINDS:
        for e in entries[kind]:
            where = f"{kind}: {e['name']}"
            if "Place" in e["scalar"] and e["scalar"]["Place"][1]:
                used_places.append((e["scalar"]["Place"][0], e["scalar"]["Place"][1], where))
    for e in entries["Quest"]:
        check_quest(e, script, rep)
    for e in entries["NPC"]:
        for n, place in check_npc(e, script, rep):
            used_places.append((n, place, f"NPC: {e['name']}"))
        if e["name"] not in npc_names:
            rep.error(script.path, e["line"], f"NPC: {e['name']}", "npc-undeclared", f"'{e['name']}' is not declared in the contract; the lane that builds them will never see the name")

    for n, place, where in used_places:
        if place not in place_names:
            rep.error(script.path, n, where, "place-undeclared", f"place '{place}' is not declared in '## Places' of the contract")

    script_text = script_path.read_text(encoding="utf-8")
    for section, items in declared.items():
        for e in items:
            if e["name"] not in script_text:
                rep.warn(contract.path, e["line"], f"{section}: {e['name']}", "name-unused", "declared in the contract and never named in the script")

    result["counts"] = {
        "places": len(place_names),
        "npcs": len(entries["NPC"]),
        "quests": len(entries["Quest"]),
        "points": len(entries["Point"]),
        "schedule_entries": sum(len(e["list"].get("Schedule", [])) for e in entries["NPC"]),
        "lines": sum(len(e["list"].get("Lines", [])) for e in entries["NPC"]),
        "props": len(declared["Props"]),
        "sounds": len(declared["Sounds"]),
        "events": len(declared["Events"]),
    }
    result["status"] = "FAIL" if rep.errors else "PASS"
    return result


def resolve(paths: list[str]) -> tuple[pathlib.Path, pathlib.Path]:
    if len(paths) == 2:
        return pathlib.Path(paths[0]), pathlib.Path(paths[1])
    p = pathlib.Path(paths[0])
    if p.is_file():
        raise SystemExit("give a scene folder, or the script and the contract as two paths")
    return p / "script.md", p / "contract.md"


def as_text(result: dict) -> str:
    out = []
    for kind in ("errors", "warnings"):
        for item in result[kind]:
            place = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
            where = f" [{item['where']}]" if item["where"] else ""
            out.append(f"{kind[:-1].upper()} {place}{where} {item['rule']}: {item['message']}")
    counts = ", ".join(f"{k} {v}" for k, v in result["counts"].items())
    out.append(f"{result['status']}: {len(result['errors'])} errors, {len(result['warnings'])} warnings" + (f" ({counts})" if counts else ""))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="a scene folder, or script.md and contract.md as two paths")
    ap.add_argument("--text", action="store_true", help="compact human list instead of JSON")
    ap.add_argument("--json", action="store_true", help="JSON (the default)")
    a = ap.parse_args()
    script_path, contract_path = resolve(a.paths)
    result = check_scene(script_path, contract_path)
    print(as_text(result) if a.text and not a.json else json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
