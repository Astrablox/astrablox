---
name: roblox-lighting-atmosphere
description: Craft reference for lighting a Roblox place and for judging how it looks - LightingStyle and the current lighting API, sun and sky, ambient and exposure, Atmosphere, the post-processing stack, motivated local light rigs, godrays, mood approaches for fantasy scenes, starting-point values and the failures that make a Roblox place look cheap. Read it before setting lighting properties or reviewing captures of a scene. Audio craft for the sound mix lives in references/audio.md. Not for geometry, materials, particle effects, UI or gameplay code.
---

# Lighting and atmosphere in Roblox

This is what the job actually consists of, what each control does, and how to tell whether the
result is good. Values here are starting points for a look, never targets: the frame decides,
not the number. Where a source is weak (one builder's recipe rather than documentation or a
shipped game) it is marked, because weak advice is worth trying and not worth defending.

## 1. The current API - use these, not the old ones

`Lighting.Technology` (Voxel / ShadowMap / Future) is **deprecated**. Every tutorial and forum
thread written before 2025 says "use Future lighting"; that mode is now reached through:

- `Lighting.LightingStyle`
  - `Realistic` - high-fidelity lighting with detailed shadows and shading. Local lights cast
    shadows. This is what old threads mean by Future.
  - `Soft` - flatter, diffused shadows, lower contrast, non-directional.
- `Lighting.PrioritizeLightingQuality` - when enabled the engine keeps lighting quality and
  degrades other things first (draw distance, for example).
- Old mode mapping: Future -> Realistic + PrioritizeLightingQuality on; ShadowMap -> Soft +
  PrioritizeLightingQuality on; Voxel -> Soft + off.
- `Lighting.ShadowSoftness` (0 hard to 1 soft) only has a visible effect under `Realistic`.

Set both properties deliberately at the start of the job. A place that inherited defaults has no
lighting decision in it, and "it was already like that" is the reason most Roblox scenes look
identical.

Two engine facts that change what you can plan:

- **Emissive surfaces and Neon do not light anything.** Emissive masks
  (`EmissiveMaskContent`, `EmissiveStrength`, `EmissiveTint` on SurfaceAppearance /
  MaterialVariant / TerrainDetail, live since February 2026) glow and bloom exactly like Neon,
  but cast no light on neighbouring geometry. A glowing rune that should illuminate the wall
  needs a real light next to it, colour-matched, or the wall stays black.
- **Local light radius is capped at 60 studs** and a moving light with a large radius inside a
  building re-renders shadows every frame. Under `Realistic`, aim for well under fifty
  shadow-casting sources visible in one frame; light a large hall with a few motivated sources
  and let ambient carry the rest rather than filling it with small lamps.

Apply lighting through `execute_luau` in batches (set the service properties, then create or
retune the rig) and read the instances back; capture with `screen_capture` from an explicit
camera position and look-at so the before and after frames are the same shot. Tool detail is in
`$roblox-studio-mcp`.

## 2. How the job is done

**Motivated light.** Every source in the frame has a visible cause: the sun, a window, a fire, a
torch, a shaft through a broken roof, a glowing thing. The player never reasons about it, but an
unmotivated pool of light on a floor reads as a bug, and a fire with no light coming off it reads
as a prop. Motivation is also a design tool: to light a dark corridor, put a reason in it -
a brazier, a crack in the ceiling, a lantern the player carries.

**Key, fill, rim.** The key is the one dominant source that defines the direction of the light
and where the shadows fall. Fill is the ambient and bounce that keeps the shadow side from going
to nothing. A rim, or edge, source behind a subject separates it from the background - it is what
makes a statue or a creature read as a shape rather than as a silhouette merged into a wall. In
Roblox the key is usually the sun or the strongest local source, the fill is `Ambient` /
`OutdoorAmbient` plus the environment scales, and the rim is a deliberately placed light behind
the focal object.

**Value hierarchy.** Before colour, decide the range: which part of the frame is the darkest,
which is the brightest, and where the eye lands. The most common failure of an AI-lit or
beginner-lit scene is that every surface sits in the same middle value - the scene is "lit" and
completely flat. Deep shadow is a material you place on purpose, not a mistake to correct.

**Exposure before lights.** Set the overall exposure and ambient level so the scene reads at the
intended time of day with the geometry it has, then add local sources for what needs emphasis.
Doing it the other way - a rig of lamps, then global brightness raised until it "looks visible" -
produces a washed frame with no hierarchy and twice the light cost.

**Light leads the route.** The path the player must take and the thing they must notice get more
light, more contrast or more colour separation than their surroundings. This is how a scene stays
readable without being bright: readability is contrast, not brightness.

**Colour has a source.** Warm key against cool ambient (firelight in blue dusk, torch against
moonlight) reads as depth and time of day. Colours picked per lamp with no shared logic read as
Christmas lights. Ambient colour should relate to the sky - a scene under a green sky with grey
ambient looks broken and nobody can say why.

## 3. The controls, by what they do

**Sun, moon, sky.** `ClockTime` and `GeographicLatitude` place the sun; low angles give long
shadows and rim light and are worth far more than any post effect. The `Sky` object holds the
six skybox faces plus `SunAngularSize` / `MoonAngularSize` (the size of the sun disc, which also
drives how sun rays read) and `StarCount`. The default Roblox skybox rarely fits a designed look;
replacing it is one of the cheapest large upgrades available, and the reference for colour and
intensity is a photograph of the real sky you are imitating.

**Ambient and environment response.**
- `Ambient` - light present everywhere, including where the sun does not reach. Raising it is
  the fastest way to destroy contrast; it is a fill, not an illumination source.
- `OutdoorAmbient` - ambient for areas open to the sky.
- `ColorShift_Top` / `ColorShift_Bottom` - tint from the direction of the sun and from below.
- `EnvironmentDiffuseScale` / `EnvironmentSpecularScale` - how much the skybox contributes to
  diffuse and specular response. asimo3089 (Jailbreak) sets both to 1 and then tunes the rest;
  a common range in forum practice is roughly 0.5 to 1. This is what makes PBR materials react
  to the sky instead of looking like flat plastic.
- `Brightness` - the sun's strength. Too high is the single most frequent beginner error; a low
  value with correct exposure looks better than a high one with washed highlights.
- `ExposureCompensation` - camera exposure. Negative exposure with higher brightness is a
  documented builder trick for "crispy" daylight and for taking the glare off Neon [weak
  source, but widely repeated]; positive exposure lifts a night scene without flattening ambient.

**Atmosphere** (an `Atmosphere` object under Lighting; official documentation):
- `Density` - more particles, more obstruction of the view. Small amounts create the sense of
  scale and distance that makes a world feel large; large amounts are fog.
- `Offset` - higher values create horizon silhouettes, lower values blend distant objects into
  the sky. Balance it against `Density` so the skybox does not show through solid objects.
- `Haze` - visible above the horizon and into the distance; `Glare` (the halo around the sun)
  only works when `Haze` is present.
- `Color` and `Decay` - the tint near the sun and the colour the atmosphere falls off toward on
  the opposite side. Decay is how you get a warm horizon and a cool zenith in one scene.

Atmosphere is the difference between "a set" and "a world with distance in it", and it is also
the most abused control in Roblox: players of Arcane Odyssey complain the fog is far too common.
Fog that hides unfinished geometry is a lie the art review will catch.

**Post-processing** (children of Lighting; all documented):
- `ColorCorrectionEffect` - Brightness, Contrast, Saturation, TintColor. Contrast is where a flat
  scene gets its punch; saturation is where a scene gets its mood.
- `BloomEffect` - Intensity, Size, Threshold. Raise the threshold so only genuinely bright things
  bloom; low thresholds make the whole frame milky.
- `SunRaysEffect` - a halo around the sun with rays formed by objects between camera and sun.
  Strong values blind the player.
- `DepthOfFieldEffect` - focus falloff. In a game with a third-person camera it is used sparingly
  and mostly at distance.
- `ColorGradingEffect.TonemapperPreset` - the tonemapper decides how highlights roll off across
  the whole image. `Default` gives vivid colours and high contrast; `Retro` reproduces the
  pre-2019 look. Choosing the tonemapper is a bigger stylistic decision than any single effect.
- `BlurEffect` - almost always a mistake outside menus and cutscenes; players read it as a bug.

Stack order used in practice: colour correction, bloom, depth of field, sun rays [weak source].
Effects multiply: atmosphere density plus depth-of-field intensity plus bloom applied at
individually reasonable values gives a frame with nothing in it.

## 4. Local lights

`PointLight` (omnidirectional), `SpotLight` (cone, the tool for pools of light and for pointing
at things), `SurfaceLight` (emits from a face; casts noticeably harsher shadows than a spot).
Each has Brightness, Range, Color, and `Shadows`.

Decide per source whether it casts shadows. Shadow-casting sources are what make a torch feel
real - they put the pillar's shadow on the floor - and they are the expensive ones. A workable
pattern is one or two shadow-casting sources per space carrying the drama, plus non-shadowing
fill where light needs to exist but not to be dramatic.

Local sources also do something for gameplay that nothing else does: the environmental art
curriculum calls them points of reference and directionality for users. A lit doorway at the end
of a dark hall is a navigation instruction that needs no HUD.

Where no fixture exists, an invisible non-colliding anchor part holds the light. Where a fixture
exists, parent the light to it so it moves with it.

## 5. Volumetrics - light shafts and godrays

Roblox has no volumetric lighting and no custom shaders. Three ways builders fake shafts, from a
2025 practitioner thread:

- **Beams** - good for sun shafts, receive shadows, do not work with point lights.
- **Meshes** (a cone or blade of translucent geometry) - work for both sun and point lights, but
  they look wrong from some angles and are expensive.
- **Billboards** - look the best, get shadows only under Realistic lighting, and can be
  expensive.

Whichever you pick, the shaft belongs to a source that exists and lands somewhere the eye should
go. A shaft in an empty corner is decoration; a shaft landing on the thing the player must find
is direction. Dust drifting inside a shaft is a particle effect and belongs to the VFX owner -
build the shaft, ask for the dust.

## 6. Moods - approaches, not recipes

Each of these is a relationship to establish. The values that produce it depend on the geometry
in front of you, so build the relationship and then look at the frame.

**Storm approaching over a mountain pass.** The key is a sun low and partly defeated: brightness
present but the sky doing most of the work, ambient cool and raised slightly so shadows are grey
rather than black. Atmosphere carries the weather - density enough that ridge after ridge
separates into planes, colour cold, decay colder away from the sun. A single band of warmer light
under the cloud line, in the direction the player is heading, gives the scene its focus and the
route its promise. Contrast comes from the value gap between the lit band and the mass of the
mountain, not from local lights - there are almost none outdoors.

**Sunset "half-light".** Players of Arcane Odyssey single out sunrise and sunset - "soft bronze
sunlight" - as the game's best-looking hours, and the reason is that low sun gives long shadows,
rim light on every edge and a warm-to-cool gradient across the frame for free. Set the sun low,
warm the tint near it, keep ambient cool so the shadow side reads blue, and let the atmosphere
decay carry the sky from bronze to slate. Watch the exposure: at this hour the highlight rolls
off badly if brightness is too high, and the bronze turns to white.

**Underground with bioluminescence.** No sun. The place is defined by what glows in it and by how
far the light does not reach. Ambient near zero, coloured slightly toward the glow; a small
number of shadow-casting sources at the glowing things; large areas left genuinely dark so the
lit ones matter. Since emissive materials cast no light, every glowing mushroom or vein that
should illuminate its surroundings needs a matched light beside it. Depth comes from a distant
glow the player can see before they can reach it.

**A magic source as the key light.** When a rune, a portal or a spell is the brightest thing in
the scene, treat it exactly as you would treat a fire: it defines the direction of the shadows,
it colours the surfaces facing it, its light falls off, and the character standing next to it is
lit from that side. This is what makes magic look expensive in Roblox - not the particle effect,
but the fact that the room reacts to it. Where the effect is animated by the VFX owner, agree
which light is yours and static and which one pulses with the cue.

**Moonlit night.** The mistake is black. A night that reads is a dim blue key from a low moon
with real direction, ambient not at zero but low and blue, a warm accent or two for anything
that matters, and enough atmosphere for the moon to have a glow. Old forum advice to set ambient
to pure black produces a scene where players see nothing and turn up their monitors.

## 7. Starting points

These come from documentation examples and from builders' recipes on the forum. Treat them as a
place to begin an experiment on a scene you then look at; none of them is a target and none of
them is a pass condition.

- Environment diffuse and specular scales around 0.5 to 1 for a scene where materials should
  react to the sky.
- Atmosphere density in the low tenths for outdoor air with scale; roughly a third and above
  starts reading as weather; heavy values are horror fog. Documentation examples run from 0 to
  about 0.35. Glare only with haze present.
- Bloom: raise the threshold until only the sun and genuine light sources bloom.
- Colour correction: contrast around a tenth to a fifth adds punch without crushing shadows;
  saturation lifted slightly for sunlight, pulled down and tinted cold for dread.
- Sun rays: low intensity. The complaint that recurs is that they blind players.
- Negative exposure compensation with raised brightness for a crisp daylight scene; the same
  builder notes it also removes glare from Neon [weak source].
- Ambient colour: keep it related to the sky colour rather than neutral grey.

## 8. What makes a Roblox scene look cheap - in the words of the people who see it

- "very dull, green, and grey" - low contrast, everything in one value. The fix is more shading
  and darkness with areas that are not bright, not more lights.
- Brightness too high. The most frequent single mistake.
- Overusing depth of field, saturation and bloom; sun rays that blind; blur that players read as
  a broken screen.
- Fog everywhere: "way too FOGGY" is the top visual complaint against a game otherwise praised
  for its lighting.
- The default skybox. It rarely fits any designed look.
- Default Studio shadows on default terrain, and auto-generated terrain under them.
- Materials with a colour map and no normal or roughness: "surfaces still look flat" no matter
  how good the lighting is. That is the world-builder's fix, and it is worth naming in a report
  rather than compensating for with light.
- Style mismatch: rocks that do not match the terrain, models that look "like plastic",
  background mountains in a different style from the foreground.

## 9. Checking your own frame

Capture the acceptance views from fixed camera positions before you touch anything and again
after, so you compare shots rather than memories. Then, on each after frame:

- **Read it for value alone, ignoring colour.** If the frame collapses into one tone, there is no
  value hierarchy - the lighting is not finished regardless of how nice the colour is.
- **Where does the eye go first?** Whatever is brightest and highest in contrast wins. If that is
  a wall, a floor or an empty patch of sky, the frame is pointing at the wrong thing.
- **Cover the focal point with your hand.** If the frame still looks fine, the focus was not
  carrying it and the composition has no centre.
- **Find the cause of every light.** Any pool with no visible reason is a defect.
- **Compare with the before frame.** If shapes that were legible before have disappeared, you
  hid the scene rather than lit it.
- **Look at the far distance.** In an open view something has to happen at the horizon: haze, a
  landmark, cloud, a lit ridge. A frame that ends in flat sky reads as a demo level.
- **Then subtract.** Remove any light or effect whose removal you cannot see. Scenes get worse by
  accumulation far more often than they get worse by restraint.

## Sources

Strong (documentation, shipped games, engine announcements):
- Unified Lighting / LightingStyle: https://devforum.roblox.com/t/let-there-be-unified-light-unified-lighting-is-fully-live/3401512
- Atmosphere: https://create.roblox.com/docs/environment/atmosphere
- Post-processing effects: https://create.roblox.com/docs/environment/post-processing-effects
- Emissive masks (glow without light): https://devforum.roblox.com/t/emissive-masks-are-now-live-for-published-experiences/4357705
- Lighting cost and the 60-stud radius: https://medium.com/@zeuxcg/the-future-is-bright-updating-lighting-systems-in-roblox-27dcc85cc391
- Environmental art curriculum (local lights as reference and directionality):
  https://create.roblox.com/docs/tutorials/curriculums/environmental-art/construct-your-world
- Volumetric options compared by a practitioner:
  https://devforum.roblox.com/t/help-with-lighting-and-light-manipulation/3683740
- asimo3089 on environment scales: https://x.com/asimo3089/status/1224555613121736704
- Creator interviews on PBR, emissive and 4K textures:
  https://about.roblox.com/newsroom/2026/07/roblox-studio-fidelity-creator-interviews-twin-atlas-fluorlite-maximillian-ecos

Weak (single-builder recipes and third-party guides; useful to try, not to cite as law):
- https://devforum.roblox.com/t/improve-lighting-step-by-step/1387033
- https://devforum.roblox.com/t/tips-on-realistic-lighting/1261456
- https://devforum.roblox.com/t/development-tips-better-lighting/580976
- https://devforum.roblox.com/t/tips-tricks-for-improving-your-game-using-lighting/1062421
- https://simplified.media/guides/roblox-lighting-atmosphere
- Player discussion of Arcane Odyssey visuals (half-light praise, fog complaint):
  https://forum.arcaneodyssey.dev/t/week-of-discussion-1-visuals/125959
