--!strict
-- Insert an uploaded asset into the style kit container. Run through Studio MCP execute_luau (Edit).
-- Replace ASSET_ID and ASSET_NAME. Requires the uploading account to own the asset (or the place's
-- security setting "Allow Loading Third Party Assets" for assets it does not own).
local InsertService = game:GetService("InsertService")
local ServerStorage = game:GetService("ServerStorage")

local kit = ServerStorage:FindFirstChild("StyleKit") or Instance.new("Folder")
kit.Name = "StyleKit"
kit.Parent = ServerStorage

local ok, result = pcall(function()
	return InsertService:LoadAsset(ASSET_ID)
end)
if not ok then
	return "LOAD_FAILED " .. tostring(result)
end
local model = result :: Model
local inner = model:GetChildren()[1]
if inner then
	inner.Name = "ASSET_NAME"
	inner.Parent = kit
	model:Destroy()
else
	model.Name = "ASSET_NAME"
	model.Parent = kit
end
local target = kit:FindFirstChild("ASSET_NAME")
local parts, tris, scripts = 0, "n/a", 0
for _, d in (target and target:GetDescendants() or {}) do
	if d:IsA("BasePart") then parts += 1 end
	if d:IsA("LuaSourceContainer") then scripts += 1 end
end
local size = target and target:IsA("Model") and target:GetExtentsSize() or (target and target:IsA("BasePart") and target.Size) or Vector3.zero
return ("INSERTED %s parts=%d scripts=%d size=%s"):format("ASSET_NAME", parts, scripts, tostring(size))
