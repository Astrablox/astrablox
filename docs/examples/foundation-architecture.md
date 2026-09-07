# The Key Remembers — Architecture

DOCUMENT TYPE: A — tiny new-game smoke test.

Implementation addendum (2026-09-06): `foundation-art-contract.md` controls the authorized post-playable environment polish, replacing the smoke-only primitive/hero restrictions below. The current bounded AGENTS.md controls scheduling and review order. Geometry, interaction identifiers, server authority and the two-room scope below remain binding.

## Concept and Experience
Dark-fantasy escape dungeon: take an iron key, unlock an iron door, enter the glowing shrine portal. Exactly two rooms, no enemies, no extra puzzles, no saves. Visual hook: the portal frame repeats the key's keyhole silhouette, turning the small object into a large visual payoff. Expected first completion 20–60 seconds; run a separate five-minute runtime soak, never artificially delay progression.

Emotional/spatial arc: Cell is intimate amber confinement, doorway is anticipation, Shrine is spacious cyan release despite identical dimensions. The key and locked door are visible immediately. Loop: spawn → E/tap key → E/tap door → walk through → touch portal → win UI.

## World Layout
Coordinates in studs. +Z leads from Cell to Shrine; both floors have top Y=0. Wall coordinates denote center planes, thickness 1. Ceilings top Y=15, bottom Y=14. Existing audit: 3 BaseParts, one default spawn, no scripts or Map. Remove blank Baseplate, reuse/reparent default spawn, retain Terrain. Conservatively reserve three existing counted parts even after cleanup.

All physical content is under Workspace.Map.Cell or Workspace.Map.Shrine. Each contains Shell, Gameplay, ArchDetail, Props, Lighting, VFX folders and one invisible CameraPoint. No content outside these except retained Terrain. Anchored=true throughout. Structural collision uses primitives.

### Cell
- Center Position (0,7,0), dimensions 24×14×24.
- Floor: Slate #302F38, Size (24,1,27), center (0,-0.5,0). Walls: Cobblestone #302F38, planes X=±12, Z=-12 and shared Z=12. Ceiling Slate #302F38, Size (24,1,24), center (0,14.5,0).
- Accents: Metal #62646D door/key; amber #F2B96B torches; tiny cyan #77DDD9 key inset.
- Two wall-torch PointLights at (-10.9,8,-4), (10.9,8,4): #F2B96B, Range 18, Brightness 1.4, Shadows true.
- SpawnLocation in Gameplay: Size (6,1,6), center (0,-0.5,-7), Neutral=true, Duration=0, face toward (-6,3,-3). Character emerges around Y=3.
- Pedestal: primitive Size (4,3,4), center (-6,1.5,-3), Slate #302F38. IronKey pickup Part center (-6,3.5,-3), Size (1.6,0.6,0.6), with optional primitive key visual; reachable from floor, no jumping.
- IronDoor: Metal #62646D, Size (7.8,10,0.8), center (0,5,12). Door gap width 8, height 10; details must retain >=7.5 clear width.
- CameraPoint at (0,5,-9), looks toward (0,5,10).
- CHARACTER: abandoned cell with a deliberately prepared pedestal; medium edge dressing, empty central walking lane, key is the only small bright focal object.
- LIFE: torch brightness smoothly breathes at 11-second intervals; continuous quiet crackle. Key acquisition produces immediate status feedback; door action raises the bars over 0.6 seconds and reveals cyan light.
- Budget including reserve: 140 BaseParts.

### Shrine
- Center Position (0,7,24), dimensions 24×14×24.
- Floor: Slate #302F38, Size (24,1,27), center (0,-0.5,24). Walls: Cobblestone #302F38 at X=±12, far Z=36. South wall is Cell's shared wall at Z=12: do not duplicate. Ceiling Size (24,1,24), center (0,14.5,24), Slate #302F38.
- Accents: Metal #62646D portal frame; Neon #77DDD9 membrane; sparse amber #F2B96B offering bowls and muted wine #8F4859 old seals.
- Portal PointLight at (0,6,31): #77DDD9, Range 20, Brightness 1.8, Shadows false. Fill PointLight at (0,10,21): same color, Range 18, Brightness 0.45, Shadows false.
- Portal frame overall Size (10,11,2), center (0,5.5,32), open inner passage >=7×9. Keyhole silhouette; primitive fallback <=12 pieces.
- PortalMembrane Size (7,9,0.3), center (0,4.5,32), Neon #77DDD9, Transparency 0.35, CanCollide/CanTouch/CanQuery=false.
- PortalTrigger Size (7,9,3), center (0,4.5,31.5), Transparency=1, CanCollide=false, CanTouch=true, CanQuery=false. No solid geometry inside its walk-in volume.
- CameraPoint at (0,5,15), looks toward (0,5,32).
- CHARACTER: sparse reverent chamber; portal is the sole hero. Maintain empty 10-stud-wide central lane and flank the frame with small offerings only.
- LIFE: portal light smoothly breathes every 8 seconds, quiet spatial hum; valid touch immediately shows win UI. Portal stays active for subsequent players.
- Budget including reserve: 146 BaseParts.

## Door Connection and Geometry
Cell ↔ Shrine doorway center (0,5,12), width 8, height 10. Cell owns shared wall: left/right piers Size (8,14,1), centers (-8,7,12)/(8,7,12); lintel Size (8,4,1), center (0,12,12). Gap X=-4..4, Y=0..10. Floors overlap Z=10.5..13.5, exactly 3 studs, with equal top Y=0. No threshold lip, corridor, stairs, second door, or corner pocket. Raised door ends centered (0,17,12); conceal its upper region behind the lintel. No mesh collision on the path.

## Services and Scripts
```text
ReplicatedStorage/Modules/Config (ModuleScript)
ServerScriptService/DungeonMain (Script)
StarterPlayer/StarterPlayerScripts/DungeonClient (LocalScript)
StarterGui/EscapeGui (ScreenGui)
  Status (TextLabel)
  WinPanel (Frame)
    Title (TextLabel)
    Subtitle (TextLabel)
    ContinueButton (TextButton)
SoundService/DungeonAmbience (SoundGroup)
```
Services: Players, CollectionService, ReplicatedStorage, TweenService, Workspace, Lighting, SoundService. No RemoteEvents/RemoteFunctions, DataStores, leaderstats, enemies or narrative scripts. All new scripts `--!strict`, `task.*` scheduling only. Track/disconnect connections and cancel tweens on teardown; remove per-player listeners/state on leaving and replace character listeners on respawn.

**Config:** immutable ModuleScript returning the exact following fields. Both scripts read constants; no runtime writes.
```lua
return table.freeze({
    InteractionDistance = 10, -- number; Main prompts/validation, studs
    PromptHoldDuration = 0.2, -- number; Main, seconds
    PromptCooldown = 0.35, -- number; Main per-player rate limit, seconds
    DoorOpenSeconds = 0.6, -- number; Main tween duration
    DoorRiseStuds = 12, -- number; Main tween delta from original CFrame
    PortalPadding = 4, -- number; Main root-in-oriented-box expansion, studs
    FeedbackSeconds = 2, -- number; Client temporary status
    TorchCycleSeconds = 11, -- number; Client cosmetic pulse
    PortalCycleSeconds = 8, -- number; Client cosmetic pulse
    WalkSpeed = 16, -- number; Main character setup
})
```

**DungeonMain:** sole gameplay authority. Functions `initializeMap`, `bindPlayer`, `bindCharacter`, `validatePrompt`, `onKeyTriggered`, `onDoorTriggered`, `onPortalTouched`, `setFeedback`, `cleanupPlayer`. Depends on Config and exact tagged Parts below. Await named objects at boot; assert exactly one per gameplay tag with actionable error. Creates/reuses named KeyPrompt under IronKey and DoorPrompt under IronDoor; never duplicates physical objects. Prompts: E, HoldDuration 0.2, MaxActivationDistance 10, RequiresLineOfSight=true; text Take/Iron Key and Unlock/Iron Door respectively.

Runtime source of truth: server-local `doorState: "Locked"|"Opening"|"Unlocked"` starts Locked; server-local player table `{hasKey:boolean=false, won:boolean=false, lastPromptAt:number=-math.huge}`. Replicated display mirrors on Player: HasIronKey:boolean=false, Escaped:boolean=false, DungeonFeedback:string="", FeedbackSerial:number=0. Map attribute DoorState:string="Locked". Main alone writes mirrors; never derive authority from client-visible attributes.

Validation for each Triggered callback: registered player, current Character in Workspace, living Humanoid, root/head present, configured tagged target, allowed phase, root-to-target distance <=10, server raycast from Head to target unobstructed by structure, per-player cooldown >=0.35 seconds. Raycast ignores current character and target's own model. Props nonqueryable; walls/closed door queryable. Do not rely solely on engine prompt distance. No client item IDs, damage claims, or progress payloads.

Key while Locked sets that player's hasKey=true and feedback "Iron key taken"; repeated pickup is idempotent. Key stays visible for other players. Door while Locked without key gives "Find the iron key". Valid keyed unlock synchronously sets Opening before yielding, consumes initiator's key, disables both prompts globally, sets door CanCollide=false, then tweens original CFrame upward 12 studs over 0.6 seconds. Completion sets Unlocked; unexpected tween interruption snaps to final position and finishes Unlocked. No relock or second tween.

Portal Touched resolves Player from an ancestor Character, rejects unrelated parts/NPCs/dead characters, requires Unlocked and won=false, then validates character root inside PortalTrigger's oriented box expanded by PortalPadding on each half-extent. Set won=true before effects and mirror Escaped=true. Repeated limb contacts are ignored. Never freeze, kill, kick or teleport on win.

Multiplayer: shared door, per-player keys/wins, recommended max four. Reset/death retains personal hasKey/won and respawns in Cell; door remains at its shared state. Leaving deletes personal state but never resets door. Visible key prevents softlock if its holder leaves. Late joins may use the open door. Fresh server/play session resets all. No persistence or automatic replay round.

**DungeonClient:** display and cosmetic effects only. Functions `renderStatus`, `renderWin`, `showFeedback`, `startAmbientPulses`, `cleanup`. Connect attribute signals before initial render. Status priority: temporary feedback → Escaped "Escaped" → door not Locked "Enter the portal" → HasIronKey "Unlock the iron door" → "Find the iron key". FeedbackSerial permits repeating identical text; use a generation token to prevent older expiry clearing newer feedback. Win panel appears when Escaped becomes true. ContinueButton.Activated dismisses locally without changing gameplay; preserve dismissal across respawn. Torch pulses 85–100%, portal 90–100% of final lighting values captured on client start; smooth TweenService cycles, no frame loop and no hue changes. Cancel on teardown.

## Remotes and Tags
**Zero custom client→server remotes and zero custom server→client remotes.** Engine ProximityPrompt.Triggered supplies Player; Touched supplies hit Part; validation is explicitly above. Server-owned attributes replicate display state. Remote security still applies to prompt callbacks independently of built-in UI.

| Tag | Count | Exact target | Attributes |
|---|---:|---|---|
| DungeonKey | 1 | Map.Cell.Gameplay.IronKey | ItemId:string="IronKey" |
| DungeonDoor | 1 | Map.Cell.Gameplay.IronDoor | DoorId:string="CellDoor" |
| DungeonExit | 1 | Map.Shrine.Gameplay.PortalTrigger | ExitId:string="ShrineExit" |
| DungeonTorch | 2 | Cell.Lighting light-bearing torch Parts | none; PointLight child |
| DungeonPortalLight | 1 | Shrine.Lighting portal light-bearing Part | none; PointLight child; excludes fill |

World-builder owns all named physical objects, spawn, tags, shell, camera points and baseline lights. Scripter owns prompts, runtime attributes, code, functional UI, gameplay-triggered sounds/tweens; adds zero BaseParts. Detail-architect only ArchDetail; set-dresser only Props, except world-builder may use Shrine's reserved 12-piece fallback frame allotment and report it. Fixtures/props/camera points/VFX are anchored, noncolliding, nontouching, nonqueryable; camera/VFX anchors invisible. Pedestal collides. Key is noncolliding/nontouching/nonqueryable. Structure and closed door collide/query. Portal exceptions defined above. No collision groups needed.

## UI and Controls
EscapeGui ResetOnSpawn=false, IgnoreGuiInset=false, DisplayOrder=10. Status AnchorPoint(.5,0), Position Scale(.5,.03), Size Scale(.70,.10), text>=16. WinPanel initially hidden, AnchorPoint(.5,.5), Position Scale(.5,.45), Size Scale(.76,.48); UISizeConstraint min(250,220), max(600,340). Children relative Scale positions/sizes: Title (.06,.10)/(.88,.22), text "Escaped", >=24; Subtitle (.06,.35)/(.88,.20), "The shrine is open.", >=16; ContinueButton (.18,.66)/(.64,.25), "Continue exploring", >=16, minimum 44×44 pixels. Dark translucent backing, cyan border, amber status accent, Gotham-family supported font. Validate at 360×640 and 640×360; persistent HUD avoids default joystick/jump controls.

Scripter creates hierarchy/text/visibility/behavior. UI-designer polishes colors, fonts, corners, strokes, sizing constraints and optional single UIAnimations script only. Continue hides panel locally. Default third-person camera; WASD/default mobile stick, mouse/touch drag camera, Space/default touch jump, E/built-in tap prompt for both interactions, click/tap Continue. No custom sprint, flashlight, precision jumps, or camera controller.

## Asset Plan
Primitives for all structure, walkable surfaces, door, key, trigger and membrane. Maximum two optional generated hero meshes; create fallbacks immediately, generation must not block smoke-test delivery. Generated visual replaces its fallback; retain primitive collider where necessary.

| Piece | Room / builder | Method and prompt | Size / Position | Collision/fallback |
|---|---|---|---|---|
| Worn key pedestal | Cell / set-dresser | Optional generate_mesh: "Low-poly worn dark-fantasy stone pedestal, shallow key recess, charcoal slate, amber worn edges, no text" | 4×3×4 / (-6,1.5,-3) | Decorative mesh; invisible primitive collider; block/cap fallback |
| Keyhole portal frame | Shrine / world-builder | Optional generate_mesh: "Low-poly ancient iron keyhole portal frame, open center, dull iron and charcoal stone, thin cyan runes, no text" | 10×11×2 / (0,5.5,32) | Noncolliding; retain >=7×9 visible opening; <=12 primitive segments fallback |

Generated mesh count 0–2 explicitly budgeted. No generated materials/store-model dependency. Reject a generated frame with a filled opening. Sound uses verified available Roblox-library asset IDs selected by responsible builder, never fabricated IDs.

## Lighting and Art Direction
Readable amber confinement → cyan release. ShadowMap Technology if available, otherwise lighting-director records supported current equivalent favoring mobile readability. ClockTime 0, Brightness 1, Ambient RGB(48,45,58), OutdoorAmbient RGB(35,38,48), ExposureCompensation 0. ColorCorrection Saturation=-0.15, Contrast=.10, TintColor RGB(235,231,242); Bloom Intensity=.20, Size=18, Threshold=1.2; Atmosphere Density=.12, Color RGB(163,175,194), Decay RGB(75,77,92), Offset=0, Haze=.5, Glare=0. No DepthOfField/SunRays. Four exact local lights given in room specifications; director may tune brightness/range while preserving roles. Client pulses captured final values.

Five-color palette: #302F38 dominant confinement stone; #62646D iron mechanism; #8F4859 tiny old seals (not danger); #F2B96B safe near interaction/torches; #77DDD9 supernatural exit/light atmosphere. Cobblestone means confinement, Slate worn traversal, Metal lock/release, Neon invitation. Human ~5 studs, pedestal 3, doorway 10, ceiling 14. Cell medium edge props, Shrine sparse; no bright competing decorations.

## Signature Moments and Environmental Events
1. Key: valid prompt sets personal key and immediate two-second text, optional short metal chime. Aftermath is persistent personal key until consumed. Scripter logic/audio/UI; builder key/pedestal.
2. Door: valid keyed prompt at t=0 enters Opening/disables collision/prompts; t=0..0.6 bars rise and optional scrape plays; t=.6 Unlocked. Permanent shared route and visible cyan shrine. Scripter choreography; builder gap/door and lighting.
3. Portal: valid touch immediately mirrors Escaped and displays panel, optional <=1.5-second chime. Portal remains usable; UI-designer polishes feedback.

Ambient: two quiet looping torch crackles in Cell, one looping hum in Shrine; <=6 total sounds including optional pickup/door/win cues, each volume<=.35. Ambient sources use DungeonAmbience group and existing parts/attachments. Sound-designer verifies actual IDs and playback; scripter owns gameplay cues. Unavailable optional cue never blocks interaction. Both rooms receive valid ambient sound where assets resolve.

VFX: up to three emitters (two tiny torch embers, portal motes), Rate<=6 each, combined<=18; <=4 invisible anchors. No full-room fog, beams or damaging flames. Ambient cycles 11/8 seconds as Config; these never change traversal or state. No story-teller or enemy-designer needed.

## Part Budget
User hard cap <=299 total Workspace BaseParts, counting Terrain if audit does. Plan <=289 including reserve; ten unallocated parts remain. Separately keep Map total descendants <=600, below studio's 5000-instance ceiling.

| Allocation | Cell | Shrine | Total |
|---|---:|---:|---:|
| World-builder shell/gameplay/spawn/camera | 30 | 30 | 60 |
| Detail-architect infrastructure | 22 | 22 | 44 |
| Props including primitive hero fallbacks | 28 | 28 | 56 |
| Light fixture geometry | 6 | 6 | 12 |
| VFX anchors | 2 | 2 | 4 |
| Optional generated meshes | 1 | 1 | 2 |
| Reserve, Game Master allocates before spending | 51 | 57 | 108 |
| Existing conservative allowance | — | — | 3 |
| Total | 140 | 146 | 289 |

Expected before reserve <=181 BaseParts. Scripter/audio add zero BaseParts. No enemy/narrative allowance. Budgets are ceilings, not density targets; count replaced fallbacks and fixtures accurately.

## Build Order
1. Scripter Config/Main/Client/UI in parallel with world-builder rooms/gameplay/tags/spawn/base lights. Validate shared contracts before runtime; missing objects may be awaited during build, but report boot errors clearly.
2. Audit shell, tags, scripts, floor overlap and clear doorway. Read Main interaction validation.
3. Parallel room blueprints within budgets → whole-map infrastructure → parallel room dressing. Account for world-builder's frame fallback within Shrine props.
4. Sound → VFX → lighting → art review/fixes; audit each layer. Skip enemies/narrative.
5. Luau-reviewer/fixes until PASS → UI polish → structural playtester/fixes until PASS.
6. Computer-player normal-input completion plus five-minute runtime soak/reset checks; monitor console and stop play afterward. Quality gate before publication.

## Walkthrough and Acceptance
1. Spawn around (0,3,-7). Approach key at (-6,3.5,-3); hold E .2 seconds or tap prompt. Confirm HasIronKey and status.
2. Approach (0,0,8), use IronDoor prompt at (0,5,12). Confirm Opening→Unlocked in .6 seconds, initiator's key consumed and door raised.
3. Walk X=0 through Z=12 into Shrine, then toward (0,0,30). Touch PortalTrigger centered (0,4.5,31.5). Confirm Escaped=true and win panel. Continue exploring dismisses it.
4. Verify door rejects without key; portal rejects while Locked; repeated triggers are idempotent; reset before unlock preserves key; reset after unlock preserves route; reset after win preserves dismissal; departed key holder cannot softlock others. Second player/late joiner can win through shared open door.
5. Five minutes of runtime total with normal movement/repeated attempts/resets, no console errors. Completion evidence must use real input, not teleporting or manually setting attributes.

## Risks and Mobile Checks
Key must sit above pedestal with unobstructed server raycast; decor nonqueryable. Unlock state changes before yield prevent competing tweens. Portal trigger is nontangible but touch-enabled, with server root-box validation. Reserve spending requires explicit producer allocation. Verify >=44×44 controls, >=14 text (specified >=16), default touch prompt/movement/jump, no precision jumps, readable shadows on mobile, and <299 audited BaseParts after every layer.

DOCUMENT TYPE: A
PART BUDGET: 289 BaseParts including reserve / 299 user cap; <=600 Map descendants / 5000 studio ceiling.
ASSUMPTIONS: cooperative shared door with per-player keys/wins; no saved progression or replay round; optional heroes use immediate primitive fallbacks; default Baseplate is disposable and spawn reused from supplied empty-place audit; conservative Terrain allowance. No Studio modifications by architect.

ARCHITECTURE DESIGNED: The Key Remembers — exact two-room smoke-test contract.
READY FOR REVIEW
