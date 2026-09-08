# tools/audio - finding sound, proving sound

Three tools and one rule: a sound that has no named source and no gate result does not exist. The
audio lane may not put a sound in the catalogue on the strength of its own opinion, because nobody
in this studio can listen.

| Tool | What it answers | Where it runs |
|---|---|---|
| `store_audio_search.py` | what the Roblox Creator Store has for this entry, with duration, publisher and the publisher's own description | shell, no API key |
| `gate.py` | is this file broken in a way a listener would hear, and what gain does it need to sit level with its set | shell, on files on disk |
| `probe.luau` | does this Store asset load, how loud is it and where is its energy | Studio, through `execute_luau` |

## store_audio_search.py

```
store_audio_search.py "forest ambience loop" --min-duration 20 --max-duration 120 --publisher pse --limit 30
store_audio_search.py "sword impact metal" --sfx --max-duration 4 --limit 30 --json
store_audio_search.py "dark medieval orchestral" --music --min-duration 90
store_audio_search.py --ids 9112789512,9116653976        # verify ids before you commit to them
```

Verified live on 2026-09-08 against `apis.roblox.com/toolbox-service/v1`, no key, no cookie:

- audio category is **3** (`/marketplace/3`; the string `audio` also resolves), not 9 - 9 returns HTTP 400.
- filters that really narrow the set: `minDuration`, `maxDuration` (seconds), `audioTypes=Music|SoundEffect`,
  `creatorTargetId`, `limit` (100 accepted), `cursor`. `creatorName` is accepted and silently ignored.
- `items/details` returns for audio: `duration`, `audioDetails.artist/title/musicAlbum/audioType`, the full
  publisher `description`, creator with `isVerifiedCreator`, `fiatProduct.isFree`, votes, dates.
- publisher ids read off live results: ProSoundEffects `7462895450`, APMOfficial `7462718749`,
  DistrokidOfficial `7135127272`, Clippsly `3470791130`, Roblox `1`.

Trap, verified: library ambience often carries `audioType: "Unknown"`, so `--sfx` hides it -
`"forest ambience" --sfx --publisher pse` returns flashlight clicks. Use `--sfx` only to strip songs
out of a noisy keyword.

Store audio cannot be downloaded and its licence covers use inside a Roblox experience only. That is
why its check is `probe.luau` and not `gate.py`.

## gate.py

```
gate.py assets/audio/amb_forest/amb_forest.wav --role ambience --loop
gate.py assets/audio/*/*.wav --role oneshot --target-lufs -20 --json      # whole set: spread and gains
gate.py file.wav --strict                                                 # warnings fail too
```

Exit 0 all passed, 1 something failed, 2 the tool could not run. Checks: Roblox format, size, duration
and sample rate limits; clipping runs; sample peak; DC offset; share of silence; leading silence and
cut tail for one-shots; padding and seam for loops; spectral balance; L/R correlation. The seam check
compares the wrap step against the largest step the waveform takes on its own, so it works on a drone
and on a rain bed alike.

Loudness is reported under the name of the metric that produced it, never as a bare number:
`lufs_i` with `pyloudnorm`, `lufs_i_bs1770_own` with numpy and scipy (this file's own BS.1770-4
K-weighting and gating), `rms_dbfs` with plain Python (unweighted - not LUFS).

Decoding order: `soundfile` (wav, ogg, flac, mp3), `ffmpeg` on PATH, the standard library `wave`
module (PCM WAV only). With none of them the format and duration still come from the container
header, every level check reports `unmeasured`, and the file **fails** unless `--allow-unmeasured` -
an ungated sound is not a gated sound. One-time setup on the build machine: `pip install soundfile`
(and `numpy`, `scipy`; `pyloudnorm` if you want the reference meter). Only the WAV path and the
header parsers have been exercised in this checkout; the `soundfile` and `ffmpeg` branches have not.

Sonniss and other library packs ship at 96 kHz: `roblox_sample_rate` fails them until they are
resampled to 48 kHz or below.

## probe.luau

Paste through `execute_luau` with the Edit DataModel, replacing the `REQUEST` table with the
shortlist. It builds `AudioPlayer -> AudioAnalyzer` and `AudioPlayer -> AudioFader(Volume 0) ->
AudioDeviceOutput` under `ServerStorage.__audio_probe`, plays each asset silently, samples
`PeakLevel`, `RmsLevel` and `GetSpectrum`, destroys the folder and returns JSON.

Not yet run against a live Studio. All-zero readings mean the probe did not measure, not that the
asset is silent: report that as unmeasured rather than as a result.

## Tests

`python -B tests/test_audio_tools.py` - fixtures are synthesised WAVs, the Store search runs against
a stubbed endpoint, nothing touches the network.
