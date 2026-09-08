#!/usr/bin/env python3
"""Static gate for Luau: type errors, unknown API members, deprecated calls, strict-mode violations.

Usage:
  check_luau.py <file-or-dir> [...] [--json] [--allow-deprecated]

Runs luau-lsp analyze with the Roblox global types (install.sh / install.ps1 first). Exit status 1 when
any error remains; deprecated-API findings count as errors unless --allow-deprecated. Output lists every
finding with file:line so a fixer can go straight to it. This is the objective check the luau-reviewer
runs before reading anything, and the check luau-scripter runs before reporting.

How to get sources out of Studio: Script Sync (Studio -> folder), a Rojo project, or the Chrrxs MCP
export; execute_luau cannot write to disk. Each script is one .luau file; names ending in
.server.luau / .client.luau tell the analyzer which globals apply.
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).parent
BIN = HERE / ("luau-lsp.exe" if os.name == "nt" else "luau-lsp")
DEFS = HERE / "globalTypes.d.luau"
LINE = re.compile(r"^(?P<file>.+?)\((?P<line>\d+),(?P<col>\d+)\): (?P<kind>\w+): (?P<msg>.*)$")


def collect(paths):
    files = []
    for p in paths:
        p = pathlib.Path(p)
        if p.is_dir():
            files += [f for f in p.rglob("*") if f.suffix in (".luau", ".lua")]
        else:
            files.append(p)
    return files


def analyze(files, allow_deprecated=False):
    if not BIN.exists() or not DEFS.exists():
        raise SystemExit(f"luau-lsp or globalTypes.d.luau missing in {HERE}; run install.sh / install.ps1")
    cmd = [str(BIN), "analyze", f"--definitions={DEFS}", "--no-strict-dm-types", *map(str, files)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    findings = []
    for raw in (p.stdout + p.stderr).splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        kind = m["kind"]
        severity = "error"
        if kind == "DeprecatedApi":
            severity = "warning" if allow_deprecated else "error"
        elif kind in ("UnusedLocal", "UnusedVariable", "UnusedFunction", "UnusedImport", "LocalShadow", "ImplicitReturn"):
            severity = "info"
        findings.append({"file": m["file"], "line": int(m["line"]), "col": int(m["col"]), "kind": kind, "message": m["msg"], "severity": severity})
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+"); ap.add_argument("--json", action="store_true"); ap.add_argument("--allow-deprecated", action="store_true")
    a = ap.parse_args()
    files = collect(a.paths)
    findings = analyze(files, a.allow_deprecated)
    errors = [f for f in findings if f["severity"] == "error"]
    summary = {"files": len(files), "errors": len(errors), "warnings": sum(1 for f in findings if f["severity"] == "warning"),
               "info": sum(1 for f in findings if f["severity"] == "info"), "findings": findings}
    if a.json:
        print(json.dumps(summary, indent=1))
    else:
        for f in findings:
            print(f"{f['severity']:7} {f['file']}:{f['line']}:{f['col']}  {f['kind']}: {f['message']}")
        print(f"{len(files)} files, {len(errors)} errors, {summary['warnings']} warnings, {summary['info']} info")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
