#!/usr/bin/env python3
"""blender.py: run a bpy script in headless Blender, finding the binary automatically.

What it does: launches `blender -b [file.blend] --python <script> -- <args>` and returns Blender's
exit code. Use it for every script in tools/blender/bpy/ instead of calling Blender directly, so the
same command works on Windows, macOS and Linux and in CI.

Usage:
  python tools/blender/blender.py <script.py> [--blend file.blend] [-- args passed to the script]
  python tools/blender/blender.py --which          # print the Blender binary that would be used
  python tools/blender/blender.py <script.py> -- --help   # the bpy script's own help

Set BLENDER=<path to binary> to force a binary. Otherwise searches PATH, then the usual Windows,
macOS and Linux install locations, newest version first. Prints the command it runs.
"""
import glob
import os
import shutil
import subprocess
import sys


def find_blender() -> str:
    env = os.environ.get("BLENDER")
    if env and os.path.exists(env):
        return env
    on_path = shutil.which("blender") or shutil.which("blender.exe")
    if on_path:
        return on_path
    patterns = [
        r"C:\Program Files\Blender Foundation\Blender *\blender.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender Foundation\Blender *\blender.exe"),
        "/Applications/Blender.app/Contents/MacOS/Blender",
        "/Applications/Blender*/Blender.app/Contents/MacOS/Blender",
        os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender"),
        "/usr/bin/blender", "/snap/bin/blender", "/opt/blender*/blender", os.path.expanduser("~/blender*/blender"),
    ]
    hits = []
    for p in patterns:
        hits += glob.glob(p)
    if not hits:
        sys.exit("Blender not found. Install Blender 4.x (winget install BlenderFoundation.Blender / "
                 "brew install --cask blender / apt install blender) or set BLENDER=<path to binary>.")
    return sorted(hits)[-1]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--which":
        print(find_blender())
        return 0
    script, rest = argv[0], argv[1:]
    if not os.path.exists(script):
        sys.exit(f"script not found: {script}")
    blend = None
    if rest[:1] == ["--blend"]:
        blend = rest[1]
        rest = rest[2:]
    if rest[:1] == ["--"]:
        rest = rest[1:]
    cmd = [find_blender(), "-b"] + ([blend] if blend else []) + ["--python", script, "--"] + rest
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
