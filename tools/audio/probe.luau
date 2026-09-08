--!strict
-- probe.luau - measure Creator Store audio inside Studio, because Store audio never lands on disk.
--
-- WHAT IT IS FOR. tools/audio/gate.py measures files. A Store asset has no file: it streams inside
-- Roblox only. This snippet is its gate. It loads each asset into an AudioPlayer, plays it into a
-- muted fader so nothing is heard, and reads an AudioAnalyzer wired off the player: peak level, rms
-- level, how much of the asset is near silence, and the spectral balance. Those numbers catch the
-- defects that reach the player as unpleasant - an asset that never loads, a clipped or distorted
-- transfer, a file that is mostly silence, one sound sitting far above the rest of its set.
--
-- HOW TO RUN IT. Paste through execute_luau with the Edit-mode DataModel and the studio_id. Replace
-- the REQUEST table with the assets you are checking. It creates one folder under ServerStorage,
-- measures, destroys the folder, and returns a JSON string - keep the batch small, the MCP result
-- is capped. It writes nothing else and touches nothing that belongs to another lane.
--
-- STATUS: written against the Audio API reference (AudioPlayer.IsReady/TimeLength/Play, AudioAnalyzer
-- .PeakLevel/.RmsLevel/:GetSpectrum, Wire, AudioFader, AudioDeviceOutput) and NOT yet run against a
-- live Studio. First run: check that `ready` is true and that `peak` is not zero for a known-good
-- asset. All-zero readings mean the probe did not measure, not that the asset is silent - report it
-- as unmeasured and fall back to the source description plus the playtest.

local REQUEST = {
	-- replace with the shortlist you are checking
	{ name = "amb_forest_day", id = 9112781510 },
	{ name = "impact_metal", id = 9116653976 },
}

local SAMPLE_SECONDS = 8 -- per window; long assets are sampled at start, middle and end
local HttpService = game:GetService("HttpService")
local ServerStorage = game:GetService("ServerStorage")

local previous = ServerStorage:FindFirstChild("__audio_probe")
if previous then
	previous:Destroy() -- only ever the probe's own folder
end
local root = Instance.new("Folder")
root.Name = "__audio_probe"
root.Parent = ServerStorage

local function setAsset(player: AudioPlayer, id: number)
	local uri = "rbxassetid://" .. tostring(id)
	local ok = pcall(function()
		(player :: any).Asset = (Content :: any).fromUri(uri)
	end)
	if not ok then
		(player :: any).AssetId = uri
	end
end

local function measureWindow(player: AudioPlayer, analyzer: AudioAnalyzer, from: number, seconds: number)
	local peak, rmsSum, frames, quiet = 0, 0, 0, 0
	local lowSum, highSum, binSum = 0, 0, 0
	player.TimePosition = from
	player:Play()
	local t0 = os.clock()
	while os.clock() - t0 < seconds do
		task.wait()
		local p, r = analyzer.PeakLevel, analyzer.RmsLevel
		peak = math.max(peak, p)
		rmsSum += r
		frames += 1
		if r < 0.001 then
			quiet += 1
		end
		local spectrum = analyzer:GetSpectrum()
		local n = #spectrum
		if n > 0 then
			for i = 1, n do
				local energy = spectrum[i] * spectrum[i]
				binSum += energy
				if i <= math.floor(n * 0.02) then
					lowSum += energy
				elseif i >= math.floor(n * 0.28) then
					highSum += energy
				end
			end
		end
	end
	player:Stop()
	return {
		peak = peak,
		rms = frames > 0 and rmsSum / frames or 0,
		quiet_share = frames > 0 and quiet / frames or 1,
		low_share = binSum > 0 and lowSum / binSum or 0,
		high_share = binSum > 0 and highSum / binSum or 0,
		frames = frames,
	}
end

local results = {}
for _, item in ipairs(REQUEST) do
	local player = Instance.new("AudioPlayer")
	local analyzer = Instance.new("AudioAnalyzer")
	local fader = Instance.new("AudioFader")
	local output = Instance.new("AudioDeviceOutput")
	analyzer.SpectrumEnabled = true
	fader.Volume = 0 -- the probe is silent: nobody is listening anyway
	player.Parent, analyzer.Parent, fader.Parent, output.Parent = root, root, root, root

	local function wire(from: Instance, to: Instance)
		local w = Instance.new("Wire")
		w.SourceInstance = from
		w.TargetInstance = to
		w.Parent = root
	end
	wire(player, analyzer)
	wire(player, fader)
	wire(fader, output)

	setAsset(player, item.id)

	local ready, waited = false, 0
	while waited < 10 do
		if player.IsReady then
			ready = true
			break
		end
		waited += task.wait(0.1)
	end

	local entry: any = { name = item.name, id = item.id, ready = ready, length = player.TimeLength }
	if ready and player.TimeLength > 0 then
		local length = player.TimeLength
		local windows = { 0 }
		if length > SAMPLE_SECONDS * 3 then
			windows = { 0, length / 2, math.max(0, length - SAMPLE_SECONDS) }
		end
		local merged = { peak = 0, rms = 0, quiet_share = 0, low_share = 0, high_share = 0, frames = 0 }
		for _, from in ipairs(windows) do
			local w = measureWindow(player, analyzer, from, math.min(SAMPLE_SECONDS, length))
			merged.peak = math.max(merged.peak, w.peak)
			merged.rms += w.rms
			merged.quiet_share += w.quiet_share
			merged.low_share += w.low_share
			merged.high_share += w.high_share
			merged.frames += w.frames
		end
		local n = #windows
		entry.peak = merged.peak
		entry.rms = merged.rms / n
		entry.quiet_share = merged.quiet_share / n
		entry.low_share = merged.low_share / n
		entry.high_share = merged.high_share / n
		entry.frames = merged.frames
		entry.measured = merged.frames > 0 and merged.peak > 0
		entry.peak_dbfs = entry.peak > 0 and 20 * math.log10(entry.peak) or -120
		entry.rms_dbfs = entry.rms > 0 and 20 * math.log10(entry.rms) or -120
	else
		entry.measured = false
		entry.reason = ready and "TimeLength is zero" or "asset never became ready: wrong id, no permission, or it failed to load"
	end
	results[#results + 1] = entry
	for _, child in ipairs(root:GetChildren()) do
		child:Destroy()
	end
end

root:Destroy()
return HttpService:JSONEncode(results)
