#!/usr/bin/env python3
"""Turn upload results into a kit manifest and the Luau that inserts the whole kit into Studio.

Usage:
  kit_manifest.py uploads.jsonl --out kit.json --luau insert_kit.luau [--folder KayKitDungeon]

uploads.jsonl is the line-per-asset output of `upload.py --batch` (each line: catalog item + "upload"
with roblox_asset_id). The manifest keeps name, pack, tags, triangles, animations and asset id, so a
role can pick pieces by tag without opening Studio. The Luau inserts every asset into
ServerStorage.StyleKit/<folder> in one execute_luau call and returns what loaded and what did not.
"""
from __future__ import annotations
import argparse, json, pathlib

LUAU = '''--!strict
local InsertService = game:GetService("InsertService")
local ServerStorage = game:GetService("ServerStorage")
local kit = ServerStorage:FindFirstChild("StyleKit") or Instance.new("Folder")
kit.Name = "StyleKit"; kit.Parent = ServerStorage
local folder = kit:FindFirstChild("FOLDER") or Instance.new("Folder")
folder.Name = "FOLDER"; folder.Parent = kit
local items: {{name: string, id: number, tags: string}} = ITEMS
local ok, failed = 0, {}
for _, item in items do
	if folder:FindFirstChild(item.name) then ok += 1; continue end
	local success, result = pcall(function() return InsertService:LoadAsset(item.id) end)
	if success then
		local model = result :: Model
		local inner = model:GetChildren()[1]
		local target = inner or model
		target.Name = item.name
		target:SetAttribute("KitTags", item.tags)
		target:SetAttribute("AssetId", item.id)
		target.Parent = folder
		if inner then model:Destroy() end
		for _, d in target:GetDescendants() do
			if d:IsA("LuaSourceContainer") then (d :: any).Enabled = false end
		end
		ok += 1
	else
		table.insert(failed, item.name .. ":" .. tostring(result))
	end
end
return ("KIT FOLDER loaded=%d failed=%d %s"):format(ok, #failed, table.concat(failed, "; "))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("uploads"); ap.add_argument("--out", default="kit.json"); ap.add_argument("--luau", default="insert_kit.luau")
    ap.add_argument("--folder", default="Kit")
    a = ap.parse_args()
    items = []
    for line in pathlib.Path(a.uploads).read_text().splitlines():
        line = line.strip()
        if not line.startswith("{"): continue
        it = json.loads(line)
        aid = (it.get("upload") or {}).get("roblox_asset_id")
        if not aid: continue
        items.append({"name": it["name"], "pack": it["pack"], "tags": it.get("tags", []), "triangles": it.get("triangles"),
                      "animations": it.get("animations", []), "asset_id": int(aid), "license": it.get("license"), "thumb": it.get("thumb")})
    pathlib.Path(a.out).write_text(json.dumps({"folder": a.folder, "items": items}, indent=1))
    luau_items = "{" + ", ".join(f'{{name = "{i["name"]}", id = {i["asset_id"]}, tags = "{",".join(i["tags"])}"}}' for i in items) + "}"
    pathlib.Path(a.luau).write_text(LUAU.replace("FOLDER", a.folder).replace("ITEMS", luau_items))
    print(json.dumps({"items": len(items), "manifest": a.out, "luau": a.luau}))


if __name__ == "__main__":
    main()
