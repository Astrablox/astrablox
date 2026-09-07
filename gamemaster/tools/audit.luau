--!strict
-- AstraBlox structural audit. Game Master runs this through execute_luau (datamodel_type = "Edit")
-- after every build step and reads the section that matters. One call, one report, no guessing.
-- Output is plain text, one fact per line, prefixed with the section name.

local out: { string } = {}
local function add(s: string) table.insert(out, s) end
local function count(root: Instance, pred: (Instance) -> boolean): number
	local n = 0
	for _, d in root:GetDescendants() do if pred(d) then n += 1 end end
	return n
end

-- SCRIPTS -------------------------------------------------------------------
-- Inventory the entire DataModel, including Workspace assets and StarterPack.
-- No source-length or suspicious-word failure gates: behavior needs separate review.
local scripts, unreadable = 0, 0
for _, d in game:GetDescendants() do
    if d:IsA("LuaSourceContainer") then
        scripts += 1
        local ok, src = pcall(function() return (d :: any).Source :: string end)
        if ok then
            local lines = select(2, src:gsub("\n", "\n")) + 1
            local flags = {}
            local padded = " " .. src
            if padded:find("[^%.%w_]wait%(") or padded:find("[^%.%w_]spawn%(") or padded:find("[^%.%w_]delay%(") then
                table.insert(flags, "REVIEW_LEGACY_API_CANDIDATE")
            end
            local enabled = "module"
            if d:IsA("BaseScript") then enabled = tostring(d.Enabled) end
            add(("SCRIPT %s %s lines=%d enabled=%s reviewLeads=%s"):format(d.ClassName, d:GetFullName(), lines, enabled, table.concat(flags, ",")))
        else
            unreadable += 1
            add(("SCRIPT %s %s source=UNREADABLE"):format(d.ClassName, d:GetFullName()))
        end
    end
end
add(("SCRIPTS total=%d unreadable=%d lengthIsInventoryOnly=true"):format(scripts, unreadable))
local remotes = count(game, function(i) return i:IsA("RemoteEvent") or i:IsA("RemoteFunction") end)
add(("REMOTES total=%d scope=wholeDataModel"):format(remotes))
add("AUDIT readOnly=true behavioralAcceptance=NOT_TESTED budgets=architectureOwned")

-- WORLD ---------------------------------------------------------------------
local ws = game:GetService("Workspace")
local parts = count(ws, function(i) return i:IsA("BasePart") end)
add(("WORLD parts=%d"):format(parts))
local map = ws:FindFirstChild("Map")
if map then
	for _, room in map:GetChildren() do
		local props = room:FindFirstChild("Props")
		local detail = room:FindFirstChild("ArchDetail")
		local blockout = room:FindFirstChild("Blockout")
		local rp = props and count(props, function(i) return i:IsA("BasePart") end) or -1
		local dp = detail and count(detail, function(i) return i:IsA("BasePart") end) or -1
		-- Blockout is throwaway scaffolding; anything left here after the rebuild is unfinished work.
		local bp = blockout and count(blockout, function(i) return i:IsA("BasePart") end) or 0
		local bad = 0
		for _, folder in { props, detail } do
			if folder then
				for _, p in folder:GetDescendants() do
					if p:IsA("BasePart") and (not p.Anchored or p.CanCollide) then bad += 1 end
				end
			end
		end
		add(("ZONE %s parts=%d props=%d detail=%d blockoutLeftover=%d unanchoredOrCollidableDetail=%d"):format(room.Name,
			count(room, function(i) return i:IsA("BasePart") end), rp, dp, bp, bad))
	end
else
	add("WORLD Map folder MISSING")
end
add(("SPAWNS total=%d"):format(count(ws, function(i) return i:IsA("SpawnLocation") end)))
local meshes = count(ws, function(i) return i:IsA("MeshPart") end)
local plainParts = count(ws, function(i) return i:IsA("Part") end)
local surfApp = count(ws, function(i) return i:IsA("SurfaceAppearance") end)
local emissive = 0
for _, o in ws:GetDescendants() do
	if o:IsA("SurfaceAppearance") then
		local ok, v = pcall(function() return (o :: any).EmissiveMaskContent end)
		if ok and v ~= nil and tostring(v) ~= "" and tostring(v) ~= "Content()" then emissive += 1 end
	end
end
local variants = count(game:GetService("MaterialService"), function(i) return i:IsA("MaterialVariant") end)
local procedural = count(ws, function(i) return i.ClassName == "ProceduralModel" end)
add(("BUILD meshParts=%d plainParts=%d surfaceAppearances=%d emissiveMasks=%d materialVariants=%d proceduralModels=%d"):format(
	meshes, plainParts, surfApp, emissive, variants, procedural))
add(("BUILD workspaceStreaming=%s meshStreamingLoDs=%s"):format(tostring(ws.StreamingEnabled),
	tostring((pcall(function() return (ws :: any).MeshStreamingAndImprovedLoDs end)) and (ws :: any).MeshStreamingAndImprovedLoDs or "n/a")))
add("BUILD inventoryOnly=true; ratios describe what the world is made of, not its quality")

-- LIGHTING ------------------------------------------------------------------
local L = game:GetService("Lighting")
-- LightingStyle replaced Lighting.Technology (deprecated). Some properties need capabilities
-- execute_luau does not have → pcall and report n/a.
local styleOk, style = pcall(function() return tostring((L :: any).LightingStyle) end)
local prioOk, prio = pcall(function() return tostring((L :: any).PrioritizeLightingQuality) end)
add(("LIGHTING style=%s prioritizeQuality=%s clock=%.1f brightness=%.2f exposure=%.2f ambient=%s outdoorAmbient=%s envDiffuse=%.2f envSpecular=%.2f"):format(
	styleOk and style or "n/a", prioOk and prio or "n/a", L.ClockTime, L.Brightness, L.ExposureCompensation,
	tostring(L.Ambient), tostring(L.OutdoorAmbient), L.EnvironmentDiffuseScale, L.EnvironmentSpecularScale))
local fx = {}
for _, c in L:GetChildren() do table.insert(fx, c.ClassName) end
add("LIGHTING children=" .. (#fx > 0 and table.concat(fx, ",") or "NONE"))
local atmos = L:FindFirstChildOfClass("Atmosphere")
if atmos then add(("ATMOSPHERE density=%.2f offset=%.2f haze=%.2f glare=%.2f"):format(atmos.Density, atmos.Offset, atmos.Haze, atmos.Glare)) end
local lights, shadowLights = 0, 0
for _, o in ws:GetDescendants() do
	if o:IsA("PointLight") or o:IsA("SpotLight") or o:IsA("SurfaceLight") then
		lights += 1
		if (o :: Light).Shadows then shadowLights += 1 end
	end
end
add(("LIGHTS total=%d shadowCasting=%d"):format(lights, shadowLights))

-- AUDIO / VFX ---------------------------------------------------------------
local running = game:GetService("RunService"):IsRunning()
local isClient = game:GetService("RunService"):IsClient()
local sounds, loud, noAsset, notPlaying, loaded, playing = 0, 0, 0, 0, 0, 0
for _, o in game:GetDescendants() do
	if o:IsA("Sound") then
		sounds += 1
		if o.Volume > 0.7 then loud += 1 end
		if o.SoundId == "" then noAsset += 1 end
		if o.IsLoaded then loaded += 1 end
        if o.Playing then playing += 1 end
        -- Templates/inactive zones and Edit values are inventory, never audibility proof.
        if o.Looped and not o.Playing then notPlaying += 1 end
	end
end
add(("AUDIO sounds=%d volumeAbove0.7=%d emptySoundId=%d loopedStoppedObserved=%d groups=%d"):format(sounds, loud, noAsset, notPlaying,
	count(game:GetService("SoundService"), function(i) return i:IsA("SoundGroup") end)))
add(("AUDIO running=%s client=%s loadedObserved=%d playingObserved=%d audible=NOT_TESTED templatesAndInactiveZonesMayBeStopped=true"):format(tostring(running), tostring(isClient), loaded, playing))
local emitters, rate, beamsBad, emptyTextures = 0, 0, 0, 0
for _, o in ws:GetDescendants() do
	if o:IsA("ParticleEmitter") then emitters += 1; rate += o.Rate; if o.Texture == "" then emptyTextures += 1 end
	elseif o:IsA("Beam") and (o.Attachment0 == nil or o.Attachment1 == nil) then beamsBad += 1 end
end
add(("VFX emitters=%d configuredRate=%.0f beamsMissingAttachment=%d emptyTextures=%d renderedQuality=NOT_TESTED"):format(emitters, rate, beamsBad, emptyTextures))

-- ENEMIES / NARRATIVE / UI --------------------------------------------------
local CS = game:GetService("CollectionService")
add(("TAGS Enemy=%d Interactable=%d Key=%d Door=%d NarrativeTrigger=%d"):format(#CS:GetTagged("Enemy"),
	#CS:GetTagged("Interactable"), #CS:GetTagged("Key"), #CS:GetTagged("Door"), #CS:GetTagged("NarrativeTrigger")))
for _, m in game:GetService("ServerStorage"):GetChildren() do
	if m:IsA("Model") and m:FindFirstChildOfClass("Humanoid") then
		local anchored = count(m, function(i) return i:IsA("BasePart") and (i :: BasePart).Anchored end)
		add(("ENEMY %s primary=%s anchoredParts=%d"):format(m.Name, m.PrimaryPart and m.PrimaryPart.Name or "NIL", anchored))
	end
end
local guis = count(game:GetService("StarterGui"), function(i) return i:IsA("ScreenGui") end)
add(("UI screenGuis=%d corners=%d strokes=%d"):format(guis,
	count(game:GetService("StarterGui"), function(i) return i:IsA("UICorner") end),
	count(game:GetService("StarterGui"), function(i) return i:IsA("UIStroke") end)))

add("COST geometryMemory=UNKNOWN textureMemory=UNKNOWN frameTime=UNKNOWN terrainTraversal=NOT_TESTED")
add("INTERPRETATION all counts are inventory; quality is judged from captures, clips and behaviour against the art direction and architecture")
return table.concat(out, "\n")
