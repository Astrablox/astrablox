--!strict
-- Build a MaterialVariant (for Parts and Terrain) and a SurfaceAppearance template (for MeshParts)
-- from uploaded texture asset ids. Run through Studio MCP execute_luau (Edit) after upload.py has
-- returned ids for the maps in a textures.py recipe. Replace the placeholders.
local MaterialService = game:GetService("MaterialService")
local ServerStorage = game:GetService("ServerStorage")

local NAME = "MATERIAL_NAME"            -- e.g. CastleBrickRed
local BASE = Enum.Material.Cobblestone  -- the built-in material this variant overrides on Parts
local COLOR = "rbxassetid://COLOR_ID"
local NORMAL = "rbxassetid://NORMAL_ID"
local ROUGH = "rbxassetid://ROUGHNESS_ID"
local METAL = "rbxassetid://METALNESS_ID" -- "" when the set has no metalness map
local STUDS_PER_TILE = 8                -- texel density on Parts: how many studs one tile covers

local variant = MaterialService:FindFirstChild(NAME) or Instance.new("MaterialVariant")
variant.Name = NAME
variant.BaseMaterial = BASE
variant.ColorMap = COLOR
variant.NormalMap = NORMAL
variant.RoughnessMap = ROUGH
if METAL ~= "" then variant.MetalnessMap = METAL end
variant.StudsPerTile = STUDS_PER_TILE
variant.Parent = MaterialService

local kit = ServerStorage:FindFirstChild("StyleKit") or Instance.new("Folder")
kit.Name = "StyleKit"; kit.Parent = ServerStorage
local mats = kit:FindFirstChild("Materials") or Instance.new("Folder")
mats.Name = "Materials"; mats.Parent = kit
local sa = mats:FindFirstChild(NAME) or Instance.new("SurfaceAppearance")
sa.Name = NAME
sa.ColorMap = COLOR
sa.NormalMap = NORMAL
sa.RoughnessMap = ROUGH
if METAL ~= "" then sa.MetalnessMap = METAL end
sa.Parent = mats

return ("MATERIAL %s variant=%s surfaceAppearance=%s (clone the SurfaceAppearance under a MeshPart; set Part.Material=%s and Part.MaterialVariant=%s)")
	:format(NAME, variant:GetFullName(), sa:GetFullName(), tostring(BASE), NAME)
