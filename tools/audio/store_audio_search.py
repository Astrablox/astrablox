#!/usr/bin/env python3
"""Search Roblox Creator Store AUDIO from the shell and get the facts that decide whether a sound is usable.

Use this first, before any local library or any generation: Store audio costs no upload quota,
plays by asset id inside the experience, and the professional catalogues on it are recorded by
sound houses rather than generated.

Usage:
  store_audio_search.py "forest ambience loop" [--sfx|--music] [--min-duration 20] [--max-duration 90]
                        [--publisher pse|apm|distrokid|clippsly|roblox] [--creator-id N]
                        [--limit 50] [--pages 2] [--free] [--verified-only] [--exclude junk,meme] [--json]
  store_audio_search.py --ids 9112789512,1839246711        # details for ids you already have

Returns per asset: id, rbxassetid uri, name, artist, audio type (Music / SoundEffect / Unknown),
duration in seconds, creator and whether the creator is verified, free/paid, votes, created date,
and the publisher description (Pro Sound Effects and APM write the recording, the category and
"Loop" into it - that description is what you select on, since nobody in this studio can listen).

No API key: this is the public toolbox-service endpoint the Studio toolbox uses. Verified live
2026-09-08: category 3 is Audio (`/marketplace/3`, `/marketplace/audio` also resolves); the
filters that actually change the result set are `minDuration`, `maxDuration` (seconds),
`audioTypes=Music|SoundEffect`, `creatorTargetId`, `limit` (100 accepted), `cursor`.
`creatorName` is accepted and ignored - use `--publisher` / `--creator-id`.

One trap, verified: a lot of library ambience carries `audioType: "Unknown"`, not `SoundEffect`.
`--sfx` therefore hides it. Use `--sfx` only to strip songs out of a noisy keyword; never together
with `--publisher pse` when you are looking for ambience.

When NOT to use it: for a sound you intend to gate on disk. Store audio cannot be downloaded -
it streams inside Roblox only, and its licence covers use inside a Roblox experience, not a
trailer or an export. Its objective check is the in-engine probe (tools/audio/probe.luau), not
tools/audio/gate.py.
"""
from __future__ import annotations
import argparse, json, sys, urllib.request, urllib.parse, urllib.error

BASE = "https://apis.roblox.com/toolbox-service/v1"
AUDIO_CATEGORY = 3
UA = {"User-Agent": "astrablox-audio-search/1.0"}

# Creator ids verified live 2026-09-08 by reading `creator.id` off search results.
PUBLISHERS = {
    "pse": (7462895450, "ProSoundEffects - recorded SFX and ambience library, structured descriptions"),
    "apm": (7462718749, "APM Music - production music library"),
    "distrokid": (7135127272, "DistrokidOfficial - songs, dominates generic music keywords"),
    "clippsly": (3470791130, "Clippsly - music"),
    "roblox": (1, "Roblox - platform default sounds"),
}


def _get(url: str) -> dict:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def details(ids: list[str]) -> list[dict]:
    """Item details for up to a page of asset ids. Audio detail fields: duration, audioDetails, description."""
    out = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        det = _get(f"{BASE}/items/details?assetIds={','.join(chunk)}")
        for item in det.get("data", []):
            a = item.get("asset", {}) or {}
            c = item.get("creator", {}) or {}
            v = item.get("voting", {}) or {}
            f = item.get("fiatProduct", {}) or {}
            ad = a.get("audioDetails", {}) or {}
            out.append({
                "id": a.get("id"),
                "uri": f"rbxassetid://{a.get('id')}",
                "name": a.get("name"),
                "artist": ad.get("artist") or "",
                "title": ad.get("title") or "",
                "album": ad.get("musicAlbum") or "",
                "audioType": ad.get("audioType"),
                "tags": ad.get("tags") or [],
                "duration": a.get("duration"),
                "creator": c.get("name"),
                "creator_id": c.get("id"),
                "creator_verified": bool(c.get("isVerifiedCreator")),
                "free": f.get("isFree", True),
                "purchasable": f.get("purchasable"),
                "upVotes": v.get("upVotes"), "downVotes": v.get("downVotes"),
                "created": a.get("createdUtc"), "updated": a.get("updatedUtc"),
                "description": (a.get("description") or "").strip(),
            })
    return out


def search(keyword: str, *, audio_type: str | None = None, min_duration: int | None = None,
           max_duration: int | None = None, creator_id: int | None = None,
           limit: int = 30, pages: int = 1) -> list[dict]:
    ids: list[str] = []
    cursor = None
    for _ in range(max(1, pages)):
        params = {"keyword": keyword, "limit": min(limit, 100)}
        if audio_type:
            params["audioTypes"] = audio_type
        if min_duration is not None:
            params["minDuration"] = min_duration
        if max_duration is not None:
            params["maxDuration"] = max_duration
        if creator_id is not None:
            params["creatorTargetId"] = creator_id
        if cursor:
            params["cursor"] = cursor
        res = _get(f"{BASE}/marketplace/{AUDIO_CATEGORY}?{urllib.parse.urlencode(params)}")
        page = [str(x["id"]) for x in res.get("data", [])]
        ids.extend(page)
        cursor = res.get("nextPageCursor")
        if not page or not cursor:
            break
    seen, uniq = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            uniq.append(i)
    return details(uniq)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("keyword", nargs="?", help="what the sound is, in the words a library would use")
    ap.add_argument("--ids", help="comma-separated asset ids: fetch details instead of searching")
    ap.add_argument("--sfx", action="store_true", help="audioTypes=SoundEffect")
    ap.add_argument("--music", action="store_true", help="audioTypes=Music")
    ap.add_argument("--min-duration", type=int)
    ap.add_argument("--max-duration", type=int)
    ap.add_argument("--publisher", choices=sorted(PUBLISHERS))
    ap.add_argument("--creator-id", type=int)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--free", action="store_true")
    ap.add_argument("--verified-only", action="store_true", help="keep only verified creators")
    ap.add_argument("--exclude", default="", help="comma-separated words; drop rows whose name or description contains one")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.publisher and not a.creator_id:
        a.creator_id = PUBLISHERS[a.publisher][0]
    try:
        if a.ids:
            rows = details([i.strip() for i in a.ids.split(",") if i.strip()])
        elif a.keyword:
            atype = "SoundEffect" if a.sfx else ("Music" if a.music else None)
            rows = search(a.keyword, audio_type=atype, min_duration=a.min_duration,
                          max_duration=a.max_duration, creator_id=a.creator_id,
                          limit=a.limit, pages=a.pages)
        else:
            ap.error("give a keyword or --ids")
            return 2
    except urllib.error.HTTPError as e:
        print(f"toolbox-service HTTP {e.code}: {e.read()[:200].decode('utf8', 'replace')}", file=sys.stderr)
        return 2
    except OSError as e:
        print(f"toolbox-service unreachable: {e}", file=sys.stderr)
        return 2

    if a.free:
        rows = [r for r in rows if r["free"]]
    if a.verified_only:
        rows = [r for r in rows if r["creator_verified"]]
    for word in [w.strip().lower() for w in a.exclude.split(",") if w.strip()]:
        rows = [r for r in rows if word not in (r["name"] or "").lower() and word not in r["description"].lower()]

    if a.json:
        print(json.dumps(rows, indent=1, ensure_ascii=False))
        return 0
    if not rows:
        print("no results")
        if a.sfx or a.music:
            print("hint: audioTypes filters on a field that is often 'Unknown' on library assets - "
                  "run the same query without --sfx/--music before concluding the Store has nothing",
                  file=sys.stderr)
        return 0
    for r in rows:
        flags = ("" if r["free"] else "PAID ") + ("V " if r["creator_verified"] else "")
        first = (r["description"].splitlines() or [""])[0][:70]
        print(f"{r['id']:>16}  {(r['name'] or '')[:40]:40}  {str(r['audioType'])[:11]:11} {str(r['duration']):>5}s  "
              f"{flags}by {(r['creator'] or '')[:18]:18} {first}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
