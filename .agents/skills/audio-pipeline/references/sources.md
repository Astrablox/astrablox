# Where sound comes from, and what each source permits

Checked 2026-09-07/08. Anything marked "verified live" was called from this checkout on that date;
everything else carries its source link and date. Prices are not a category here: this studio uses
no paid audio service at all.

**The licence rule that catches people out:** the licence of the code, the site or the repository is
not the licence of the thing you are shipping. A model repository under MIT can carry weights under
a non-commercial licence; a free download site can host assets under four different licences at
once. Read the licence attached to the asset or to the weights, and record it in `provenance.json`
in the words of the licence, not as "free".

## 1. Roblox Creator Store audio - the default source

Reached through `tools/audio/store_audio_search.py`, no API key, no cookie.
Verified live 2026-09-08 against `https://apis.roblox.com/toolbox-service/v1`:

- Audio is category **3**: `GET /marketplace/3?keyword=...&limit=...`. The literal `audio` also
  resolves. Category 9 returns HTTP 400 ("The value '9' is invalid").
- Filters that change the result set: `minDuration`, `maxDuration` in seconds; `audioTypes=Music`
  or `audioTypes=SoundEffect`; `creatorTargetId`; `limit` up to 100; `cursor` for the next page.
  `creatorName` is accepted and ignored.
- `GET /items/details?assetIds=a,b,c` returns per asset: `duration` (seconds), `audioDetails`
  (`artist`, `title`, `musicAlbum`, `audioType`, `tags`), the publisher's `description`, `creator`
  with `isVerifiedCreator`, `fiatProduct.isFree`, votes and dates.
- Publisher ids read off live results: **ProSoundEffects 7462895450** (recorded SFX and ambience,
  structured descriptions: what was recorded, where, whether it loops), **APMOfficial 7462718749**
  (production music), **DistrokidOfficial 7135127272** (songs; dominates generic music keywords),
  **Clippsly 3470791130**, **Roblox 1**.
- Trap: much library ambience carries `audioType: "Unknown"`, so `audioTypes=SoundEffect` hides it.
- The match is lexical over title and description, not semantic: "wind through pine trees" returns a
  ship's wake, while the words a library itself uses - "Forest Ambience", "Armor Clink", "Footsteps
  Gravel" - land on the right shelf. Try several phrasings of the same entry, and expect a narrowed
  publisher query to rank within that publisher only, so an off-target result there means the words
  were wrong rather than that the catalogue is empty.

Licence and mechanics:

- Store audio is licensed for use **inside Roblox experiences** and streams there; it cannot be
  downloaded, exported, or used in a trailer outside the platform (Roblox staff answer, sound
  library rules: https://devforum.roblox.com/t/4266598).
- Too Lost joined the Store music library in July 2026 with thousands of rights-cleared tracks
  (https://devforum.roblox.com/t/4760221). Store music has been removed from under creators before
  (https://devforum.roblox.com/t/4559449), so record the id and check it still loads on every build.
- Cost to this studio: none, and no upload quota. An asset is used by id
  (`rbxassetid://<id>`); nothing is inserted or copied.
- Because it never lands on disk, `gate.py` cannot see it. Its objective check is
  `tools/audio/probe.luau` in Studio: loaded, length, peak, rms, spectrum.

## 2. Uploading anything else: the budget and the privacy rule

Facts from Roblox documentation (create.roblox.com/docs/audio/assets and
create.roblox.com/docs/cloud/guides/usage-assets, read 2026-09-08):

- Accepted: `.mp3`, `.ogg`, `.wav`, `.flac`; **≤ 20 MB**, **≤ 7 minutes**, sample rate **≤ 48 kHz**,
  mono or stereo 2.0 / 3.0 / 5.1.
- Through Studio and the Creator Hub: **2,000 audio assets per 30 days** for an ID-verified creator,
  100 without verification.
- Through the Open Cloud Assets API - the only channel an agent can drive unattended - **100 uploads
  a month** for an ID-verified user, 10 without. Audio cannot be updated, only uploaded again.
- Uploaded audio is **private by default**: it plays only where its owner granted permission, so an
  uploaded sound needs the experience granted before it will play there. A silent sound in Studio is
  usually this, not a broken file.

That budget is the reason the Store comes first. Every file taken from a pack or generated spends a
slot; a Store asset spends none.

The upload itself: `python tools/assets/upload.py --file <path> --name "<name>" --type Audio`
(Open Cloud, needs `ROBLOX_API_KEY` with the assets write scope and a creator id in the environment).
It carries `.wav`, `.ogg` and `.mp3` - not `.flac`, so convert before uploading. Moderation takes
time, so the id it returns may not play immediately, and the asset is private until the experience is
granted permission. Record the id, the date and the permission state in `provenance.json`.

## 3. Open packs on disk

| Source | What it is | Licence | How to get it | Watch out |
|---|---|---|---|---|
| **Sonniss GDC Game Audio Bundle** (https://gdc.sonniss.com/) | Annual free bundle from Sonniss vendors; the 2026 edition is 7.47 GB, 347 files, WAV (2026-03-12) | Royalty free, no attribution, unlimited projects, commercial use stated on the page | Direct download per vendor archive; unpack once into `assets/library/audio/` and catalogue | Studio-grade material is often 96 kHz or 24-bit: resample to ≤ 48 kHz or the Roblox limit fails it. Files are long compilations - cut the take you need |
| **Kenney audio** (https://kenney.nl/assets) | Interface, impact, digital and RPG sets made for games | CC0 | Direct zip per pack | Stylised and small-scale; right for interface, wrong for a forest |
| **OpenGameArt** (https://opengameart.org/) | Community uploads, still active in 2026 | Mixed: CC0, CC-BY, CC-BY-SA, GPL - per asset | Web pages, no API | Only take CC0 unless you are prepared to carry attribution text into the game's credits; record the licence exactly |
| **Freesound** (https://freesound.org/docs/api/) | Large community library with a CC0 filter and content-based search | Per sound: CC0, CC-BY, CC-BY-NC (exclude NC) | APIv2 needs a free token in a request parameter; **downloading the original file needs OAuth2**, which needs a browser and a person | Optional for this studio: without OAuth2 only lossy previews are reachable. Use only if a token exists in the environment; never block a scene on it |
| **Pixabay / Mixkit** | Site-licensed music and effects | Own site licences: no attribution, but resale and standalone distribution restricted | Direct download | Read the site licence before use; they are not CC0 |

Not used here: any service that charges, anything under a non-commercial licence, and ZapSplat-style
libraries whose attribution terms and copyright-claim history (a false Content ID claim reported at
https://devforum.roblox.com/t/4292606) make them a liability.

## 4. Local generation

Open weights only, and only with a licence that permits commercial use of the output. Details, model
list, install and prompting: `references/local-generation.md`. It is the third source, not the first,
for two reasons: it spends upload budget like any file, and it is the only source where nothing
except our own gates stands between a bad result and the player.

## 5. What goes into provenance.json

```
name, role, source ("roblox-store" | "pack:<pack name>" | "generated:<model>"),
source_ref (asset id, or pack file path, or prompt + seed + model version),
licence (the words of the licence and what it permits, including whether the sound may leave Roblox),
duration_s, loudness {metric, value}, gates (the gate.py or probe.luau result),
beat ([{id, why}] - the candidates this one won against),
state (source | rendered | accepted | ... , from the contract's ladder),
roblox_asset_id (once uploaded, plus the date, so the upload budget can be counted)
```
