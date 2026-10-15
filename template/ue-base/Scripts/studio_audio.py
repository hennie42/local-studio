"""studio_audio: small numpy toolkit for procedural music and sound effects (48 kHz).

    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import studio_audio as sa
    tl = sa.Timeline(seconds=20)
    for i, chord in enumerate(sa.progression("Am F C G", octave=3)):      # one chord per bar
        tl.add(sa.pad(chord, sa.bars(1, bpm=90)), at=sa.bars(i, bpm=90))
    for b in sa.beat_times(20, bpm=90):
        tl.add(sa.kick(), at=b, gain=0.8)
    tl.add(sa.riser(4.0), at=12.0)                                       # tension into a cut at 16 s
    tl.add(sa.impact(), at=16.0)
    tl.write("audio/score.wav", peak_db=-1.5, fade_in=1.0, fade_out=2.0)
Times are in seconds; sa.bars()/beat_times() convert from musical time. Everything is mono until
Timeline.write(), which renders stereo with optional pan per clip.
"""
import math
import wave

import numpy as np

SR = 48000
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7,
         "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


# ------------------------------------------------------------------ pitch and time
def hz(note):
    """'A4' -> 440.0, 'C#3' -> 138.6; also accepts MIDI numbers."""
    if isinstance(note, (int, float)):
        return 440.0 * 2 ** ((note - 69) / 12)
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** (((octave + 1) * 12 + NOTES[name] - 69) / 12)


def chord(root, quality="min", octave=3):
    """Triad as frequencies: chord('A', 'min') -> A3 C4 E4. Qualities: maj, min, dim, sus2, sus4, maj7, min7."""
    steps = {"maj": (0, 4, 7), "min": (0, 3, 7), "dim": (0, 3, 6), "sus2": (0, 2, 7), "sus4": (0, 5, 7),
             "maj7": (0, 4, 7, 11), "min7": (0, 3, 7, 10)}[quality]
    base = (octave + 1) * 12 + NOTES[root]
    return [hz(base + s) for s in steps]


def progression(text, octave=3):
    """'Am F C G' -> list of chords (lowercase 'm' = minor, 'dim', '7' suffixes supported)."""
    out = []
    for sym in text.split():
        root = sym[:2] if len(sym) > 1 and sym[1] in "#b" else sym[:1]
        rest = sym[len(root):]
        q = {"": "maj", "m": "min", "dim": "dim", "sus2": "sus2", "sus4": "sus4", "maj7": "maj7", "m7": "min7"}[rest]
        out.append(chord(root, q, octave))
    return out


def bars(n, bpm, beats_per_bar=4):
    return n * beats_per_bar * 60.0 / bpm


def beat_times(seconds, bpm, offset=0.0, subdivision=1):
    step = 60.0 / bpm / subdivision
    return [offset + i * step for i in range(int((seconds - offset) / step) + 1) if offset + i * step < seconds]


# ------------------------------------------------------------------ building blocks
def t_axis(seconds):
    return np.arange(int(seconds * SR)) / SR


def adsr(n, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    a, d, r = int(attack * SR), int(decay * SR), int(release * SR)
    s = max(n - a - d - r, 0)
    env = np.concatenate([np.linspace(0, 1, a, endpoint=False), np.linspace(1, sustain, d, endpoint=False),
                          np.full(s, sustain), np.linspace(sustain, 0, r)])
    return np.pad(env, (0, max(n - env.size, 0)))[:n]


def osc(freq, seconds, shape="sine", detune_cents=0.0):
    t = t_axis(seconds)
    f = freq * 2 ** (detune_cents / 1200)
    ph = 2 * np.pi * f * t
    if shape == "sine":
        return np.sin(ph)
    if shape == "saw":  # band-limited-ish: sum of harmonics below 8 kHz
        return sum(np.sin(k * ph) / k for k in range(1, max(2, int(8000 / max(f, 1))))) * 0.6
    if shape == "square":
        return sum(np.sin(k * ph) / k for k in range(1, max(2, int(8000 / max(f, 1))), 2)) * 0.8
    if shape == "triangle":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    raise ValueError(shape)


def lowpass(x, cutoff):
    """Low-pass filter (FFT-based, soft knee)."""
    return _fast_lowpass(x, cutoff)


def pad(freqs, seconds, attack=0.6, release=0.8, shape="saw", detune=7.0, brightness=1800.0):
    """Warm detuned chord pad."""
    n = int(seconds * SR)
    x = sum(osc(f, seconds, shape, d) for f in freqs for d in (-detune, detune)) / (2 * len(freqs))
    x = _fast_lowpass(x, brightness)
    return x * adsr(n, attack, 0.2, 0.85, release)


def bass(freq, seconds, shape="triangle"):
    n = int(seconds * SR)
    return osc(freq, seconds, shape) * adsr(n, 0.005, 0.15, 0.6, 0.08) * 0.8


def pluck(freq, seconds=0.6):
    n = int(seconds * SR)
    return osc(freq, seconds, "triangle") * np.exp(-t_axis(seconds) * 6) * adsr(n, 0.002, 0.05, 1.0, 0.05)


def kick(seconds=0.35):
    t = t_axis(seconds)
    return np.sin(2 * np.pi * (45 + 90 * np.exp(-t * 35)) * t) * np.exp(-t * 9)


def snare(seconds=0.25, seed=2):
    t = t_axis(seconds)
    noise = np.random.default_rng(seed).uniform(-1, 1, t.size)
    return (0.6 * noise * np.exp(-t * 18) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25)) * 0.8


def hat(seconds=0.06, seed=1):
    t = t_axis(seconds)
    noise = np.random.default_rng(seed).uniform(-1, 1, t.size)
    return (noise - _fast_lowpass(noise, 6000)) * np.exp(-t * 70) * 0.9


def riser(seconds=4.0, seed=3):
    """Noise sweep rising in pitch and volume: tension before a cut."""
    t = t_axis(seconds)
    noise = np.random.default_rng(seed).uniform(-1, 1, t.size)
    sweep = np.sin(2 * np.pi * np.cumsum(200 + 1800 * (t / seconds) ** 2) / SR)
    return (0.5 * noise * (t / seconds) ** 2 + 0.3 * sweep * (t / seconds)) * 0.8


def impact(seconds=2.5, seed=4):
    """Low boom + noise burst: lands a cut or a reveal."""
    t = t_axis(seconds)
    boom = np.sin(2 * np.pi * (35 + 60 * np.exp(-t * 8)) * t) * np.exp(-t * 2.2)
    noise = np.random.default_rng(seed).uniform(-1, 1, t.size) * np.exp(-t * 12) * 0.4
    return boom + _fast_lowpass(noise, 1500)


def whoosh(seconds=1.2, seed=5):
    t = t_axis(seconds)
    noise = np.random.default_rng(seed).uniform(-1, 1, t.size)
    env = np.sin(np.pi * t / seconds) ** 2
    return _fast_lowpass(noise, 2500) * env * 1.5


def reverb(x, seconds=2.0, mix=0.3, seed=6):
    """Convolution with decaying noise (FFT): cheap, smooth room/hall."""
    t = t_axis(seconds)
    ir = np.random.default_rng(seed).normal(0, 1, t.size) * np.exp(-t * 6.9 / seconds)
    ir /= np.sqrt((ir ** 2).sum())
    n = x.size + ir.size - 1
    wet = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: x.size]
    return (1 - mix) * x + mix * wet


def _fast_lowpass(x, cutoff):
    """Low-pass via FFT brick-wall with a soft knee (much faster than the per-sample loop)."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(x.size, 1 / SR)
    spec *= 1 / (1 + (f / cutoff) ** 4)
    return np.fft.irfft(spec, x.size)


# ------------------------------------------------------------------ timeline and output
class Timeline:
    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.left = np.zeros(self.n)
        self.right = np.zeros(self.n)

    def add(self, clip, at, gain=1.0, pan=0.0):
        """Place a mono clip at time `at` (s). pan -1 (left) .. 1 (right)."""
        s = int(at * SR)
        if s >= self.n or clip.size == 0:
            return
        c = clip[: self.n - s] * gain
        lg, rg = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        self.left[s:s + c.size] += c * lg * math.sqrt(2)
        self.right[s:s + c.size] += c * rg * math.sqrt(2)

    def write(self, path, peak_db=-1.0, fade_in=0.0, fade_out=0.0, bits=16):
        st = np.stack([self.left, self.right], axis=1)
        t = np.arange(self.n) / SR
        dur = self.n / SR
        env = np.ones(self.n)
        if fade_in:
            env *= np.clip(t / fade_in, 0, 1)
        if fade_out:
            env *= np.clip((dur - t) / fade_out, 0, 1)
        st *= env[:, None]
        peak = np.abs(st).max()
        if peak > 0:
            st *= 10 ** (peak_db / 20) / peak
        with wave.open(str(path), "w") as w:
            w.setnchannels(2)
            w.setsampwidth(bits // 8)
            w.setframerate(SR)
            if bits == 16:
                w.writeframes((st * 32767).astype("<i2").tobytes())
            else:
                raise ValueError("only 16-bit output is supported")
        print(f"STUDIO_AUDIO wrote {path}: {dur:.2f}s stereo {SR} Hz, peak {peak_db} dBFS")
