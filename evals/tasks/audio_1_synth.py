"""Procedural audio: synthesize a 20 s ambient track to a musical spec with numpy."""
import numpy as np
import _media

AREA = "blender_media"
TITLE = "Audio synth: 20 s, A minor progression (key checked), kick/hats, levels + fades"
KIND = "agent"
TIMEOUT = 1500

PROMPT = """Write Scripts/synth.py (python3 + numpy; you may use scipy/soundfile only if importable) that
renders a 20-second electronic ambient track to audio/ambient.wav:
- 48 kHz, 16-bit, stereo; exactly 20.0 seconds long;
- tempo 90 BPM in 4/4, key of A minor: a soft pad playing Am - F - C - G (one chord per bar, repeating),
  a kick drum on every beat and a closed hi-hat on every off-beat (eighth notes between beats);
- 2-second fade-in at the start and 2-second fade-out at the end;
- peak level between -3 dBFS and -1 dBFS.
Run it with python3 and verify duration, sample rate and peak level yourself."""


def setup(ws):
    (ws / "Scripts").mkdir()
    (ws / "audio").mkdir()


def grade(ws):
    wav = ws / "audio/ambient.wav"
    if not wav.exists():
        return {"score": 0.0, "passed": False, "notes": "no audio/ambient.wav"}
    try:
        a, rate = _media.read_wav(wav)
    except Exception as e:
        return {"score": 0.05, "passed": False, "notes": f"unreadable wav: {e}"}
    import wave
    with wave.open(str(wav)) as w:
        sampwidth = w.getsampwidth()
    mono = a.mean(axis=1)
    dur = len(mono) / rate
    peak = float(np.abs(a).max()) if a.size else 0.0
    peak_db = 20 * np.log10(peak) if peak > 0 else -99
    checks = {"format": rate == 48000 and a.shape[1] == 2 and sampwidth == 2, "duration": abs(dur - 20.0) < 0.05,
              "peak": -3.2 <= peak_db <= -0.9}

    def rms(t0, t1):
        s = mono[int(t0 * rate):int(t1 * rate)]
        return float(np.sqrt((s ** 2).mean())) if s.size else 0.0
    mid = rms(8, 12)
    checks["fades"] = mid > 0 and rms(0, 0.3) < 0.3 * mid and rms(dur - 0.3, dur) < 0.3 * mid
    # No tempo check: onset-based tempo tests misjudged correct 90 BPM tracks (nested 60/90/180 grids, pad
    # ripples counted as onsets). Tempo is verified by review of the worker's synth code instead.
    ratio = a_minor_ratio(mono, rate)
    checks["a_minor"] = ratio > 8  # correct A-minor outputs measured >= 16.9, wrong keys <= 3.1
    score = sum(checks.values()) / len(checks)
    failed = [k for k, v in checks.items() if not v]
    return {"score": round(float(score), 3), "passed": not failed,
            "notes": f"dur={dur:.2f}s peak={peak_db:.1f}dB key_ratio={ratio:.1f}"
                     + (f"; failed: {', '.join(failed)}" if failed else "")}


def a_minor_ratio(mono, rate):
    """Diatonic (A minor) vs chromatic energy of the *tonal* content. Per short frame, the frame's noise floor
    (median magnitude across frequency) is subtracted: broadband hi-hat noise sits at the floor and drops out,
    while sustained notes stand far above it. Band 180-1000 Hz keeps pitched kick sweeps out."""
    seg = mono[int(4 * rate):int(16 * rate)]
    n, hop = int(0.2 * rate), int(0.1 * rate)
    win = np.hanning(n)
    freqs = np.fft.rfftfreq(n, 1 / rate)
    band = (freqs > 180) & (freqs < 1000)  # kick sweeps start up to ~150 Hz
    pcs = np.round(12 * np.log2(freqs[band] / 440.0)).astype(int) % 12  # 0 = A
    chroma = np.zeros(12)
    for i in range(0, len(seg) - n, hop):
        mag = np.abs(np.fft.rfft(seg[i:i + n] * win))[band]
        tonal = np.clip(mag - 4 * np.median(mag), 0, None)
        chroma += np.bincount(pcs, weights=tonal ** 2, minlength=12)
    diatonic = [0, 2, 3, 5, 7, 8, 10]  # A B C D E F G
    return float(chroma[diatonic].sum() / max(chroma[[1, 4, 6, 9, 11]].sum(), 1e-12))
