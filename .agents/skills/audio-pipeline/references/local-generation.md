# Generating sound locally, with open weights only

The third source, after the Creator Store and the catalogued packs. It exists so that an entry
nobody else can fill does not block a scene - not so that searching can be skipped. Nothing here
costs money and nothing here calls a hosted service.

Status in this checkout: none of these models is installed and none of the commands below has been
run here. Treat the first run as setup work, report what actually happened, and record the model
version and the exact prompt in `provenance.json`.

## The licence rule, first

Check the licence of the **weights**, not of the repository. Meta's AudioCraft is the standing
example: the code is MIT and the MusicGen and AudioGen weights are CC-BY-NC 4.0, which forbids the
commercial use a shipped game is. MiniMax Music 3 (open weights, August 2026) is another - weights
published, commercial use not granted. A model whose weights do not permit commercial use is not an
option here, however good it sounds.

## What to use

**Stable Audio 3, open-weight variants** - effects, ambience and music.
Released 2026-05-20 (https://stability.ai/news-updates/meet-stable-audio-3-the-model-family-built-for-artistic-experimentation-with-open-weight-models,
code at https://github.com/Stability-AI/stable-audio-3).

- Variants with weights: `stabilityai/stable-audio-3-small-sfx` and `stabilityai/stable-audio-3-small-music`
  (433M, up to 120 s, about 2.4 GB peak VRAM, will also run on CPU), `stabilityai/stable-audio-3-medium`
  (1.4B, up to 380 s, about 6.5 GB VRAM, CUDA, Flash Attention 2). The Large variant is API-only and
  therefore out of scope.
- Licence: Stability AI Community License. Stability states the models are trained on fully licensed
  data and that outputs may be distributed and commercialised under that licence by organisations
  below the revenue threshold it names; above it, an enterprise licence is required. Read the licence
  text before the first shipped build and write what it permits into provenance.
- Output is stereo at 44.1 kHz - inside Roblox's limits without resampling.
- It supports inpainting and continuation: a short recording can be extended rather than replaced,
  which is the cleanest way to lengthen a bed that is almost right.
- Runs on Windows and Linux; the repository installs through `uv`.

**ACE-Step 1.5** - music only, when a full piece is needed fast.
Released 2026-01-31 (https://github.com/ace-step/ACE-Step-1.5, paper arXiv 2602.00744). MIT licence
on the 1.5 release, commercial use explicitly allowed. Under 4 GB VRAM, a full song in seconds on a
consumer card, multilingual lyrics, up to a few minutes.

## How to prompt for something a game can use

The same description that went into the sound list is the prompt: the object, its material and size,
the force, the space, the distance. "Heavy oak door with iron hinges dragged open slowly in a stone
hall, close mic, no music" beats "ominous door". Say what must not be there - music under an effect,
voices, reverb you intend to add in the engine yourself - because generators add atmosphere by
default and a bed with baked-in reverb cannot be placed in two different rooms.

Generate several takes per entry and let the gate choose among them. Generation is cheap; a bad take
in the catalogue is not.

What these models are good at: textures, weather, room tone, impacts, whooshes, magic, machinery,
instrumental beds. What they are bad at: anything the player will recognise as a specific real
object heard up close, and long tonal material that has to stay clean for minutes. If the Store has
the sound, the Store's recording wins.

## Making a generated file usable

Generated material almost always needs three fixes, and all three are mechanical:

```
# trim the silence a generator leaves at the ends
ffmpeg -i raw.wav -af "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse" trimmed.wav

# turn a take into a seamless loop: overlap the tail onto the head
ffmpeg -i trimmed.wav -filter_complex "[0]atrim=0:20,asetpts=N/SR/TB[a];[0]atrim=20:22,asetpts=N/SR/TB[b];[b][a]acrossfade=d=2" loop.wav

# apply the gain the gate suggested for this sound's place in the scene
ffmpeg -i loop.wav -af "volume=-4.5dB" final.wav

# bring a pack file inside the platform limits
ffmpeg -i pack_96k.wav -ar 48000 -ac 1 -c:a pcm_s16le final.wav
```

Then run `tools/audio/gate.py final.wav --role <role> --loop --strict`. Generated audio goes through
the gate in strict mode because its typical failures - a click at the loop, a tail cut mid-decay, a
hiss-heavy spectrum - are exactly the warnings that would otherwise be waved through.
