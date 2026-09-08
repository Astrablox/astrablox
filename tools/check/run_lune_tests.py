#!/usr/bin/env python3
"""Run the Luau unit tests under game/src/tests with Lune (headless Luau runtime), or say honestly that it could not.

Usage:
  run_lune_tests.py [--root <checkout>] [--tests game/src/tests]

Finds `lune` on PATH (install: `rokit add lune` or https://lune-org.github.io/docs; on Windows also
`scoop install lune`). Runs every `*.spec.luau` / `*.test.luau` file under the tests folder with
`lune run <file>`, collects exit codes and output, prints a JSON summary and `LUNE TESTS: PASS | FAIL | NOT RUN`.
NOT RUN (exit 3) when lune is missing or the folder has no test files: a lane reports it as NOT RUN in
its GATE: marker, never as passed. Exit 1 when any test fails.
"""
from __future__ import annotations
import argparse, json, pathlib, shutil, subprocess, sys


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--root", default=None); ap.add_argument("--tests", default="game/src/tests")
    a = ap.parse_args()
    root = pathlib.Path(a.root or pathlib.Path(__file__).resolve().parents[2])
    lune = shutil.which("lune")
    tests = sorted(list((root / a.tests).glob("**/*.spec.luau")) + list((root / a.tests).glob("**/*.test.luau"))) if (root / a.tests).exists() else []
    if not lune or not tests:
        reason = "lune not on PATH" if not lune else f"no *.spec.luau or *.test.luau under {a.tests}"
        print(json.dumps({"status": "NOT RUN", "reason": reason, "tests": len(tests)}, indent=1)); print("LUNE TESTS: NOT RUN"); sys.exit(3)
    results = []
    for t in tests:
        r = subprocess.run([lune, "run", str(t)], capture_output=True, text=True, cwd=root)
        results.append({"file": str(t.relative_to(root)), "exit": r.returncode, "tail": (r.stdout + r.stderr)[-800:]})
    failed = [r for r in results if r["exit"] != 0]
    print(json.dumps({"status": "FAIL" if failed else "PASS", "ran": len(results), "failed": len(failed), "results": results}, indent=1))
    print("LUNE TESTS:", "FAIL" if failed else "PASS"); sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
