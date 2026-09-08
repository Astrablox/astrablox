# Audio craft in Roblox: ambience, mix, spaces, combat

Read this when designing what a place sounds like or when judging a mix. Everything below is
method and mechanics; levels are decisions you make while listening, and no number here is a
target.

## 1. Two audio stacks - pick one graph and stay in it

**Legacy:** `Sound` instances (parented to a part for positional audio, to SoundService or a
script for 2D), `SoundGroup` as a bus with `Volume` and effect children
(`ReverbSoundEffect`, `EqualizerSoundEffect`, `CompressorSoundEffect`, `PitchShiftSoundEffect`,
`DistortionSoundEffect`, `TremoloSoundEffect`), `SoundService.AmbientReverb`. Simple, well
understood, adequate for a bed plus a handful of spots.

**Audio API** (generally available since 2024, the current stack): a graph you wire yourself.
`AudioPlayer` produces the signal; `AudioEmitter` places it in the world; `AudioListener` (on the
camera, or wherever you decide the ears are) receives; `AudioDeviceOutput` sends to the player's
device; effects sit between them - `AudioReverb`, `AudioEqualizer`, `AudioCompressor`,
`AudioLimiter`, `AudioFader`, `AudioDistortion`, `AudioChorus`, `AudioFlanger`, `AudioPitchShifter`,
`AudioEcho`. `Wire` instances connect nodes. Because you build the routing, you get per-source
effect chains, real bus structures, directional emitters and limiting - which is what a designed
mix needs.

Rules of thumb: build the whole place in one stack. A mix half in SoundGroups and half in Wires
has two volume systems and nobody can predict the result. If you build with the Audio API, the
listener and the output device are part of the design, not boilerplate - decide where the ears
are (camera or character) and say so in the report.

**Acoustic Simulation** (`SoundService.AcousticSimulationEnabled`, `BasePart.AudioCanCollide`,
`PhysicalProperties.AcousticAbsorption`) gives occlusion through walls, diffraction around
corners and space-derived reverb. It has been a client beta since January 2026 and full release
was pushed to late 2026, so some clients will not have it. Design the mix so it reads without
it, and record in the report which of your judgements assumed it was on. `AudioCanCollide` and
absorption live on parts owned by the world builder - name the parts and the values, do not
retexture the world to fix a mix.

## 2. The method that works: bed plus spots

From the Roblox showcase Beyond the Dark, which documents its own sound design:

- A **2D omnipresent soundbed** is the base - non-positional, always there, establishing the room
  or the outdoors.
- **3D sounds attached to objects** - spot ambiences - "pull the user's ear". A dripping pipe, a
  brazier, a creaking mast, a waterfall in the distance. This is what converts a loop into a
  place: the ear can point at things the eye can also see.
- **Loops of different lengths.** Layers whose lengths share no common factor take the product of
  their lengths to repeat their combination, so the player never hears the same arrangement come
  back. Equal-length layers loop in step and the seam becomes audible within a minute.
- **SoundGroups as buses with a sidechain compressor** - "one audio source to duck the volume of
  another" - so that "all of the sounds are creating room for each other to breathe". Ambience
  ducks under interaction and threat; music ducks under both.
- **Reverb carries scale**: the whole point of the cave reverb is "making the whole thing feel
  like a cave". Reverb is a statement about the size of the space, and it has to change when the
  space changes.

Placement mechanics: a positional source is a Sound in a part (or an AudioEmitter) with a
rolloff. `RollOffMode`, `RollOffMinDistance` and `RollOffMaxDistance` decide how far the object
reaches; tune them against the neighbouring space so that bleed between zones is a decision.
Silence at a doorway is a design; silence because the rolloff was left at default is an accident.

## 3. Combat and interaction layers

A hit is three sounds, not one:

- **Swing** at the start of the animation - the whoosh that tells the player the attack started
  and gives the anticipation weight.
- **Impact** only when the hit actually lands, on the frame the damage resolves. An impact that
  plays with the swing makes every miss sound like a hit and destroys the feedback loop.
- **Reaction** from whatever was hit - a creature's grunt, metal ringing, stone cracking.

Beyond that: cap how many hit sounds can play at once, or a crowd fight turns into noise; vary
pitch and start offset slightly per play so a repeated attack does not machine-gun; keep threat
telegraphs on a bus that ducks everything else, because a telegraph the player cannot hear is a
combat design failure, not an audio detail. Practitioners describe the "crunch" of a good hit as
mostly a mix decision - a short transient that sits above the bed for a moment and then gets out
of the way.

Cue sounds are triggered by the effect owner's presentation code at a named path. Fill the path;
do not rename it.

## 4. Mix discipline

- Decide the loudest moment in the game first and set everything relative to it. A mix built
  quiet-to-loud clips at the climax; a mix built loud-to-quiet leaves the ambience inaudible.
- Every bus exists for a reason you can name: ambience, interaction, threat, music, interface.
  If a source does not belong to a bus, it will be the one nobody can turn down later.
- Masking is the enemy: two layers in the same frequency range at the same time means neither is
  heard. The fix is usually to duck or to move one of them, not to raise the other.
- Music is optional and always on its own bus. Continuous music under everything is the fastest
  way to make a game sound like a template.
- Deliberate silence is a design, but it needs a marker: the sound that stops at the doorway, or
  a single distant source that proves audio is alive.

## 5. Where sounds come from

- **Creator Store** through the Studio MCP asset search and insert. Free Store assets are usable
  in experiences under the Store terms; record the id and the source. Any script inside an
  inserted model stays disabled until the code reviewer has read it - free models are the known
  malware vector.
- **Too Lost catalogue** - thousands of tracks licensed for use in experiences, available in the
  Creator Store music library since July 2026. This is the legitimate route to music.
- **Own uploads** through the Open Cloud Assets API: `.mp3`, `.ogg`, `.wav`, `.flac`, up to
  seven minutes, 20 MB per call, and a hard monthly cap (about a hundred audio uploads a month
  for an ID-verified account, an order of magnitude fewer without). Everything passes moderation,
  which takes time. Treat it as a harness capability: if the brief did not give you an upload
  path, it is a blocker to name, not something to improvise.

For every source record: what it is, the asset id, where it came from, what it may be used for,
and whether it actually loaded in this place. An asset that failed to load is a missing
dependency with a name, not a placeholder.

## 6. What counts as evidence that it sounds right

In descending order of strength:

1. **Heard it** - the game running, walking the route, with an audio capture or the owner's ears.
   Only this supports a statement about how the mix sounds.
2. **Runtime state** - in a running session: the asset loaded, playback position advancing, the
   right sources active in the right zone, the listener where you expect it. This proves the
   plumbing, not the mix.
3. **Edit-mode inspection** - instances, routing, levels, rolloff read back from the tree. This
   proves the build, nothing more. A template Sound with Playing checked in Edit proves nothing
   at all.

Say which of the three each claim rests on. "Numeric inspection" and "listening" are different
words for a reason, and a mix signed off from a properties table reaches the player as noise.

## 7. Failures to look for

- The same ambience loop in every room, at similar level - the template sound.
- Ambience or music covering a telegraph, an interaction or a hit.
- A recognizable loop seam: layers of equal length restarting together.
- The same reverb everywhere, or none anywhere - the player never hears that they changed space.
- Duplicated loops after respawn or re-entering a zone, stacking up in volume.
- Sounds with no visible or narrative cause where the player is standing.
- Recognisable default library sounds used for signature moments.
- A sound in the tree that never loaded, left in place as if it were a placeholder.

## Sources

- Beyond the Dark sound design (bed, spot ambiences, loop lengths, SoundGroups and sidechain,
  scale reverb): https://create.roblox.com/docs/resources/beyond-the-dark/sound-design
- Audio API deep dive: https://devforum.roblox.com/t/robloxs-new-audio-api-a-somewhat-deep-dive/3156011
- Audio API features (directional audio, AudioLimiter and more):
  https://devforum.roblox.com/t/new-audio-api-features-directional-audio-audiolimiter-and-more/3282100
- Acoustic Simulation client beta (occlusion, diffraction, AudioCanCollide, AcousticAbsorption):
  https://devforum.roblox.com/t/client-beta-acoustic-simulation-emit-audio-with-presence/4307121
- Open Cloud Assets API limits for audio uploads:
  https://create.roblox.com/docs/cloud/guides/usage-assets
- Frontlines interview (six months on weapon audio; small details add up):
  https://about.roblox.com/newsroom/2026/07/roblox-studio-fidelity-creator-interviews-twin-atlas-fluorlite-maximillian-ecos


## Sources of sound the studio can call from a script

- **ElevenLabs Sound Effects API** (`POST /v1/sound-generation`, model `eleven_text_to_sound_v2`,
  0.5–30 s, `loop`, `prompt_influence`, WAV 48 kHz) and **Eleven Music** (`POST /v1/music`,
  `music_length_ms` up to ten minutes, `composition_plan` by sections, `force_instrumental`). Commercial
  use starts with the Starter plan; API billing about $0.12/min for effects and $0.15/min for music.
  Some plans ask for a credit line; read the music terms before release.
- **Roblox audio library and Too Lost catalogue** in the Creator Store: free, licensed only inside Roblox
  (not for trailers on YouTube), searchable with duration filters.
- Upload route matters: Open Cloud allows 100 audio uploads a month on an ID-verified account; Studio's
  own uploader allows 2000 per 30 days. Bulk sound goes through Studio.
- **AudioEngine** (`github.com/gmoddev/AudioEngine`, MIT, 2026-08): adaptive music from synchronised
  stems with state and parameter rules, buses with ducking, ambience emitters, voice budgets, on the
  new Audio API. New and unproven; architecturally the right shape for a boss fight.
- **Resonance** (Creator Store 107564850777477): one-object wrapper over the new Audio API with falloff
  curves and a spectrum analyser.
