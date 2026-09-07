---
name: roblox-luau
description: Reference for writing or reviewing Roblox Luau in 2026 - modern task API, strict typing under the New Type Solver, server authority and remote validation, connection and task cleanup, streaming-safe code, the Character Controller library, Animation Graph playback with SetParameter, the Audio API instances, collision groups on WorldRoot, plus a map of deprecated APIs to their replacements and the traps of editing scripts inside a live Studio session. Use when writing, changing or reviewing game code, or when an engine API name is about to enter code or a review finding. Not for art, lighting, composition or Studio tool mechanics (see roblox-studio-mcp).
---

# Roblox Luau, 2026

Read the section you need; the file is a reference, not a procedure. Two rules govern everything below.

**Check the API before you write it.** Model memory of Roblox APIs is a year or two stale and the engine changed a lot in 2026. If a class, method or property is going into code or into a review finding and you are not certain it exists with that exact name today, look it up in the engine reference or inspect the live class through the Studio tools first. A misremembered API costs a whole fix round.

**Every fact here is from documentation and release notes, not from a run in this project.** Lines marked `VERIFY ON FIRST RUN` were not confirmed against a live Studio in this harness; confirm them the first time they matter and record the result.

## Non-negotiables

- `--!strict` at the top of every new script and module.
- `task.spawn` / `task.defer` / `task.delay` / `task.wait`; never the legacy globals.
- The server decides outcomes; the client sends intent. Validate every remote payload before touching it.
- Every connection and task has a place that ends it, and that place runs on player leave, character removal and instance destruction.
- Set properties first, parent last.
- Read back what you wrote from the place; a tool's success message is not the object.

## Modern task API

```lua
task.spawn(fn, ...)      -- run now, on a new thread
task.defer(fn, ...)      -- run at the end of the current resumption cycle
task.delay(seconds, fn)  -- run later; returns the thread
task.wait(seconds?)      -- yield; returns elapsed time
task.cancel(thread)      -- stop a thread you started
task.synchronize() / task.desynchronize()  -- parallel Luau only
```

Keep the thread handle for anything that can outlive its owner, and cancel it in cleanup. `task.delay` fired on a character that dies before it resolves is a classic source of damage after death.

`Debris:AddItem(instance, seconds)` is still fine for throwaway instances. For anything that owns state, destroy it from the cleanup that owns it.

## Strict typing and the New Type Solver

The New Type Solver is generally available (Nov 2025). It infers far more than the old one, so `--!strict` is cheap and catches the errors this codebase actually makes: a nil instance used as a value, a wrong payload field, a function called with the wrong shape.

```lua
--!strict
export type AbilityState = {
    cooldownEndsAt: number,
    charges: number,
}

local function findHumanoid(model: Instance): Humanoid?
    return model:FindFirstChildOfClass("Humanoid")
end

local humanoid = findHumanoid(character)
if not humanoid then return end   -- narrowing, not a cast
```

Prefer narrowing (`if not x then return end`) to casts. `::` casts silence the checker and hide the bug it found. Type remote payloads as `unknown` at the boundary and check them into a real type; a typed function signature is not validation, because the client can send anything.

There is no offline analyzer available through the Studio MCP tools, so strict-mode problems surface as Studio script analysis warnings and as runtime errors in the console. `VERIFY ON FIRST RUN` whether the Studio script analysis list is reachable through any available tool; if it is not, a clean Play console is the strongest signal available.

## Server authority and the validation ladder

The client sends what it wants to do. The server decides what happened, from state the server holds.

```lua
--!strict
local Players = game:GetService("Players")
local remote: RemoteEvent = ...

local COOLDOWN = 1.2
local lastUse: { [Player]: number } = {}

remote.OnServerEvent:Connect(function(player: Player, rawTargetId: unknown)
    -- 1. shape and type
    if typeof(rawTargetId) ~= "number" then return end
    local targetId = rawTargetId :: number
    -- 2. finite and in range
    if targetId ~= targetId or targetId == math.huge or targetId < 1 then return end
    -- 3. sender state
    local character = player.Character
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not humanoid or humanoid.Health <= 0 then return end
    -- 4. rate
    local now = os.clock()
    if now - (lastUse[player] or 0) < COOLDOWN then return end
    -- 5. world facts: target exists, is alive, is reachable
    local target = resolveTarget(targetId)
    if not target or not isAlive(target) then return end
    if (target:GetPivot().Position - character:GetPivot().Position).Magnitude > MAX_RANGE then return end
    -- 6. only now, act
    lastUse[player] = now
    applyEffect(player, target)
end)
```

The order matters: cheap checks first, world queries last, state change only at the end. Anything that indexes the payload before checking it is the defect.

Checks that belong on the ladder, in this order: shape and types; numbers finite and inside a plausible range (`x ~= x` catches NaN, and `math.huge` is a valid number that breaks everything downstream); the sender's identity and permission; the game state that makes the action legal; the world facts the action depends on (target alive, distance, line of sight via `workspace:Raycast` with a `RaycastParams` filter); how often this sender is asking.

Refuse by returning. Do not `error()` in a remote handler over untrusted input, and do not send a client an error it can spam.

**Rate limiting** that survives bursts is a token bucket per player, refilled by elapsed time, cleared in the player's cleanup. A `debounce` boolean shared across players is a bug in a multiplayer game.

**Idempotency**: an action that can be requested twice in the same frame must produce the same state as one request. Key it on the state that changes, not on a flag near the handler: check that the door is closed before opening it, that the item is not already granted, that the phase has not already advanced.

**RemoteFunction** from client to server blocks the server thread on a client that may never answer; prefer RemoteEvent in both directions for gameplay. `RemoteEvent:FireClient` for one player, `FireAllClients` for a shared world event; a shared event carries the same CFrames to everyone so the presentation lands in the same place on every client.

`Player:GetAttribute` / `Instance:SetAttribute` replicate server-to-client automatically and are the cheapest way to publish read-only state (health, phase, count) that a HUD or an effect reads. Attributes set by the client do not replicate to the server, which is exactly why they are safe as a one-way channel.

## Lifecycle and cleanup

Every connection, task, instance and table entry belongs to a scope that ends. The pattern that scales is one cleanup object per scope (the community calls it a Janitor or a Trove; a table of functions is enough):

```lua
--!strict
type Cleanup = { add: (any) -> (), destroy: () -> () }

local function newCleanup(): Cleanup
    local items: { any } = {}
    local self = {}
    function self.add(item: any) table.insert(items, item) end
    function self.destroy()
        for i = #items, 1, -1 do
            local item = items[i]
            if typeof(item) == "RBXScriptConnection" then item:Disconnect()
            elseif typeof(item) == "thread" then task.cancel(item)
            elseif typeof(item) == "Instance" then item:Destroy()
            elseif typeof(item) == "function" then item() end
            items[i] = nil
        end
    end
    return self
end
```

The events that end scopes:

```lua
Players.PlayerAdded / Players.PlayerRemoving
Player.CharacterAdded / Player.CharacterRemoving
Humanoid.Died
Instance.Destroying
```

`Instance:Destroy()` disconnects connections to that instance's own events, so a connection to a part you destroy is fine. A connection to `Players.PlayerRemoving`, `RunService.Heartbeat` or another long-lived object is not: it lives until you disconnect it, and it holds a reference to everything its closure captures.

Per-player and per-character tables are cleared in `PlayerRemoving` and `CharacterRemoving`, not on the next join. A table keyed by `Player` that is never cleared is a memory leak and a source of state from a previous life.

Tagged instances, connected once, including the ones that arrive later:

```lua
local CollectionService = game:GetService("CollectionService")
local function bind(instance: Instance) ... end
for _, instance in CollectionService:GetTagged("Interactable") do bind(instance) end
CollectionService:GetInstanceAddedSignal("Interactable"):Connect(bind)
CollectionService:GetInstanceRemovedSignal("Interactable"):Connect(unbind)
```

With streaming on, a tagged instance can be added and removed repeatedly on a client as the player moves; the removed signal must undo exactly what the added signal did.

Per-frame work: one `RunService.Heartbeat` (server or shared) or `RunService.PreRender`/`PreSimulation` connection that iterates a list, not one connection per object. `RunService.RenderStepped` exists on the client only.

## Streaming-safe code

With `Workspace.StreamingEnabled` the client receives parts of the world as the player moves. The server always has the whole DataModel; the client does not.

- Client code waits with a timeout and handles failure: `local part = folder:WaitForChild("Door", 10)` returns `nil` after the timeout instead of yielding forever. An unbounded `WaitForChild` on a streamed instance is a client that hangs with no error.
- Client code never assumes an instance still exists between frames; re-find it or hold a reference plus a `Destroying`/removed check.
- `Model.ModelStreamingMode` controls whether a model streams as a unit (`Atomic`), is always present (`Persistent`), or per player (`PersistentPerPlayer`). Anything the client must be able to see or reference at all times — spawn structures, controllers, references the HUD binds to — is persistent by design, not by luck.
- `Player:RequestStreamAroundAsync(position)` before a teleport gives the client a chance to have the destination loaded.
- Server-side gameplay decisions never depend on what a client has streamed in.

## Character Controller library

Full release, April 2026. `ControllerManager` with `GroundController`, `AirController`, `SwimController`, `ClimbController`, plus sensors (`ControllerPartSensor`, `BufferSensor`) replaces Humanoid-property hacks when movement is a real verb in the game: momentum, friction, wall interaction, custom air control. It is enabled per place through the Avatar Settings movement option; `VERIFY ON FIRST RUN` the exact place setting and its property name.

`Humanoid:MoveTo` is not supported under the Character Controller. NPC navigation that relies on `Humanoid:MoveTo` and `PathfindingService` keeps its Humanoid; that is the enemy owner's code, and mixing the two on one rig is a defect worth a finding.

Choose deliberately: a game whose central feeling is movement and whose movement is `WalkSpeed = 24` has left its main verb unimplemented. A game where movement is transport does not need the controller.

## Animation

Load through the Humanoid's `Animator` (`animator:LoadAnimation(animation)`); `Humanoid:LoadAnimation` is the deprecated path to the same object.

**Animation Graphs** (full release, July 2026) are state machines with blending, layering and masks, authored only in the Studio Avatar tab. Code cannot create or edit a graph. Code can play one: point an `Animation` at the graph asset, load it like any animation, and drive it with parameters.

```lua
local track = animator:LoadAnimation(graphAnimation)
track:Play()
track:SetParameter("MoveSpeed", speed)
track:SetParameter("Grounded", isGrounded)
```

Parameter names come from the graph the animator built; ask for them, do not guess. Negative `Speed` and negative `Weight` are not allowed. `VERIFY ON FIRST RUN` the exact `SetParameter` signature against the live class.

For plain clips, `AnimationTrack` gives `Play(fadeTime)`, `Stop(fadeTime)`, `AdjustSpeed`, `AdjustWeight`, `Priority`, and `GetMarkerReachedSignal(name)`. Animation markers are the right way to line up a gameplay moment with a pose — a hit landing on the frame the weapon connects — instead of a `task.wait` guessed from the clip length.

Freeze-frame effects done with `AdjustSpeed(0)` are unreliable when driven from the server; the track has to be adjusted on the client that plays it. Timing that gameplay depends on stays on the server.

## Audio API

The modern stack is instances wired together: `AudioPlayer` (the source) to effects (`AudioFader`, `AudioEqualizer`, `AudioReverb`, `AudioCompressor`, `AudioLimiter`, `AudioAnalyzer`) to an `AudioEmitter` in the world, heard by an `AudioListener` on the camera, connected by `Wire` instances (`SourceInstance` / `TargetInstance`). Reverb zones are chains placed before the emitter. Acoustic simulation (`SoundService.AcousticSimulationEnabled`, `BasePart.AudioCanCollide`, `PhysicalProperties.AcousticAbsorption`) gives occlusion and diffraction and is in client beta; do not build gameplay on it.

Legacy `Sound` inside a part still works and still replicates. In this studio the audio instances and the mix belong to the sound designer; gameplay code fires the named event that the audio responds to and does not create `Sound` objects of its own.

## Collision groups

Collision groups live on `WorldRoot` as of September 2026; the `PhysicsService` methods are deprecated. Register the group, set which groups collide, then set `BasePart.CollisionGroup`. `VERIFY ON FIRST RUN` the exact method names on `WorldRoot` against the live class reference before writing them into code.

Uses that matter here: decoration that must not block the player, invisible colliders that shape movement, projectiles that ignore their owner. Setting `CanCollide = false` on everything decorative and giving the player a clean collision surface is a movement-feel decision, not a cleanup task.

## Working inside a live Studio session

These are the traps that produce false diagnoses in this harness. They come from teams running exactly this setup.

- **Parent last.** Create the instance, set every property, then set `Parent`. Parenting first makes the engine replicate and render each subsequent property change.
- **A running game caches modules.** Once the game has started, the first `require` of a module is cached for that session. After editing a module, stop and start Play again before testing; testing without a restart shows the old code and produces an hour of debugging a fix that already worked.
- **`Model:PivotTo()` moves the pivot, not the visual centre.** A model whose pivot sits at the origin of its source file lands nowhere near where the coordinates suggest. Check `GetPivot()` and `GetBoundingBox()`, or set `PrimaryPart`, before moving anything imported. `SetPrimaryPartCFrame` is the deprecated form of the same operation.
- **The MCP `execute_luau` sandbox is not the game.** It runs with its own identity and its own module cache, so code that works there can behave differently inside a running game, and state it creates is not the state the server sees. Use it to inspect and to build, and use a real Play session to test behaviour.
- **Read back from the place.** After a script edit, read the source out of the place again; after creating instances, inspect them. Report success only for what you observed.
- **`loadstring` is disabled** unless `ServerScriptService.LoadStringEnabled` is on, and it stays off.
- **Scripts inside inserted Creator Store models are not trusted.** Do not enable them before they have been read.

## Performance shape

Event-driven beats polling. One frame connection beats many. Reuse a mesh id instead of unique meshes for repeated props (one load, instanced draw). Keep `Transparency` at 0 or 1 where possible; partial transparency multiplies overdraw. `RenderFidelity = Performance` for everything but landmarks, `CollisionFidelity = Box` for anything the player just walks past, `CastShadow = false` on small clutter. Order-of-magnitude targets for a base device are around a thousand draw calls and a million triangles in view; treat them as direction, not as a quota.

## Deprecated to current

| Do not use | Use |
|---|---|
| `wait()`, `spawn()`, `delay()` | `task.wait`, `task.spawn`, `task.delay` |
| `Instance.new("Part", parent)` | create, set properties, then set `Parent` |
| `:remove()` | `:Destroy()` |
| `Humanoid:LoadAnimation` | `Animator:LoadAnimation` |
| `Model:SetPrimaryPartCFrame` | `Model:PivotTo` (and check the pivot) |
| `PhysicsService` collision-group methods | the `WorldRoot` equivalents |
| `Ray.new` + `workspace:FindPartOnRay` | `workspace:Raycast` with `RaycastParams`; `Blockcast` / `Spherecast` / `Shapecast` |
| `BodyVelocity`, `BodyPosition`, `BodyGyro` | `LinearVelocity`, `AlignPosition`, `AlignOrientation` |
| `Lighting.Technology` | `Lighting.LightingStyle` plus `PrioritizeLightingQuality` |
| `InsertService:LoadAsset` for third-party models | `AssetService:LoadAssetAsync` with third-party assets allowed in place security |
| `game.Workspace`, `game.Players` | `workspace`, `game:GetService("Players")` |

## What this skill does not cover

Lighting, atmosphere, materials, composition and effect authoring have their own skills and their own owners. Studio tool mechanics, limits and traps are in `roblox-studio-mcp`.

## Sources

Luau New Type Solver general release: https://devforum.roblox.com/t/general-release-luau%E2%80%99s-new-type-solver/4084991 · Luau runtime recap 2025: https://luau.org/news/2025-12-19-luau-recap-runtime-2025/ · Character Controller full release: https://devforum.roblox.com/t/full-release-the-future-of-character-movement-character-controller-library/4565267 · Animation Graphs full release: https://devforum.roblox.com/t/full-release-animation-graphs-create-complex-character-motion-visually/4739840 · Audio API deep dive: https://devforum.roblox.com/t/robloxs-new-audio-api-a-somewhat-deep-dive/3156011 · Acoustic Simulation client beta: https://devforum.roblox.com/t/client-beta-acoustic-simulation-emit-audio-with-presence/4307121 · Design for performance: https://create.roblox.com/docs/performance-optimization/design · MeshPart performance: https://devforum.roblox.com/t/meshpart-usage-performance-optimizations/1319217 · Live-Studio working rules from teams running Rojo plus MCP: https://github.com/dnouri/roblox-pi-template/blob/main/AGENTS.md, https://github.com/Chrrxs/roblox-mcp-primitives, https://roxlit.dev/blog/how-to-use-claude-code-with-roblox · Third-party asset loading: https://devforum.roblox.com/t/loading-third-party-model-assets-in-experience/3939065
