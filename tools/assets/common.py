"""Shared configuration, logging and provenance for the AstraBlox asset tools.

Environment (all optional; a missing key turns the step that needs it into a dry run):
  OPENAI_API_KEY            concept images (gpt-image-2)
  TRIPO_API_KEY             image -> 3D (Tripo)
  ROBLOX_API_KEY            Open Cloud assets upload
  ROBLOX_CREATOR_USER_ID    or ROBLOX_CREATOR_GROUP_ID: who owns uploaded assets
  ASTRA_ASSET_ROOT          where generated files go (default: ./assets-work)
"""
from __future__ import annotations
import json, os, sys, time, hashlib, pathlib, datetime

ROOT = pathlib.Path(os.environ.get("ASTRA_ASSET_ROOT", "assets-work")).resolve()
ROBLOX_MAX_TRIS = 20000          # engine refuses a MeshPart above this at import
ROBLOX_MAX_FILE_BYTES = 20 * 1024 * 1024
ROBLOX_TARGET_TRIS = 10000       # working target per mesh for kit pieces
TEXTURE_MAX = 1024               # UV-space texture size Roblox renders at full detail


def log(*a):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}]", *a, file=sys.stderr, flush=True)


def key(name: str) -> str | None:
    return os.environ.get(name) or None


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def asset_dir(slug: str) -> pathlib.Path:
    d = ROOT / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def provenance_path(slug: str) -> pathlib.Path:
    return asset_dir(slug) / "provenance.json"


def read_provenance(slug: str) -> dict:
    p = provenance_path(slug)
    return json.loads(p.read_text()) if p.exists() else {"slug": slug, "steps": []}


def record(slug: str, step: str, **fields) -> dict:
    """Append one step to the asset's provenance file. Every tool writes here; nothing is silent."""
    prov = read_provenance(slug)
    entry = {"step": step, "at": datetime.datetime.utcnow().isoformat() + "Z", **fields}
    prov["steps"].append(entry)
    for k, v in fields.items():
        if k in ("concept_png", "glb", "glb_optimized", "roblox_asset_id", "tripo_task_id", "license", "source"):
            prov[k] = v
    provenance_path(slug).write_text(json.dumps(prov, indent=1))
    return prov


def slugify(s: str) -> str:
    out = "".join(c.lower() if c.isalnum() else "_" for c in s).strip("_")
    while "__" in out:
        out = out.replace("__", "_")
    return out[:60]
