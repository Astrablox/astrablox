#!/usr/bin/env python3
"""Search the Roblox Creator Store from the shell and get the facts that decide whether an asset is usable.

Usage:
  store_search.py "storm dragon rigged" [--limit 10] [--free] [--no-scripts] [--max-tris 20000] [--category models|audio|decals|meshes|plugins] [--json]

Returns per asset: id, name, creator, triangles, meshParts, animations, scripts (hasScripts), votes, free/paid,
category path, object types. No API key: uses the public toolbox-service endpoint the Studio toolbox uses.
The official Open Cloud search (POST /toolbox-service/v2/assets:search) needs an API key; switch to it if this
endpoint disappears. The output feeds insert_asset in Studio MCP; an asset with scripts stays quarantined.
"""
from __future__ import annotations
import argparse, json, sys, urllib.request, urllib.parse

BASE = "https://apis.roblox.com/toolbox-service/v1"
CATEGORY = {"models": 10, "decals": 13, "audio": 9, "meshes": 40, "plugins": 38, "videos": 62, "fonts": 73}


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "astrablox-asset-search/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def search(keyword: str, category: str = "models", limit: int = 10) -> list[dict]:
    cat = CATEGORY.get(category, category)
    q = urllib.parse.urlencode({"keyword": keyword, "limit": limit})
    res = get(f"{BASE}/marketplace/{cat}?{q}")
    ids = [str(x["id"]) for x in res.get("data", [])]
    if not ids:
        return []
    det = get(f"{BASE}/items/details?assetIds={','.join(ids)}")
    out = []
    for item in det.get("data", []):
        a = item.get("asset", {}); c = item.get("creator", {}); v = item.get("voting", {}); f = item.get("fiatProduct", {}) or {}
        tech = a.get("modelTechnicalDetails") or {}
        mesh = tech.get("objectMeshSummary") or {}
        counts = tech.get("instanceCounts") or {}
        out.append({
            "id": a.get("id"), "name": a.get("name"), "creator": c.get("name"), "creator_verified": c.get("isVerifiedCreator"),
            "triangles": mesh.get("triangles"), "meshParts": counts.get("meshPart"), "animations": counts.get("animation"),
            "scripts": counts.get("script"), "hasScripts": a.get("hasScripts"), "audio": counts.get("audio"),
            "upVotes": v.get("upVotes"), "downVotes": v.get("downVotes"), "upVotePercent": v.get("upVotePercent"),
            "free": f.get("isFree", True), "purchasable": f.get("purchasable"),
            "category": a.get("categoryPath"), "objectTypes": a.get("objectTypes"), "updated": a.get("updatedUtc"),
            "description": (a.get("description") or "")[:200],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("keyword"); ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--category", default="models"); ap.add_argument("--free", action="store_true")
    ap.add_argument("--no-scripts", action="store_true"); ap.add_argument("--max-tris", type=int)
    ap.add_argument("--min-votes", type=int, default=0); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rows = search(a.keyword, a.category, a.limit)
    if a.free: rows = [r for r in rows if r["free"]]
    if a.no_scripts: rows = [r for r in rows if not r["hasScripts"]]
    if a.max_tris: rows = [r for r in rows if (r["triangles"] or 0) <= a.max_tris]
    rows = [r for r in rows if (r["upVotes"] or 0) >= a.min_votes]
    if a.json:
        print(json.dumps(rows, indent=1)); return
    for r in rows:
        flags = ("SCRIPTS " if r["hasScripts"] else "") + ("" if r["free"] else "PAID ")
        print(f"{r['id']:>16}  {r['name'][:44]:44}  tris={r['triangles'] or '?':>6}  meshParts={r['meshParts'] or 0:<3} anim={r['animations'] or 0:<3} votes={r['upVotes'] or 0:>4}/{r['upVotePercent'] or 0:>3}%  {flags}{r['category'] or ''}  by {r['creator']}")


if __name__ == "__main__":
    main()
