---
name: roblox-vfx
description: Roblox VFX craft — particles, beams, trails, mesh VFX, flipbooks, spell and impact cues, camera shake, hitstop, impact frames, cue timing and client-side presentation code. Use when building or tuning an effect, a combat hit, a spell, a portal, a reveal, or environmental atmosphere emitters, and when judging why an effect looks cheap. Not for global Lighting, Atmosphere or post-processing setup (that is the lighting skill), not for sound mixing or SoundGroup routing (that is the sound skill).
---

# Roblox VFX craft

Reference for building effects that read as events, not as sparkle. Values here are starting
points to tune against what the camera actually shows, never targets to hit. Nothing in this file
is a quota: the number of layers, emitters and cues follows the moments the game has.

## 1. What makes an effect read

An effect is a small piece of staging. Three beats, in this order, always:

- **Anticipation** — something changes before the payoff: a gather, a charge glow, a wind-up,
  dust pulled inward, a light dimming. Anticipation is what makes the burst land; without it the
  burst reads as a pop.
- **Burst** — the peak. One frame carries the whole effect. If you cannot point at the strongest
  frame in a capture, the effect has no peak and will read as mush.
- **Dissipate** — the fall-off. Community rule of thumb: reduce intensity before the elements
  fully disappear, so nothing snaps out of existence. Smoke and embers outlive the flash.

Timing is the craft; the emitter properties only serve it. Slowing the anticipation usually reads
better than speeding up the burst (same finding as in animation: easing beats raw speed).

**Layers do different jobs.** A cue that is one emitter turned up reads cheap no matter how bright
it is. The jobs, chosen per cue (not a checklist to fill):

- shape / core — the thing itself (mesh, beam, or a large slow sprite) that gives the effect a
  silhouette;
- motion — directional streaks, trails, speedlines that show where energy goes;
- debris — sparks, embers, chunks, dust that give the world something to react with;
- light — a short-lived PointLight/SpotLight or an emissive surface pulse that puts the effect on
  the surrounding geometry, so it belongs to the scene rather than floating over it;
- camera — shake, and optionally a brief post-effect frame;
- sound — see §8; without it, a hit "works functionally but doesn't feel satisfying".

**Contrast decides visibility.** An effect is seen against the scene's value and hue, not in
isolation. A bright warm burst dies in a bright warm room. Check the effect against the background
it will actually have, from the camera the player will actually have.

**Scale communicates stakes.** A gate opening and a footstep cannot use the same size, speed and
count. If the same effect serves a small and a huge event, the huge event is undersold.

## 2. ParticleEmitter — the knobs that matter

Roblox particles are camera-facing (or oriented) textured quads spawned from an Attachment or a
part. What each knob actually buys:

- **Texture** — any 2D image: sparks, traces, smoke puffs, swirls, stars, soft round gradients.
  The single biggest quality lever. Inspect the sprite in place: hard rectangular edges, a visible
  alpha box, or the default sprite are what make an effect look like a tutorial. Prefer a texture
  whose alpha falls off at the edges.
- **Color / Size / Transparency as sequences** — these are curves (NumberSequence /
  ColorSequence), not single values. Flat values are the mark of an untuned emitter. Fire is
  usually authored hot-to-cool along the lifetime (white into orange into red, several keypoints
  so the ramp is smooth). Size almost always changes over life: grow fast, shrink slow, or the
  inverse for a suck-in. Transparency starts and ends at 1 unless you want a pop.
- **LightEmission** (0..1) — additive blending. High values make particles glow and stack; good
  for magic, sparks, fire cores. Additive over a bright background disappears, and stacked
  additive particles blow out to white.
- **LightInfluence** (0..1) — how much scene lighting darkens the particle. Smoke and dust want
  higher influence so they sit in the scene's light; energy wants 0.
- **Brightness** — multiplies emission; use with LightEmission for HDR-ish cores that bloom.
- **Orientation** — `FacingCamera` (default billboard), `FacingCameraWorldUp` (billboard that
  keeps world up; good for ground fog, columns of smoke), `VelocityParallel` (sprite aligned along
  motion; the way to get streaks/sparks), `VelocityPerpendicular` (rings, shockwave discs).
- **Squash** — stretches the sprite along its axis, positive or negative. With
  `VelocityParallel` this is how speed reads: fast particles stretch.
- **ZOffset** — pushes the particle toward or away from the camera in the emitter's sorting, which
  is how you layer effects deliberately: give fire a higher ZOffset than the smoke behind it so
  the fire stays in front.
- **SpreadAngle**, **Rotation** (-180..180), **RotSpeed** — break up uniformity. Identical rotation
  on every sprite is instantly readable as machine-made.
- **Lifetime as a range** (e.g. a min/max pair rather than one number) — variance is what keeps a
  burst from behaving like a single object. If particles vanish too early or hang around, lifetime
  is the first property to touch.
- **Drag / Acceleration / VelocityInheritance** — physical behaviour. Debris that falls and slows
  reads as matter; debris on a straight line reads as a screensaver.
- **Shape / ShapeStyle / ShapeInOut / ShapePartial / EmissionDirection** — emitter volume (box,
  sphere, cylinder, disc) and whether particles start inside, on the surface, or move inward.
  Sphere+inward is the standard "gather" for anticipation.
- **Flipbooks** — animated sprite sheets via `FlipbookLayout` (`Grid2x2`, `Grid4x4`, `Grid8x8`).
  A flipbook of real smoke or an explosion does in one emitter what twenty static sprites cannot.
  `FlipbookMode` (Loop / OneShot / PingPong) and `FlipbookFramerate` control playback. Frames must
  match the declared grid or the animation tears.
- **Enabled / Rate / `Emit(n)`** — see §3.

Spawn from an Attachment placed exactly where the effect is caused (a hand, a weapon tip, the
foot, the impact point, the vent), not from the model's center.

## 3. Rate versus Emit

- **Continuous effects** (torch fire, waterfall mist, dust shaft, portal churn) use `Rate` with
  `Enabled = true`. Simultaneous particle count is `Rate × Lifetime` — an emitter with a rate of
  100 and a lifetime of 5 keeps ~500 particles alive. Do that arithmetic before tuning brightness.
- **Event effects** (a hit, a cast, a shatter, a gate slam) use `Rate = 0`, `Enabled = false` at
  rest, and `ParticleEmitter:Emit(n)` at the moment. This is the standard Roblox pattern: an
  event burst driven by Rate is either always running or arrives late.
- A cue is usually several emitters emitting on different offsets: core at t0, debris a fraction
  later, dust last. Sequencing `Emit` calls costs nothing and is most of what makes a burst feel
  authored.
- Templates that sit disabled in Edit are correct, not broken. Verify them by triggering, not by
  looking at them at rest.

**Budget orientation (starting point, not a law):** there is no hard engine limit, but practical
headroom is roughly a few hundred simultaneous particles on desktop and noticeably fewer on
mobile; overdraw, not count, is what kills frame time — many large, semi-transparent, overlapping
sprites are far more expensive than many small ones. Avoid `Transparency` values strictly between
0 and 1 on large geometry for the same reason.

## 4. Beams and Trails

- **Beam** — a textured ribbon between two Attachments, with `CurveSize0/CurveSize1` for bezier
  bend, `Width0/Width1`, `TextureSpeed`, `TextureLength`, `TextureMode`, `LightEmission`,
  `FaceCamera`, and Color/Transparency sequences along its length. This is the tool for: lightning,
  laser, magic tether, portal edge, sword arc, waterfall sheet, tracer. Both attachments must be
  real, parented to real parts, and correctly oriented — a beam attached to a floating attachment
  with no world reason is the classic broken effect.
- **Trail** — a ribbon that follows two attachments through motion (`Lifetime`, `MinLength`,
  `WidthScale` curve, `FaceCamera`). This is how a swing, a projectile, a dash or a falling ember
  gets its motion streak. Trails read as speed; without them fast objects look teleporting.
- Both take the same texture discipline as particles: a good soft texture with a gradient along
  its length is the difference between "energy" and "a colored rectangle".

## 5. Mesh VFX

Roblox has no native mesh-VFX tool; the technique is meshes tweened/scaled/spun by code, and it is
what separates hobby effects from the ones people copy.

- The core patterns: a ring or cone mesh that scales outward and fades (shockwave), a mesh that
  scales in on itself then out (implosion), a spinning tube (tornado, energy column), a stack of
  meshes on different speeds and rotations for volume, a slash mesh that appears for a few frames.
- **Texture scrolling** gives flow: `Texture.OffsetStudsU/OffsetStudsV` animated per frame. It
  works only on a `MeshPart` with proper UVs — Roblox-generated UVs and `SpecialMesh` will not
  scroll. If the UVs are wrong, the scroll goes nowhere; that is a mesh problem, not a code bug.
  `EditableMesh` UV manipulation is the alternative when you must scroll on generated geometry.
- **Emissive masks** on `SurfaceAppearance`/`MaterialVariant` (`EmissiveMaskContent`,
  `EmissiveStrength`, `EmissiveTint`, live since Feb 2026) let a mesh glow selectively — runes,
  cracks, lava seams, charging weapons — and strength/tint are animatable from code. Emissive
  glows and blooms but casts no light on neighbours: pair it with a short-lived PointLight if the
  surroundings should react.
- **Mesh flipbooks** are not an engine feature: cycling `TextureID` (or `MeshId`) frame by frame is
  the whole technique; open-source mesh flipbook packs exist.
- Author mesh VFX geometry outside Studio when you can (subdivide a plane, Simple Deform 360° on
  Z for rings and vortices, export and import as MeshPart). Keep VFX meshes low-poly: they are seen
  for a fraction of a second, and the engine caps a MeshPart at 20k triangles on import.
- Hitbox and visual are separate objects. The visual mesh is non-colliding, massless, anchored or
  welded as suited; damage geometry is its own thing on the server.

## 6. Camera work: shake, impact frames, hitstop

All three are client-side. They are the difference between "an effect played" and "I felt that".

- **Camera shake** — the standard implementation is Sleitnick's `RbxCameraShaker` (a port of EZ
  Camera Shake), with presets: `Bump` (high-magnitude, short, smooth — melee hits), `Explosion`,
  `Earthquake`, `HandheldCamera` (idle sway), `Vibration`, plus `Shake` (one-shot decaying) and
  `ShakeSustain` (held until released). Scale magnitude by distance from the source, and give the
  shake a direction related to the hit — players notice when the camera moves the way the blow
  went. Shake must always decay to zero and must never fight player aim or survive death, respawn
  or menu.
- **Impact frames** (anime convention, and the single cheapest way to sell weight): at the moment
  of contact, hold a high-contrast frame for a beat — speedlines, a `ColorCorrection` pushed to
  near-black or blown white, a `Highlight` on the character, then a heavier particle burst as the
  frame releases. Because it is per-player, the presentation module creates and drives its own
  post-effect instance on the client and removes or disables it when the cue ends; never edit the
  lighting owner's global post-processing values.
- **Hitstop** — freeze or slow motion for a fraction of a beat on contact, then resume:
  `AnimationTrack:AdjustSpeed(0)` (and `AdjustWeight`) on the client where the track is playing.
  Called from the server or from the wrong client it is unreliable. Hitstop applies to the
  attacker's animation, the effect's own tweens, and optionally the victim's; it never touches
  server state, damage timing or input.
- Camera focus tricks used by combat games: follow the head instead of the torso
  (`bodyPartToFollow` in BaseCamera) and lerp `Humanoid.CameraOffset` toward a focus target, bound
  on `RenderStepped` at a high priority, with sin/cos shaping. This is a modification of the
  PlayerModule and belongs to whoever owns character control, not to a cue.

## 6b. Directed sequences (cutscenes) in Roblox

A directed sequence is a cue whose camera is also authored. The mechanics:

- Take the camera: `workspace.CurrentCamera.CameraType = Enum.CameraType.Scriptable`, then drive
  `CFrame` per shot, with `TweenService` for moves and hard cuts by setting `CFrame` directly.
  `FieldOfView` is a per-shot decision (long for compressing distance and making mass heavy, wide
  for speed and scale up close). Restore `CameraType` to `Custom` and the subject to the
  character when the sequence ends, and re-enable player controls you disabled.
- Hide the interface for the duration (`StarterGui:SetCoreGuiEnabled` and your own HUD) and add a
  letterbox or equivalent treatment so the player reads "this is directed"; remove it on return.
- Freeze what must not move: the server holds the player safe (no damage, no fall) for the length
  of the sequence and restores control after; that is the scripter's side of the interface.
- Run the creature's animations from the client for the sequence beats and play the cues on
  the same timeline; one presentation module owns the whole timeline so cuts, cues, shake and
  sound stay in sync.
- Scale on camera: a creature reads as huge when the frame contains something human-sized and
  when the camera looks up at it from player height; a wide shot of a large model in empty space
  reads as a small model close up. Low camera, near foreground element, creature filling and
  breaking the frame edge.
- Every cut lands on a frame that reads alone; the peak shot is the one that gets the impact
  frame, the strongest shake and the loudest layer.
- Skip and interrupt: the sequence must be cancellable (death, leave, a second trigger) and must
  leave camera, interface and control exactly as it found them.

## 7. Replication and where the code lives

- The server owns outcomes. It fires a **named event** (or sets an attribute) with the data the
  presentation needs — a world CFrame, a direction or surface normal, a strength class, the
  victim. It does not build effects.
- The client presentation module clones and plays the effect locally. Multiplayer pattern:
  `FireAllClients` with a shared CFrame so every client builds its own copy at the same world
  position; replicating hundreds of particle parts from the server instead is the usual cause of
  a "laggy spell".
- Presentation never gates progress. If the client controller errors or is deleted mid-cue, the
  door still opens, the damage still applied, the quest still advances.
- Everything a cue creates is cleaned up: emitters stopped, meshes destroyed or returned to a pool,
  lights removed, shake released, post-effect neutralised, connections and tasks cancelled. Replay,
  leaving the area, dying and interrupting mid-sequence all return the presentation to idle.
- Pool and reuse cue instances that fire often; instantiating a fresh model per swing is a visible
  hitch. One MeshId loads once and instances cheaply — reusing the same mesh across effects is free
  quality.

## 8. Sound is half of the feel

Cue audio is triggered by the presentation, but the assets and the mix belong to the sound owner.
A hit normally carries three layers on separate timings: **swing / whoosh** at the start of the
wind-up, **impact** only when contact actually happens, and **victim reaction**. Spells add a
charge layer under the anticipation and a tail under the dissipate. If a sound the cue needs does
not exist yet, name the hook and report it; do not silently drop the layer or grab an arbitrary
asset. Cap simultaneous identical hit sounds — stacked copies of one impact sound read as
distortion, not power.

## 8b. Libraries to put in the kit instead of building from nothing

Open-source and cheap building blocks that VFX artists on the platform actually use in 2026. Bring them
into `ServerStorage.StyleKit/VFX` once (Creator Store ids through `insert_asset`, GitHub modules through
the code owner) and reference them from cues; do not re-author a lightning bolt or a camera shaker.

- **Effect Designer Suite** (iGottic, 2026-07, open source): emit-property editor, bezier/tween animator
  for parts and meshes, and a library of roughly seven thousand open-source flipbooks and particle
  textures in a standard effect format with a runtime player (`miagobble/effect-player`, wally/pesde).
  The first place to look for a texture. DevForum topic 4754553.
- **Lightning Beams** (Quasiduck, MIT, `github.com/SamyBlue/Lightning-Beams`): LightningBolt with perlin
  noise and bezier control, sparks and explosion helpers; the storm-dragon arcs come from here.
- **VSV** (Creator Store 118384350930474, open source): voxelizes a mesh into particles with noise
  dissolve; deaths, portals, transformations.
- **Open-Source Mesh Flipbook Pack** (DevForum 3635032): smoke ball, dissolve, shockwave meshes; the
  reference format for mesh flipbooks.
- **GG Camera Shake** (MIT, wally `hysteriabee/gg-camerashake`): kick, perlin and bounce shakes with
  direction and presets; or Sleitnick's RbxCameraShaker.
- **Refx** (wally / `@rbxts/refx`): replicate cues to clients without server-side instancing.
- **VFX Editor** (VirtualButFake, MIT, Creator Store 18800449515): bezier NumberSequence editor and a
  texture store with flipbooks; a GUI tool, useful as a source of curves and textures.
- **Sine VFX** (Creator Store 96645663824840, $5): about fourteen thousand textures, beams, meshes,
  mesh flipbooks and sounds; the licence of the bundled assets is not stated by the author, so ask
  before shipping a game with them.
- Hitstop and impact frames have no library worth taking; they are twenty lines of client code
  (Highlight + a client-side ColorCorrection instance + `AnimationTrack:AdjustSpeed(0)` for a few frames).

## 9. Tools

- **Studio MCP** does the work: `execute_luau` to build and tune instances in batches,
  `start_stop_play` plus `screen_capture` to see the cue in motion (a still cannot verify timing),
  `get_console_output` for errors, `search_asset`/`insert_asset` for textures and meshes,
  `generate_mesh` for a VFX shape you cannot find, `upload_image` for a texture you produced.
- **Plugins worth knowing about as references** (they are GUI tools, not agent tools): VFX Studio
  (real-time property panels, bezier curve editor for property animation, texture/mesh library),
  VFX Forge (mesh VFX, decal flipbooks, ring/line/debris rock effects, custom tween properties),
  SteakParticles.
- Verification is visual and in motion: run the cue, capture from the player's camera, watch the
  capture. Property values in Edit prove nothing about how a cue reads.

## 10. Failures that mark an effect as amateur

- Default or hard-edged sprite textures; visible alpha rectangles.
- Flat Color/Size/Transparency instead of sequences; identical rotation on every particle.
- No anticipation: the burst appears with no warning and no build.
- No dissipate: everything vanishes on the same frame.
- One emitter doing all the work; no light, no shake, no sound, so nothing lands.
- The effect floats: nothing in the scene is lit or moved by it.
- Additive brightness used as a substitute for shape — a white blob with no silhouette.
- Screen-filling opacity that hides the enemy, the route, the objective or the HUD at the exact
  moment the player must act.
- Effects driven by `Rate` for one-shot events, so they arrive late or never stop.
- Effects built on the server and replicated part by part.
- Residue: emitters still running after the cue, lights left in the scene, pooled models leaking.
- The same effect at the same scale for a small event and a huge one.

## Sources

Verified links (official docs and announcements):

- ParticleEmitter reference: https://create.roblox.com/docs/reference/engine/classes/ParticleEmitter
- Particle effects, beams and trails: https://create.roblox.com/docs/effects/particle-emitters ,
  https://create.roblox.com/docs/effects/beams , https://create.roblox.com/docs/effects/trails
- Emissive masks live for published experiences (Feb 2026):
  https://devforum.roblox.com/t/emissive-masks-are-now-live-for-published-experiences/4357705
- Design for performance (overdraw, transparency, mesh reuse):
  https://create.roblox.com/docs/performance-optimization/design
- MeshPart usage and performance:
  https://devforum.roblox.com/t/meshpart-usage-performance-optimizations/1319217
- Beyond the Dark, sound design (layered bed plus spot sources, groups as buses):
  https://create.roblox.com/docs/resources/beyond-the-dark/sound-design
- Studio MCP tools: https://create.roblox.com/docs/studio/mcp
- Sleitnick RbxCameraShaker (EZ Camera Shake port, presets Bump / Explosion / Earthquake /
  HandheldCamera / Vibration): https://github.com/Sleitnick/RbxCameraShaker

Community craft, cited by thread title (search the DevForum by title rather than trusting a
remembered thread ID): "Breakdown on how VFX work" (particles + beams + trails, Rate 0 with Emit,
lifetime tuning); the particle flipbook announcement "Particle Flipbooks: Animated Textures for
Particle Emitters"; mesh VFX feature-request thread on the absence of a native mesh VFX tool;
threads on scrolling a Texture on a MeshPart (`OffsetStudsU/V` needs real mesh UVs, not
Roblox-generated ones or SpecialMesh); impact-frame threads (speedlines plus ColorCorrection plus
Highlight); hitstop threads on `AnimationTrack:AdjustSpeed(0)` being reliable only on the client
playing the track; anime-VFX guides on `FireAllClients` with a shared CFrame and keeping the hitbox
separate from the visual. Plugin references: VFX Studio (Sytranom), VFX Forge, SteakParticles.

Provenance rule: when this file and the live Studio API disagree, the live API wins — read the
tool schemas and the class reference before building on a property named here.
