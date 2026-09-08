#!/usr/bin/env python3
"""Upload a GLB (or image/audio) to Roblox through Open Cloud and return the asset id.

Usage:
  upload.py --file model.glb --name "Iron portcullis" [--type Model|Image|Audio] [--slug iron_portcullis] [--dry-run]
  upload.py --batch catalog.json --root kits/ --prefix "KayKit " [--limit 50]   # bulk upload a CC0 catalog

Needs ROBLOX_API_KEY with the assets write scope and ROBLOX_CREATOR_USER_ID or ROBLOX_CREATOR_GROUP_ID.
Documented limits: 20 MB per file; audio 100/month for ID-verified accounts; moderation takes time,
so the returned asset id may not render for anyone until it clears. Provenance is written per asset.
"""
from __future__ import annotations
import argparse, json, mimetypes, pathlib, sys, time, urllib.request, urllib.error, uuid
from common import log, key, record, sha256, ROBLOX_MAX_FILE_BYTES

API = "https://apis.roblox.com/assets/v1"
MIME = {".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".fbx": "model/fbx", ".rbxm": "model/x-rbxm",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".wav": "audio/wav"}
TYPE_FOR = {".glb": "Model", ".gltf": "Model", ".fbx": "Model", ".rbxm": "Model", ".png": "Image", ".jpg": "Image", ".jpeg": "Image",
            ".mp3": "Audio", ".ogg": "Audio", ".wav": "Audio"}


def creator() -> dict:
    if key("ROBLOX_CREATOR_GROUP_ID"):
        return {"groupId": key("ROBLOX_CREATOR_GROUP_ID")}
    if key("ROBLOX_CREATOR_USER_ID"):
        return {"userId": key("ROBLOX_CREATOR_USER_ID")}
    raise SystemExit("set ROBLOX_CREATOR_USER_ID or ROBLOX_CREATOR_GROUP_ID")


def multipart(fields: dict, file_field: str, path: pathlib.Path, mime: str) -> tuple[bytes, str]:
    boundary = "----astrablox" + uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\nContent-Type: application/json\r\n\r\n{v}\r\n".encode()
    body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{file_field}\"; filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n".encode()
    body += path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    return body, boundary


def create_asset(path: pathlib.Path, name: str, asset_type: str, description: str = "") -> dict:
    mime = MIME.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    req_json = json.dumps({"assetType": asset_type, "displayName": name[:50], "description": description[:1000],
                           "creationContext": {"creator": creator()}})
    body, boundary = multipart({"request": req_json}, "fileContent", path, mime)
    req = urllib.request.Request(f"{API}/assets", data=body, method="POST",
                                 headers={"x-api-key": key("ROBLOX_API_KEY"), "Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def wait_operation(op_path: str, timeout: float = 600) -> dict:
    """Poll assets/v1/operations/{id} with backoff until done; return the final operation."""
    op_id = op_path.split("/")[-1]
    delay, waited = 2.0, 0.0
    while waited < timeout:
        req = urllib.request.Request(f"{API}/operations/{op_id}", headers={"x-api-key": key("ROBLOX_API_KEY")})
        with urllib.request.urlopen(req, timeout=60) as r:
            op = json.load(r)
        if op.get("done"):
            return op
        time.sleep(delay); waited += delay; delay = min(delay * 1.6, 20)
    raise TimeoutError(f"operation {op_id} not done after {timeout}s")


def upload(path: pathlib.Path, name: str, asset_type: str | None, slug: str | None, dry_run: bool, description: str = "") -> dict:
    asset_type = asset_type or TYPE_FOR.get(path.suffix.lower(), "Model")
    if path.stat().st_size > ROBLOX_MAX_FILE_BYTES:
        raise SystemExit(f"{path} exceeds 20 MB")
    digest = sha256(path)
    if dry_run or not key("ROBLOX_API_KEY"):
        res = {"dry_run": True, "file": str(path), "sha256": digest, "assetType": asset_type, "name": name}
        if slug: record(slug, "upload", **res)
        return res
    op = create_asset(path, name, asset_type, description)
    final = wait_operation(op["path"])
    resp = final.get("response", {})
    asset_id = (resp.get("assetId") or (resp.get("path", "").split("/")[-1] if resp.get("path") else None))
    res = {"file": str(path), "sha256": digest, "assetType": asset_type, "name": name, "roblox_asset_id": asset_id,
           "revision_id": resp.get("revisionId"), "moderation": resp.get("moderationResult"), "operation": op.get("path")}
    if slug: record(slug, "upload", source="open-cloud", **res)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file"); ap.add_argument("--name"); ap.add_argument("--type"); ap.add_argument("--slug")
    ap.add_argument("--description", default="")
    ap.add_argument("--batch", help="catalog.json from kit_catalog.py"); ap.add_argument("--root", help="kits root for --batch")
    ap.add_argument("--prefix", default=""); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--only-tag")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.batch:
        cat = json.load(open(a.batch)); root = pathlib.Path(a.root or ".")
        out = []; n = 0
        for item in cat:
            if not item.get("roblox_ok"): continue
            if a.only_tag and a.only_tag not in item.get("tags", []): continue
            p = root / item["file"]
            if p.suffix.lower() == ".gltf":
                # a .gltf with external .bin/.png cannot be sent as one file: pack it into a temporary .glb
                import shutil, subprocess, tempfile
                tmp = pathlib.Path(tempfile.gettempdir()) / "astrablox-pack" / (p.stem.replace(".gltf", "") + ".glb")
                tmp.parent.mkdir(parents=True, exist_ok=True)
                cli = shutil.which("gltf-transform")
                cmd = [cli, "copy", str(p), str(tmp)] if cli else ["npx", "-y", "@gltf-transform/cli", "copy", str(p), str(tmp)]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                p = tmp
            elif p.suffix.lower() != ".glb":
                continue
            try:
                res = upload(p, f"{a.prefix}{item['name']}", "Model", None, a.dry_run, f"{item['pack']} {item['license']}")
            except (urllib.error.HTTPError, TimeoutError) as e:
                res = {"file": str(p), "error": str(e)}
                log("upload error", p.name, e)
            item_out = {**item, "upload": res}; out.append(item_out); n += 1
            print(json.dumps(item_out), flush=True)
            if a.limit and n >= a.limit: break
            if not a.dry_run: time.sleep(1.0)
        return
    if not a.file or not a.name:
        ap.error("--file and --name required (or --batch)")
    print(json.dumps(upload(pathlib.Path(a.file), a.name, a.type, a.slug, a.dry_run, a.description), indent=1))


if __name__ == "__main__":
    main()
