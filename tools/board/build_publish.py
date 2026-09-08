#!/usr/bin/env python3
"""build_publish.py: publish a build of a scene into builds/<n>/ so the lead, the judges and the owner
look at one numbered folder instead of hunting renders across work dirs (docs/contract.md §8).

What it does: takes the next build number, copies the renders, the target frame, optional Studio
captures and .rbxl into builds/<n>/, writes one side-by-side PNG per render against the target
(Pillow, inline), writes CHANGES.md (number, scene, time, what changed, where to look,
file list) and, when game/scenes/<id>/card.md exists, rewrites its `Current build:` line.
Prints `BUILD <n> READY builds/<n>/` last; that line is the §3 signal text to send to the lead / studio.

When to use: lead after assembling a scene in Blender (renders from render_views.py); studio after a
Studio capture pass (--captures). Not for single pieces: those go through task reports.

Run:
  python tools/board/build_publish.py --scene harbour --renders work/harbour/renders \\
      --target game/scenes/harbour/target.png [--captures work/harbour/captures] [--rbxl work/harbour.rbxl] \\
      --changes "Pier kit replaced blockout; lighting matched to target; quay wall still flat"
Returns exit 0 with the folder path; exit 1 when the renders dir or the target is missing.
"""
import argparse
import importlib.util
import pathlib
import re
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("astra_board", HERE / "board.py")
board = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(board)


def compose(left, right, out, labels=("Render", "Target"), height=900):
    """Render beside target in one PNG with labels; returns 0, or 3 when Pillow is missing (no file written)."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("SIDE_BY_SIDE skipped: Pillow not installed", file=sys.stderr)
        return 3
    if not pathlib.Path(right).exists():
        return 2
    imgs = []
    for path in (left, right):
        im = Image.open(path).convert("RGB")
        im = im.resize((int(im.width * height / im.height), height))
        imgs.append(im)
    gap, top = 12, 28
    canvas = Image.new("RGB", (imgs[0].width + gap + imgs[1].width, height + top), (18, 18, 20))
    d = ImageDraw.Draw(canvas)
    x = 0
    for im, label in zip(imgs, labels):
        canvas.paste(im, (x, top)); d.text((x + 6, 7), label, fill=(230, 230, 230)); x += im.width + gap
    canvas.save(out)
    print("SIDE_BY_SIDE", out)
    return 0


def next_build(builds):
    builds.mkdir(parents=True, exist_ok=True)
    nums = [int(p.name) for p in builds.iterdir() if p.is_dir() and p.name.isdigit()]
    return (max(nums) + 1) if nums else 1


def copy_tree(src, dst):
    files = []
    src = pathlib.Path(src)
    if not src.is_dir():
        return files
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.rglob("*")):
        if p.is_file():
            rel = p.relative_to(src)
            (dst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst / rel)
            files.append(dst / rel)
    return files


def update_card(card, n, folder_rel):
    text = card.read_text(encoding="utf-8")
    line = f"Current build: {n}  ({folder_rel}/)"
    if re.search(r"^Current build:.*$", text, re.M):
        text = re.sub(r"^Current build:.*$", line, text, count=1, flags=re.M)
    else:
        text = text.rstrip("\n") + "\n" + line + "\n"
    card.write_text(text, encoding="utf-8")


def publish(root, scene, renders, target, changes, captures=None, rbxl=None):
    root = pathlib.Path(root)
    renders, target = pathlib.Path(renders), pathlib.Path(target)
    if not renders.is_dir():
        raise SystemExit(f"renders dir missing: {renders}")
    if not target.is_file():
        raise SystemExit(f"target frame missing: {target}")
    n = next_build(root / "builds")
    folder = root / "builds" / f"{n:03d}"
    folder.mkdir(parents=True)
    files = copy_tree(renders, folder / "renders")
    shutil.copy2(target, folder / "target.png")
    files.append(folder / "target.png")
    if captures:
        files += copy_tree(captures, folder / "captures")
    if rbxl and pathlib.Path(rbxl).is_file():
        dst = folder / pathlib.Path(rbxl).name
        shutil.copy2(rbxl, dst)
        files.append(dst)
    comparisons = []
    for r in sorted((folder / "renders").glob("*.png")):
        out = folder / f"side_by_side_{r.stem}.png"
        if compose(str(r), str(folder / "target.png"), str(out), (f"Render {r.stem} (build {n})", "Target"), 900) == 0:
            comparisons.append(out)
            files.append(out)
    rel = lambda p: p.relative_to(root).as_posix()
    look = [rel(c) for c in comparisons] or [rel(f) for f in files if f.parent.name == "renders"]
    if captures:
        look += [rel(f) for f in files if f.parent.name == "captures"][:3]
    changes_md = folder / "CHANGES.md"
    changes_md.write_text("\n".join([
        f"# Build {n} — scene {scene}",
        f"Time: {board.now_iso()}",
        f"Scene: {scene} (game/scenes/{scene}/card.md)",
        "",
        "## What changed",
        changes.strip(),
        "",
        "## Where to look",
        *(f"- {p}" for p in look),
        "",
        "## Files",
        *(f"- {rel(f)}" for f in sorted(files)),
        "",
    ]), encoding="utf-8")
    card = root / "game" / "scenes" / scene / "card.md"
    if card.is_file():
        update_card(card, n, rel(folder))
    print(f"BUILD {n} READY {rel(folder)}/")
    return folder


def main(argv=None):
    ap = argparse.ArgumentParser(prog="build_publish.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root")
    ap.add_argument("--scene", required=True)
    ap.add_argument("--renders", required=True, help="folder with render PNGs (render_views.py --out)")
    ap.add_argument("--target", required=True, help="target frame PNG")
    ap.add_argument("--captures", help="folder with Studio captures")
    ap.add_argument("--rbxl", help="place file to include")
    ap.add_argument("--changes", required=True, help="what changed since the previous build, one paragraph")
    a = ap.parse_args(argv)
    publish(board.find_root(a.root), a.scene, a.renders, a.target, a.changes, a.captures, a.rbxl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
