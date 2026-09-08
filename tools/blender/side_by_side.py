#!/usr/bin/env python3
"""side_by_side.py: put a render and its target frame next to each other in one PNG with labels, so a
judge (or the owner) compares them in one look instead of switching windows.

Plain Python (no Blender). Needs Pillow; without it the tool prints a warning, writes nothing and
exits 3, so a pipeline can continue and the report can say the comparison is missing.

Run:
  python tools/blender/side_by_side.py --left out/renders/final_far.png --right game/scenes/harbour/target.png \\
      --out builds/007/side_by_side_far.png [--labels "Render (build 7, far)" "Target"] [--height 900]

Both images are scaled to the same height (default: the smaller of the two, capped by --height),
placed left | right with a thin gutter and a label strip on top. Prints SIDE_BY_SIDE <path>.
Exit 0 written, 2 input missing, 3 Pillow missing.
"""
import argparse
import os
import sys


def compose(left, right, out, labels=("Render", "Target"), height=None):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("WARNING side_by_side: Pillow not installed (pip install pillow); no comparison image written", file=sys.stderr)
        return 3
    for p in (left, right):
        if not os.path.exists(p):
            print(f"side_by_side: input missing: {p}", file=sys.stderr)
            return 2
    a = Image.open(left).convert("RGB")
    b = Image.open(right).convert("RGB")
    h = min(a.height, b.height)
    if height:
        h = min(h, height)

    def fit(im):
        return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)

    a, b = fit(a), fit(b)
    gutter, strip = 12, 36
    canvas = Image.new("RGB", (a.width + b.width + gutter, h + strip), (18, 18, 20))
    canvas.paste(a, (0, strip))
    canvas.paste(b, (a.width + gutter, strip))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    draw.text((10, 9), labels[0], fill=(235, 235, 235), font=font)
    draw.text((a.width + gutter + 10, 9), labels[1], fill=(235, 235, 235), font=font)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    canvas.save(out)
    print("SIDE_BY_SIDE", out)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="side_by_side.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--left", required=True, help="render PNG")
    ap.add_argument("--right", required=True, help="target frame PNG")
    ap.add_argument("--out", required=True)
    ap.add_argument("--labels", nargs=2, default=("Render", "Target"), metavar=("LEFT", "RIGHT"))
    ap.add_argument("--height", type=int, default=900, help="max height in pixels")
    a = ap.parse_args(argv)
    return compose(a.left, a.right, a.out, tuple(a.labels), a.height)


if __name__ == "__main__":
    sys.exit(main())
