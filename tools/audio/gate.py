#!/usr/bin/env python3
"""Objective gate for audio files on disk: does this sound break the rules a listener would hear as wrong?

Run it on every WAV / OGG / MP3 / FLAC before the sound enters the catalogue. It measures what can
be measured - format against Roblox's own limits, duration, loudness, peak, clipping, DC offset,
silence, tail, loop seam, spectral balance, channel correlation - and fails the file when a measured
value is one of the defects that reach the player as "unpleasant" or "strange": clipped, cut off,
mostly silence, clicking at the loop point, out of level with the rest of its set, hissing or rumbling.

Usage:
  gate.py FILE [FILE ...] [--role ambience|loop|oneshot|impact|footstep|ui|music|stinger]
          [--loop] [--target-lufs -20] [--silence-floor -60] [--strict] [--allow-unmeasured] [--json]

Exit code: 0 every file passed, 1 any file failed (with --strict a warning also fails),
2 the tool could not run (bad arguments, unreadable file).

Give the whole set of one scene in one call: the `set` block then reports the loudness spread
across the files and the gain each one needs to sit level with the rest, which is the single
measurement that stops a mix from jumping.

What it cannot do: tell you whether the sound is the right sound. Nothing here judges whether a
"stone door" recording is a stone door - that is the source description and the placement.
It also cannot touch Creator Store audio, which never lands on disk: for a Store asset the
objective check is tools/audio/probe.luau inside Studio.

Decoding, in order, whichever is available: `soundfile` (pip install soundfile - covers wav, ogg,
flac, mp3), `ffmpeg` on PATH, the standard library `wave` module (PCM WAV only). If none of them
can decode the file, the format and duration checks still run from the container header and every
level check is reported "unmeasured" - which fails the file unless you pass --allow-unmeasured,
because an ungated sound is not a gated sound.

Loudness metric, honestly named in the output: `lufs_i` when `pyloudnorm` is installed (ITU-R
BS.1770-4), `lufs_i_bs1770_own` when numpy and scipy are here (same standard, this file's own
K-weighting and gating), `rms_dbfs` when only plain Python is available (unweighted, not LUFS).
"""
from __future__ import annotations

import argparse, array, json, math, os, struct, subprocess, sys, wave

# --- optional dependencies, each one honestly reported in the output -------------------------
try:
    import numpy as _np
except Exception:
    _np = None
try:
    from scipy import signal as _sig
except Exception:
    _sig = None
try:
    import soundfile as _sf
except Exception:
    _sf = None
try:
    import pyloudnorm as _pln
except Exception:
    _pln = None

if os.environ.get("AUDIO_GATE_NO_NUMPY"):  # used by the tests to exercise the plain-Python path
    _np = _sig = _sf = _pln = None

ROBLOX_MAX_SECONDS = 7 * 60
ROBLOX_MAX_BYTES = 20 * 1024 * 1024
ROBLOX_MAX_RATE = 48000
ROBLOX_FORMATS = {".wav", ".ogg", ".mp3", ".flac"}

ROLES = ("ambience", "loop", "oneshot", "impact", "footstep", "ui", "music", "stinger")
LOOPING_ROLES = {"ambience", "loop", "music"}
ONESHOT_ROLES = {"oneshot", "impact", "footstep", "ui", "stinger"}


# --------------------------------------------------------------------------- container headers
def _header_facts(path: str) -> dict:
    """Container, sample rate, channels and duration read from the file header, without decoding."""
    ext = os.path.splitext(path)[1].lower()
    size = os.path.getsize(path)
    out = {"container": ext.lstrip("."), "bytes": size, "sample_rate": None, "channels": None,
           "bit_depth": None, "duration_s": None, "codec": None}
    with open(path, "rb") as fh:
        head = fh.read(64)
        if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
            fh.seek(12)
            data_bytes = 0
            while True:
                hdr = fh.read(8)
                if len(hdr) < 8:
                    break
                cid, clen = struct.unpack("<4sI", hdr)
                body = fh.read(clen + (clen & 1))
                if cid == b"fmt " and clen >= 16:
                    fmt, ch, rate, _br, _ba, bits = struct.unpack("<HHIIHH", body[:16])
                    out.update(sample_rate=rate, channels=ch, bit_depth=bits,
                               codec={1: "pcm", 3: "float", 0xFFFE: "extensible"}.get(fmt, f"fmt{fmt}"))
                elif cid == b"data":
                    data_bytes = clen
            if out["sample_rate"] and out["channels"] and out["bit_depth"]:
                per = out["channels"] * max(1, out["bit_depth"] // 8)
                out["duration_s"] = round(data_bytes / (out["sample_rate"] * per), 4)
        elif head[:4] == b"OggS":
            out.update(_ogg_facts(path))
        elif head[:4] == b"fLaC":
            info = head[8:26]
            if len(info) >= 18:
                bits = int.from_bytes(info[10:14], "big")
                rate = bits >> 12
                ch = ((bits >> 9) & 0x7) + 1
                depth = ((bits >> 4) & 0x1F) + 1
                total = int.from_bytes(info[13:18], "big") & ((1 << 36) - 1)
                out.update(sample_rate=rate, channels=ch, bit_depth=depth, codec="flac",
                           duration_s=round(total / rate, 4) if rate else None)
        elif head[:3] == b"ID3" or (head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
            out.update(_mp3_facts(path))
    return out


def _ogg_facts(path: str) -> dict:
    """Sample rate from the identification header, duration from the last page's granule position."""
    facts = {"codec": None, "sample_rate": None, "channels": None, "duration_s": None}
    with open(path, "rb") as fh:
        blob = fh.read(4096)
        if b"vorbis" in blob:
            i = blob.find(b"\x01vorbis")
            if i >= 0:
                ch = blob[i + 11]
                rate = struct.unpack("<I", blob[i + 12:i + 16])[0]
                facts.update(codec="vorbis", channels=ch, sample_rate=rate)
        elif b"OpusHead" in blob:
            i = blob.find(b"OpusHead")
            facts.update(codec="opus", channels=blob[i + 9],
                         sample_rate=48000)  # Opus granule positions are always at 48 kHz
        fh.seek(0, os.SEEK_END)
        end = fh.tell()
        fh.seek(max(0, end - 65536))
        tail = fh.read()
        j = tail.rfind(b"OggS")
        if j >= 0 and facts["sample_rate"]:
            granule = struct.unpack("<q", tail[j + 6:j + 14])[0]
            if granule > 0:
                facts["duration_s"] = round(granule / facts["sample_rate"], 4)
    return facts


_MP3_RATES = {3: [44100, 48000, 32000], 2: [22050, 24000, 16000], 0: [11025, 12000, 8000]}
_MP3_BITRATES_V1L3 = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]


def _mp3_facts(path: str) -> dict:
    """First valid frame header gives rate and channels; Xing/Info frame count gives duration, else CBR estimate."""
    facts = {"codec": "mp3", "sample_rate": None, "channels": None, "duration_s": None}
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        blob = fh.read(200000)
    off = 0
    if blob[:3] == b"ID3":
        sz = blob[6:10]
        off = 10 + ((sz[0] & 0x7F) << 21 | (sz[1] & 0x7F) << 14 | (sz[2] & 0x7F) << 7 | (sz[3] & 0x7F))
    for i in range(off, min(len(blob) - 4, off + 100000)):
        if blob[i] == 0xFF and (blob[i + 1] & 0xE0) == 0xE0:
            ver = (blob[i + 1] >> 3) & 0x3
            rate_i = (blob[i + 2] >> 2) & 0x3
            bitrate_i = (blob[i + 2] >> 4) & 0xF
            mode = (blob[i + 3] >> 6) & 0x3
            if ver not in _MP3_RATES or rate_i == 3 or bitrate_i in (0, 15):
                continue
            rate = _MP3_RATES[ver][rate_i]
            facts.update(sample_rate=rate, channels=1 if mode == 3 else 2)
            frames = None
            window = blob[i:i + 1600]
            for tag in (b"Xing", b"Info"):
                k = window.find(tag)
                if k >= 0 and len(window) >= k + 12:
                    flags = struct.unpack(">I", window[k + 4:k + 8])[0]
                    if flags & 1:
                        frames = struct.unpack(">I", window[k + 8:k + 12])[0]
            spf = 1152 if ver == 3 else 576
            if frames:
                facts["duration_s"] = round(frames * spf / rate, 4)
            else:
                kbps = _MP3_BITRATES_V1L3[bitrate_i] if ver == 3 else _MP3_BITRATES_V1L3[bitrate_i] // 2
                if kbps:
                    facts["duration_s"] = round((size - off) * 8 / (kbps * 1000), 4)
            break
    return facts


# ------------------------------------------------------------------------------------ decoding
def _decode(path: str):
    """Return (samples, rate, decoder). samples: list of per-channel sequences (numpy arrays or array('f'))."""
    ext = os.path.splitext(path)[1].lower()
    if _sf is not None:
        try:
            data, rate = _sf.read(path, always_2d=True, dtype="float32")
            return [data[:, c] for c in range(data.shape[1])], rate, "soundfile"
        except Exception:
            pass
    if ext == ".wav":
        try:
            return _decode_wave(path)
        except Exception:
            pass
    dec = _decode_ffmpeg(path)
    if dec:
        return dec
    if ext == ".wav":
        raise ValueError("WAV could not be decoded")
    return None, None, None


def _decode_wave(path: str):
    with wave.open(path, "rb") as w:
        ch, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(frames)
    if width == 1:
        vals = [(b - 128) / 128.0 for b in raw]
    elif width == 2:
        a = array.array("h")
        a.frombytes(raw[:len(raw) - len(raw) % 2])
        vals = [v / 32768.0 for v in a]
    elif width == 3:
        vals = []
        for i in range(0, len(raw) - 2, 3):
            v = int.from_bytes(raw[i:i + 3], "little", signed=True)
            vals.append(v / 8388608.0)
    elif width == 4:
        a = array.array("i")
        a.frombytes(raw[:len(raw) - len(raw) % 4])
        vals = [v / 2147483648.0 for v in a]
    else:
        raise ValueError(f"unsupported sample width {width}")
    if _np is not None:
        arr = _np.asarray(vals, dtype=_np.float32).reshape(-1, ch) if ch > 1 else _np.asarray(vals, dtype=_np.float32).reshape(-1, 1)
        return [arr[:, c] for c in range(ch)], rate, "stdlib-wave"
    chans = [array.array("f", vals[c::ch]) for c in range(ch)]
    return chans, rate, "stdlib-wave"


def _decode_ffmpeg(path: str):
    exe = None
    for cand in ("ffmpeg", "ffmpeg.exe"):
        try:
            subprocess.run([cand, "-version"], capture_output=True, timeout=10)
            exe = cand
            break
        except Exception:
            continue
    if exe is None:
        return None
    try:
        probe = subprocess.run([exe, "-v", "error", "-i", path, "-f", "f32le", "-"],
                               capture_output=True, timeout=300)
        if probe.returncode != 0 or not probe.stdout:
            return None
        rate = _header_facts(path).get("sample_rate") or 44100
        ch = _header_facts(path).get("channels") or 1
        buf = array.array("f")
        buf.frombytes(probe.stdout[:len(probe.stdout) - len(probe.stdout) % 4])
        if _np is not None:
            arr = _np.frombuffer(bytes(buf), dtype=_np.float32)
            n = (len(arr) // ch) * ch
            arr = arr[:n].reshape(-1, ch)
            return [arr[:, c] for c in range(ch)], rate, "ffmpeg"
        return [array.array("f", buf[c::ch]) for c in range(ch)], rate, "ffmpeg"
    except Exception:
        return None


# ----------------------------------------------------------------------------------- measuring
def _db(x: float) -> float:
    return round(20.0 * math.log10(max(x, 1e-12)), 2)


def _mono(chans):
    if _np is not None:
        return sum(chans) / len(chans)
    n = min(len(c) for c in chans)
    return array.array("f", [sum(c[i] for c in chans) / len(chans) for i in range(n)])


def _rms(seq) -> float:
    if _np is not None:
        return float(_np.sqrt(_np.mean(_np.square(seq)))) if len(seq) else 0.0
    if not len(seq):
        return 0.0
    return math.sqrt(sum(v * v for v in seq) / len(seq))


def _peak(seq) -> float:
    if _np is not None:
        return float(_np.max(_np.abs(seq))) if len(seq) else 0.0
    return max((abs(v) for v in seq), default=0.0)


def _frame_rms(mono, rate: int, win: float = 0.05):
    step = max(1, int(rate * win))
    if _np is not None:
        n = (len(mono) // step) * step
        if n == 0:
            return []
        blocks = _np.asarray(mono[:n]).reshape(-1, step)
        return list(_np.sqrt(_np.mean(_np.square(blocks), axis=1)))
    return [_rms(mono[i:i + step]) for i in range(0, len(mono) - step + 1, step)]


def _kweight_lufs(chans, rate: int):
    """ITU-R BS.1770-4 integrated loudness, own implementation. Needs numpy and scipy."""
    if _np is None or _sig is None:
        return None
    def shelf(fs):
        f0, G, Q = 1681.974450955533, 3.999843853973347, 0.7071752369554196
        K = math.tan(math.pi * f0 / fs)
        Vh = 10 ** (G / 20.0); Vb = Vh ** 0.4996667741545416
        a0 = 1.0 + K / Q + K * K
        return ([(Vh + Vb * K / Q + K * K) / a0, 2.0 * (K * K - Vh) / a0, (Vh - Vb * K / Q + K * K) / a0],
                [1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    def hpf(fs):
        f0, Q = 38.13547087602444, 0.5003270373238773
        K = math.tan(math.pi * f0 / fs)
        a0 = 1.0 + K / Q + K * K
        return ([1.0, -2.0, 1.0], [1.0, 2.0 * (K * K - 1.0) / a0, (1.0 - K / Q + K * K) / a0])
    b1, a1 = shelf(rate); b2, a2 = hpf(rate)
    block = int(0.400 * rate)
    if block <= 0 or min(len(c) for c in chans) < block:
        return None
    hop = block // 4
    weights = [1.0, 1.0, 1.0, 1.41, 1.41]
    per_block = None
    for i, ch in enumerate(chans):
        y = _sig.lfilter(b1, a1, _np.asarray(ch, dtype=_np.float64))
        y = _sig.lfilter(b2, a2, y)
        n_blocks = 1 + (len(y) - block) // hop
        idx = _np.arange(block)[None, :] + hop * _np.arange(n_blocks)[:, None]
        ms = _np.mean(_np.square(y[idx]), axis=1)
        w = weights[i] if i < len(weights) else 1.0
        per_block = w * ms if per_block is None else per_block + w * ms
    with _np.errstate(divide="ignore"):
        l_block = -0.691 + 10.0 * _np.log10(_np.maximum(per_block, 1e-20))
    keep = per_block[l_block > -70.0]
    if keep.size == 0:
        return None
    rel = -0.691 + 10.0 * math.log10(float(_np.mean(keep))) - 10.0
    keep2 = per_block[(l_block > -70.0) & (l_block > rel)]
    if keep2.size == 0:
        return None
    return round(-0.691 + 10.0 * math.log10(float(_np.mean(keep2))), 2)


def _loudness(chans, rate: int):
    if _pln is not None and _np is not None:
        try:
            data = _np.stack([_np.asarray(c, dtype=_np.float64) for c in chans], axis=-1)
            meter = _pln.Meter(rate)
            return round(float(meter.integrated_loudness(data)), 2), "lufs_i"
        except Exception:
            pass
    own = _kweight_lufs(chans, rate)
    if own is not None:
        return own, "lufs_i_bs1770_own"
    return _db(_rms(_mono(chans))), "rms_dbfs"


def _clipping(chans):
    thresh = 0.999
    total = at = longest = 0
    for ch in chans:
        run = 0
        if _np is not None:
            flags = _np.abs(_np.asarray(ch)) >= thresh
            at += int(flags.sum()); total += len(flags)
            if flags.any():
                idx = _np.flatnonzero(_np.diff(_np.concatenate(([0], flags.view(_np.int8), [0]))))
                runs = idx[1::2] - idx[0::2]
                longest = max(longest, int(runs.max()))
        else:
            total += len(ch)
            for v in ch:
                if abs(v) >= thresh:
                    run += 1; at += 1
                    longest = max(longest, run)
                else:
                    run = 0
    return {"full_scale_samples": at, "share": round(at / total, 6) if total else 0.0, "longest_run": longest}


def _spectrum(mono, rate: int):
    if _np is None or len(mono) < 2048:
        return None
    x = _np.asarray(mono, dtype=_np.float64)
    n = min(len(x), rate * 30)
    x = x[:n]
    win = _np.hanning(len(x))
    mag = _np.abs(_np.fft.rfft(x * win))
    freqs = _np.fft.rfftfreq(len(x), 1.0 / rate)
    energy = mag ** 2
    total = float(energy.sum()) or 1.0
    low = float(energy[freqs < 200].sum()) / total
    high = float(energy[freqs > 6000].sum()) / total
    centroid = float((freqs * energy).sum() / total)
    return {"centroid_hz": round(centroid, 1), "low_share": round(low, 3),
            "mid_share": round(1.0 - low - high, 3), "high_share": round(high, 3)}


def _step_yardstick(mono) -> float:
    """The largest step this waveform takes between neighbouring samples anywhere (99.9th percentile).

    A loop wrap that jumps further than the signal ever jumps on its own is a discontinuity, and a
    discontinuity is the click. Comparing against the waveform itself is what makes the check work
    on a quiet drone and on a rain bed alike."""
    if _np is not None:
        d = _np.abs(_np.diff(_np.asarray(mono, dtype=_np.float64)))
        return float(_np.percentile(d, 99.9)) if d.size else 0.0
    n = len(mono)
    if n < 2:
        return 0.0
    stride = max(1, n // 40000)
    d = sorted(abs(mono[i + 1] - mono[i]) for i in range(0, n - 1, stride))
    return d[min(len(d) - 1, int(len(d) * 0.999))] if d else 0.0


def _correlation(chans):
    if len(chans) < 2 or _np is None:
        return None
    a = _np.asarray(chans[0], dtype=_np.float64); b = _np.asarray(chans[1], dtype=_np.float64)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    da, db = a - a.mean(), b - b.mean()
    den = math.sqrt(float((da ** 2).sum()) * float((db ** 2).sum()))
    return round(float((da * db).sum()) / den, 3) if den else None


# -------------------------------------------------------------------------------------- checks
def _add(checks, name, status, detail):
    checks.append({"name": name, "status": status, "detail": detail})


def measure(path: str, role: str | None, loop: bool, silence_floor: float) -> dict:
    facts = _header_facts(path)
    ext = os.path.splitext(path)[1].lower()
    res = {"file": os.path.abspath(path), "role": role, "loop": loop, "format": facts,
           "decoder": None, "duration_s": facts.get("duration_s"), "checks": []}
    checks = res["checks"]

    _add(checks, "roblox_format", "pass" if ext in ROBLOX_FORMATS else "fail",
         f"{ext or 'no extension'}; Roblox accepts .mp3 .ogg .wav .flac")
    _add(checks, "roblox_size", "pass" if facts["bytes"] <= ROBLOX_MAX_BYTES else "fail",
         f"{facts['bytes'] / 1048576:.2f} MB; limit 20 MB per upload")
    if facts.get("sample_rate"):
        _add(checks, "roblox_sample_rate", "pass" if facts["sample_rate"] <= ROBLOX_MAX_RATE else "fail",
             f"{facts['sample_rate']} Hz; limit 48000 Hz")
    if facts.get("channels"):
        st = "pass" if facts["channels"] <= 2 else "warn"
        _add(checks, "channels", st, f"{facts['channels']}; a positional emitter wants mono, a bed stereo")

    try:
        chans, rate, decoder = _decode(path)
    except Exception as e:
        chans, rate, decoder = None, None, None
        _add(checks, "decode", "fail", f"{type(e).__name__}: {e}")
    res["decoder"] = decoder

    if not chans:
        res["duration_s"] = facts.get("duration_s")
        if res["duration_s"] is not None:
            _add(checks, "roblox_duration", "pass" if res["duration_s"] <= ROBLOX_MAX_SECONDS else "fail",
                 f"{res['duration_s']} s from the header; limit 420 s")
        _add(checks, "levels", "unmeasured",
             "no decoder for this file: install soundfile or put ffmpeg on PATH; "
             "level, clipping, silence and loop checks did not run")
        return res

    rate = rate or facts.get("sample_rate") or 44100
    mono = _mono(chans)
    duration = len(mono) / rate
    res["duration_s"] = round(duration, 4)
    res["format"]["sample_rate"] = res["format"].get("sample_rate") or rate
    res["format"]["channels"] = res["format"].get("channels") or len(chans)
    _add(checks, "roblox_duration", "pass" if duration <= ROBLOX_MAX_SECONDS else "fail",
         f"{duration:.2f} s; limit 420 s")

    peak = _peak(mono)
    res["peak_dbfs"] = _db(peak)
    clip = _clipping(chans)
    res["clipping"] = clip
    value, metric = _loudness(chans, rate)
    res["loudness"] = {"metric": metric, "value": value}
    dc = [round(float(sum(c) / len(c)) if _np is None else float(_np.mean(c)), 6) for c in chans]
    res["dc_offset"] = max(abs(v) for v in dc)

    frames = _frame_rms(mono, rate)
    floor_lin = 10 ** (silence_floor / 20.0)
    quiet = [f < floor_lin for f in frames]
    lead = 0
    for q in quiet:
        if q: lead += 1
        else: break
    trail = 0
    for q in reversed(quiet):
        if q: trail += 1
        else: break
    win = 0.05
    res["silence"] = {"floor_dbfs": silence_floor, "leading_s": round(lead * win, 3),
                      "trailing_s": round(trail * win, 3),
                      "share": round(sum(quiet) / len(quiet), 3) if quiet else 1.0}
    tail_n = max(1, int(0.05 * rate))
    tail_rms = _rms(mono[-tail_n:])
    res["tail"] = {"end_rms_dbfs": _db(tail_rms), "peak_dbfs": res["peak_dbfs"]}
    res["spectrum"] = _spectrum(mono, rate)
    res["channel_correlation"] = _correlation(chans)

    if loop:
        first, last = float(mono[0]), float(mono[-1])
        head = _rms(mono[:tail_n]); tailr = _rms(mono[-tail_n:])
        step = abs(last - first)
        typical = _step_yardstick(mono)
        res["loop_seam"] = {"step_dbfs": _db(step),
                            "seam_over_waveform_db": round(_db(step) - _db(typical), 2) if typical else None,
                            "head_tail_delta_db": round(_db(head) - _db(tailr), 2)}

    # --- verdicts -----------------------------------------------------------------------------
    _add(checks, "clipping", "fail" if clip["longest_run"] >= 4 else ("warn" if clip["full_scale_samples"] else "pass"),
         f"{clip['full_scale_samples']} samples at full scale, longest run {clip['longest_run']}")
    _add(checks, "peak", "warn" if res["peak_dbfs"] > -0.3 else "pass",
         f"sample peak {res['peak_dbfs']} dBFS")
    _add(checks, "dc_offset", "fail" if res["dc_offset"] > 0.01 else ("warn" if res["dc_offset"] > 0.003 else "pass"),
         f"mean offset {res['dc_offset']}; an offset clicks on every start and stop")
    _add(checks, "not_silence", "fail" if res["silence"]["share"] > 0.95 else "pass",
         f"{res['silence']['share'] * 100:.0f}% of the file is below {silence_floor} dBFS")

    if role in ONESHOT_ROLES:
        _add(checks, "trigger_latency", "warn" if res["silence"]["leading_s"] > 0.05 else "pass",
             f"{res['silence']['leading_s']} s of silence before the sound starts; a one-shot fires late by that much")
        cut = res["tail"]["end_rms_dbfs"] > res["peak_dbfs"] - 12
        _add(checks, "tail_cut", "warn" if cut else "pass",
             f"last 50 ms at {res['tail']['end_rms_dbfs']} dBFS against a peak of {res['peak_dbfs']}; "
             "a tail this loud means the file was cut before the sound ended")
    if role in LOOPING_ROLES or loop:
        _add(checks, "loop_padding", "warn" if res["silence"]["trailing_s"] > 0.15 or res["silence"]["leading_s"] > 0.15 else "pass",
             f"silence at the ends: {res['silence']['leading_s']} s / {res['silence']['trailing_s']} s - "
             "a loop with padding breathes a gap every cycle")
    if loop and "loop_seam" in res:
        over = res["loop_seam"]["seam_over_waveform_db"]
        if over is None:
            _add(checks, "loop_seam", "unmeasured", "the file is too short to compare the wrap against its own waveform")
        else:
            _add(checks, "loop_seam", "fail" if over > 16 else ("warn" if over > 6 else "pass"),
                 f"the jump from the last sample back to the first is {over} dB above the largest step this waveform "
                 f"takes on its own "
                 f"({res['loop_seam']['step_dbfs']} dBFS absolute); this is the click heard once every cycle")
        _add(checks, "loop_balance", "warn" if abs(res["loop_seam"]["head_tail_delta_db"]) > 6 else "pass",
             f"head against tail {res['loop_seam']['head_tail_delta_db']} dB")
    if res["spectrum"]:
        sp = res["spectrum"]
        _add(checks, "spectral_balance",
             "warn" if sp["high_share"] > 0.5 or sp["low_share"] > 0.85 else "pass",
             f"centroid {sp['centroid_hz']} Hz, low {sp['low_share']}, mid {sp['mid_share']}, high {sp['high_share']}; "
             "high-heavy reads as hiss or harshness, low-heavy as rumble")
    if res["channel_correlation"] is not None:
        _add(checks, "channel_phase", "warn" if res["channel_correlation"] < -0.2 else "pass",
             f"L/R correlation {res['channel_correlation']}; negative means the sound thins or vanishes when summed to mono")
    return res


def verdict(result: dict, strict: bool, allow_unmeasured: bool) -> str:
    states = [c["status"] for c in result["checks"]]
    if "fail" in states:
        return "fail"
    if "unmeasured" in states and not allow_unmeasured:
        return "fail"
    if strict and "warn" in states:
        return "fail"
    return "pass"


def set_report(results: list[dict], target: float | None) -> dict | None:
    vals = [(r["file"], r["loudness"]["value"], r["loudness"]["metric"]) for r in results if r.get("loudness")]
    if not vals:
        return None
    counts = {}
    for _, _, m in vals:
        counts[m] = counts.get(m, 0) + 1
    metric = max(counts, key=counts.get)
    same = [(f, v) for f, v, m in vals if m == metric]
    other = [f for f, _, m in vals if m != metric]
    levels = [v for _, v in same]
    ref = target if target is not None else round(sorted(levels)[len(levels) // 2], 2)
    return {
        "metric": metric,
        "reference": ref, "reference_source": "target" if target is not None else "median of this set",
        "spread_db": round(max(levels) - min(levels), 2),
        "measured_on_a_different_metric": other,
        "files": [{"file": f, "level": v, "gain_db": round(ref - v, 2)} for f, v in same],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--role", choices=ROLES)
    ap.add_argument("--loop", action="store_true", help="the file will be looped: check the seam and the padding")
    ap.add_argument("--target-lufs", type=float, help="reference level for the gain suggestion of the set")
    ap.add_argument("--silence-floor", type=float, default=-60.0)
    ap.add_argument("--strict", action="store_true", help="a warning fails the file too")
    ap.add_argument("--allow-unmeasured", action="store_true",
                    help="pass a file whose levels could not be measured; say so in the report if you use it")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    results, failed = [], False
    for path in a.files:
        if not os.path.isfile(path):
            print(f"gate: no such file: {path}", file=sys.stderr)
            return 2
        r = measure(path, a.role, a.loop or (a.role in LOOPING_ROLES if a.role else False), a.silence_floor)
        r["verdict"] = verdict(r, a.strict, a.allow_unmeasured)
        failed = failed or r["verdict"] == "fail"
        results.append(r)

    report = {"results": results, "set": set_report(results, a.target_lufs) if len(results) > 1 else None,
              "tools": {"numpy": _np is not None, "scipy": _sig is not None,
                        "soundfile": _sf is not None, "pyloudnorm": _pln is not None}}
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        for r in results:
            loud = r.get("loudness") or {}
            print(f"{r['verdict'].upper():4} {os.path.basename(r['file'])}  "
                  f"{r.get('duration_s')}s  {loud.get('metric', 'unmeasured')}={loud.get('value', '?')}  "
                  f"peak={r.get('peak_dbfs', '?')}  decoder={r['decoder']}")
            for c in r["checks"]:
                if c["status"] != "pass":
                    print(f"     {c['status']:10} {c['name']}: {c['detail']}")
        s = report["set"]
        if s:
            print(f"set: {s['metric']} spread {s['spread_db']} dB against {s['reference']} ({s['reference_source']})")
            for f in s["files"]:
                print(f"     gain {f['gain_db']:+.2f} dB  {os.path.basename(f['file'])}")
            for f in s["measured_on_a_different_metric"]:
                print(f"     not comparable (different metric)  {os.path.basename(f)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
