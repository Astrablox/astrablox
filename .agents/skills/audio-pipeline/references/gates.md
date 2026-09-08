# Reading the gates: what each number means and what it sounds like

`tools/audio/gate.py` on files, `tools/audio/probe.luau` on Creator Store assets. Neither tool
decides whether a sound is the right sound; both decide whether it is broken. The point of this
file is that a number is only useful if you know which defect it stands for.

## The verdicts

`pass` - nothing measured is out of bounds. `warn` - something is out of the ordinary and needs a
decision, not an automatic rejection. `fail` - the file is broken, or a measurement that matters did
not happen. `unmeasured` - no decoder was available; this fails the file, because a sound nobody
gated is not a gated sound. `--strict` makes warnings fail too; use it on generated material, where
warnings are much more likely to be real.

## The measurements, and the defect behind each

**Format, size, duration, sample rate.** Roblox's own limits: `.mp3 .ogg .wav .flac`, ≤ 20 MB,
≤ 7 minutes, ≤ 48 kHz. A studio-grade pack at 96 kHz fails here; resample before uploading, do not
argue with the platform:
`ffmpeg -i in.wav -ar 48000 -ac 2 -c:a pcm_s16le out.wav`

**Clipping** - samples pinned at full scale in a run. This is the sound of distortion and the single
most common reason a sound is described as harsh or unpleasant. A run of a few samples fails the
file; isolated full-scale samples warn. Turning the gain down afterwards does not undo it - the
distortion is already in the file. Find another asset.

**Sample peak.** Reported for headroom, not as a target. A file that peaks at the ceiling has no
room for the ducking and summing that happen later.

**Loudness.** Reported under the name of the metric that produced it - `lufs_i` (pyloudnorm,
ITU-R BS.1770-4), `lufs_i_bs1770_own` (this tool's own implementation of the same standard, needs
numpy and scipy), `rms_dbfs` (plain Python, unweighted, not LUFS). Never compare two numbers
measured under different metrics; the tool refuses to and so should you.

**Set spread and gain.** Pass the whole scene to one call. The `set` block reports the spread across
the files and the gain each one needs to reach the reference. This is the measurement that prevents
the defect players actually complain about: one sound far louder than its neighbours, which reads as
a mistake no matter how good the recording is. Write those gains into the placement package.

**DC offset** - the waveform sits off centre. Every start and stop clicks, and the offset eats
headroom. A large offset fails.

**Share of silence, leading silence, cut tail.** A file that is nearly all silence is an empty
download. Silence before the first sound in a one-shot is latency the player feels as a late hit.
A tail still near peak level in the last moments means the file was cut before the sound ended - the
"strange" sound that stops mid-air.

**Loop seam.** The wrap from the last sample back to the first is compared against the largest step
the waveform takes anywhere on its own. A jump much larger than that is a discontinuity, and a
discontinuity is the click the player hears once every cycle - the fastest way an ambience becomes
unbearable. This is why the comparison is against the waveform and not against a fixed number: a
rain bed jumps a lot from sample to sample, a drone almost not at all.

**Loop padding.** Silence at either end of a looping file becomes a gap in the bed every cycle.

**Spectral balance** - the share of energy below 200 Hz and above 6 kHz, plus the centroid. Very
high-heavy reads as hiss or harshness; very low-heavy reads as rumble or mud. These warn rather than
fail, because a wind bed is legitimately high-heavy and a cave drone legitimately low-heavy - the
question the warning asks is whether the balance matches what the entry said the sound is.

**Channel correlation.** Strongly negative correlation means the two channels cancel when summed;
the sound thins or disappears on a mono emitter or a phone speaker. Positional emitters want mono
material anyway.

## The Store probe

`probe.luau` reports per asset: `ready` (did it load at all), `length`, `peak_dbfs`, `rms_dbfs`,
`quiet_share`, `low_share`, `high_share`, `measured`.

- `ready = false` is the useful failure: a wrong id, an asset that was taken down, or - for anything
  uploaded by this studio - audio whose permission was never granted to the experience.
- `measured = false`, or every reading at zero, means the probe did not measure. Report that as
  unmeasured. Zeros are not evidence of silence.
- The probe's levels are the engine's own decoded stream, which is exactly what the player will
  hear, so the set comparison across Store assets is done on these numbers the same way `gate.py`
  does it for files.

## Setting up the measuring chain on a build machine

`pip install soundfile` gets ogg, flac and mp3 decoding; `numpy` and `scipy` enable the BS.1770
loudness, the spectrum and the correlation; `pyloudnorm` swaps in the reference meter. With none of
them, only PCM WAV is measured and everything else fails as unmeasured. Installing these once is
cheaper than every argument about whether a sound is fine.
