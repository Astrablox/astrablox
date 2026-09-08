---
name: audio-pipeline
description: How this studio gets sound it cannot listen to - deriving the sound list from a scene contract, the order of open sources (Roblox Creator Store, catalogued CC0 packs, local open-weight generation), licences, choosing between candidates on descriptions and metadata, the objective gates, levels and loudness across a scene, layering, ducking and adaptive music design, and the placement package handed to the studio lane. Read it before searching for a single sound. Sources, licences and endpoints are in references/sources.md, the meaning of every gate number in references/gates.md, running the open models locally in references/local-generation.md. Not the in-engine wiring craft - that is roblox-lighting-atmosphere/references/audio.md.
---

# Sound for a studio that cannot hear

Everything in this file follows from one fact: nobody in this pipeline can listen. No agent, no
judge, no reviewer. The owner may hear the build eventually; between now and then, sound quality
has to come from somewhere other than an opinion about how it sounds.

It comes from three places, and they are the whole method:

1. **The source.** A recording made by a sound house is pleasant because a person made it pleasant.
   A synthesised beep assembled out of primitives, or a generation nobody vetted, is a gamble.
   Choosing the right shelf is most of the work.
2. **The description.** A library asset arrives with the recordist's own words - what the object
   was, what it did, where it was recorded, whether it loops. Matching those words against what
   the scene needs is how selection happens without ears.
3. **The measurement.** Clipping, silence, a cut tail, a click at the loop point, one sound sitting
   far above the rest - these are the defects that reach a player as "unpleasant" and "strange",
   and every one of them is a number. `tools/audio/gate.py` on files, `tools/audio/probe.luau` on
   Store assets in Studio.

A sound with no named source, no description and no gate result is not a sound this studio ships.

## 1. The sound list comes before any searching

The scene contract from the story lane says what happens and where. Turn it into a list before you
open a search, because a list written while searching is a list of what happened to be easy to find.

For every entry write, in this order: the **name** other lanes will use, the **role** (bed, spot
ambience, footstep set, interaction, combat layer, creature voice, interface, music, stinger), the
**place or event** it belongs to, and then the part that does the work - **what physically makes
this sound**: the object, its material and size, the force applied to it, the space it is in, the
distance and the time of day. "Heavy oak door, iron hinges, dragged open slowly, stone hall" is a
search query, an acceptance test and a brief for a generator all at once. "Ominous door sound" is
none of those things: it is an adjective, and adjectives cannot be matched against a library.

Then say what shape the file has to be: looping or one-shot, roughly how long the event lasts, mono
for a positional emitter or stereo for a bed. Do not decide the level here; level is decided across
the whole scene later, in one pass.

Entries the list must not be missing, because their absence is what makes a place feel dead: the bed
for every space the player stands in, footsteps for every surface they walk on, and a sound for every
interaction and every hit the code and effect lanes already trigger by name. Those names are declared for the whole studio in
`game/src/shared/Presentation.luau` - fill them, never rename them and never spell a variant; a
renamed source is a cue that plays silence in somebody else's review.

## 2. The order of sources, and why it is this order

Full detail, licences and endpoints: `references/sources.md`.

1. **Roblox Creator Store audio** (`tools/audio/store_audio_search.py`). Free, plays by asset id
   inside the experience, costs no upload quota, and the professional catalogues on it - Pro Sound
   Effects for effects and ambience, APM for music - are recordings with real descriptions. This is
   the default; look here first for every entry.
2. **Catalogued open packs on disk** (`assets/library/audio/`) - the Sonniss GDC bundles, Kenney's
   CC0 sets, CC0 uploads on OpenGameArt. Use when the Store has nothing that matches the
   description. These files cost upload quota and must be resampled to Roblox's limits.
3. **Local generation with open weights** (`references/local-generation.md`) - Stable Audio 3
   small-sfx and small-music, ACE-Step 1.5 for music. Only for entries the first two could not
   fill, and only from models whose *weights* allow commercial use. Generation is the last resort,
   not the first idea: it costs upload quota too, and it is the one source where nothing guarantees
   the result is pleasant.

Paid services are out of the question in this studio - no ElevenLabs, no Suno, no subscription
libraries, whatever their quality. The upload budget is the other hard limit: audio uploaded through
Open Cloud is capped per month, so every sound taken from disk or generated spends a scarce resource
while a Store asset spends none. Say in the report how much of that budget the scene consumed.

## 3. Choosing between candidates without hearing them

Search wide, then choose. One search that returns one usable result has not established anything -
the first candidate is a candidate.

What decides:

- **The description against the entry.** The publisher wrote what the sound is; your list says what
  it needs to be. Read the whole description, not the title: the title says "Metal Hits 5", the
  description says which metals, whether it is a single hit or a series, and whether it loops.
  A candidate whose description contradicts one part of the entry - a jungle recording for a
  northern forest, a series of hits where the scene needs one - loses.
- **Who published it.** A verified sound house has a consistent chain, level and edit across its
  whole catalogue, which is exactly what a scene needs from a set of sounds. An anonymous upload
  named "sword hit or swing" may be perfect and there is no way to know.
- **Duration against the event.** The gate rejects wrong lengths later; catch them here.
- **Consistency with the sounds already chosen for this scene.** A bed from one recordist and its
  spot ambiences from another read as two different places. Prefer taking a scene's ambience family
  from one library.

Record the choice with what it beat and why - the rejected ids and the reason, one line each, in
the sound's `provenance.json`. That record is what makes the choice reviewable by someone who also
cannot listen, and it is what stops the next pass from re-picking a candidate already rejected.

## 4. Gates: what actually gets measured

Numbers and their meanings: `references/gates.md`.

- Files on disk go through `tools/audio/gate.py` before they enter the catalogue. Give it the whole
  set of a scene in one call, because the most valuable thing it reports is the **spread** across
  the set and the gain each file needs to sit level with the rest. A mix where one sound is far
  above its neighbours is the most common way audio reads as broken, and it is entirely preventable
  with arithmetic.
- Store assets never touch the disk, so they go through `tools/audio/probe.luau` in Studio: does the
  asset load at all, how loud is it, where is its energy, how much of it is silence.
- A check that could not run is not a check that passed. `unmeasured` fails the file; using
  `--allow-unmeasured` is a decision that belongs in the report with the reason.

The gates do not judge whether a sound is the right sound. That is the description match, and it is
yours.

## 5. Level is a scene-wide decision, made once

Pick the loudest moment the scene will ever have, and set everything relative to it. Then use the
measured loudness of every asset to compute one gain per sound, so that assets recorded a decade
apart on different chains arrive at the player as one mix. Write the gains into the placement
package; do not leave "set it by ear later" for a lane that also has no ears.

The relationships that hold a mix together, in the order they must survive: a telegraph, an
interaction and an impact are audible over everything else at the moment they matter; the bed is
present but never competes; music never covers either, and it ducks under both. If a sound had to
be turned down to nothing so another could be heard, the two are fighting in the same range and the
fix is ducking or a different asset, not more gain.

## 6. What makes a place sound designed rather than filled

- **A bed and spots.** One non-positional layer establishes the space; positioned sources sit on
  things the player can see, so the ear can point at what the eye finds. Either one alone is not a
  design. The in-engine mechanics of this - emitters, rolloff, reverb zones, buses - are the studio
  lane's craft in `roblox-lighting-atmosphere/references/audio.md`; what you own is deciding which
  sounds exist and what each one is for.
- **Layers of unequal length.** Beds built from layers whose lengths share no common factor take the
  product of those lengths to repeat their combination. Equal-length layers restart together and the
  seam is audible within a minute.
- **A hit is three sounds.** The swing at the start of the animation, the impact on the frame the
  damage resolves, the reaction of whatever was hit. One sound covering the whole exchange makes
  every miss sound like a hit.
- **Footsteps belong to surfaces, not to characters.** One set per material the player can walk on,
  with enough variants that a run does not machine-gun.
- **Silence is allowed, but it has to be legible.** A space with no bed needs the sound that stops
  at its doorway, or one distant source, so the player hears a decision rather than a missing file.
- **Interface sounds are the easiest place to be cheap.** Few, short, quiet, and never a synthesised
  beep when the world is a medieval forest.

## 7. Music and adaptive layers

Music is optional and always separable: it must be possible to fade it out entirely without the
scene losing information. Choose it the same way as everything else - from the Store's music
catalogues, or generated locally with a model whose weights allow it.

Two ways to make music follow the game, and they behave differently in this engine:

- **Horizontal** - separate pieces for exploration, tension and combat, swapped at a musical
  boundary with a crossfade. Robust: each piece is one asset, nothing has to stay in step.
- **Vertical** - stems of the same piece playing together, faded in and out by intensity. Musically
  better and mechanically fragile here: developers report that keeping two players in sample-accurate
  sync over time is not guaranteed on this platform, so stems can drift. If you use stems, keep them
  short, start them in the same frame, and say in the report that drift is the risk being taken.

Whichever you use, name the states the music has and what moves between them, and hand that to the
code lane as a specification rather than writing the lifecycle code yourself.

## 8. What you hand over

Per sound, `assets/audio/<name>/provenance.json`: what it is, where it came from with the licence
and what that licence permits, the asset id or the file, every gate result, the candidates it beat,
and its readiness state from the contract's ladder.

Per scene, `assets/audio/<scene>/placement.json` - the package the studio lane reads: for every
sound, where it lives (the space, the object, or the event name declared in
`game/src/shared/Presentation.luau`), positional or not, looping or one-shot, which bus, its gain,
and what ducks under what. Plus the reverb the spaces need and the
zones where beds change. Written so the studio lane can build it without asking a question, because
it cannot ask you one.

## 9. Failures to look for in your own delivery

- Every space in the scene got a loop, at similar level, and their descriptions in your own report
  are interchangeable. That is a filled place, not a designed one.
- A sound in the catalogue whose provenance says where it came from but not what its licence permits.
- A sound that passed no gate because the gate could not decode it, recorded as if it had passed.
- The scene's sounds measured over a wide loudness spread and shipped anyway.
- An entry from the contract with no sound and no line saying it is deliberately silent.
- A cue name from the code or effect lanes left unfilled, or filled under a different name.
- Generation used where the Store had the sound, spending upload budget for nothing.
