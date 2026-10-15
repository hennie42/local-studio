"""Media helpers for graders: ffprobe info, frame luma/colour sampling, WAV analysis (stdlib + numpy)."""
import json
import subprocess
import wave

import numpy as np


def probe(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                       capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(p.stdout)
    except json.JSONDecodeError:
        return {}
    out = {"duration": float(d.get("format", {}).get("duration", 0) or 0)}
    for s in d.get("streams", []):
        if s.get("codec_type") == "video" and "video" not in out:
            num, den = (s.get("r_frame_rate") or "0/1").split("/")
            out["video"] = {"codec": s.get("codec_name"), "width": s.get("width"), "height": s.get("height"),
                            "fps": float(num) / float(den or 1), "pix_fmt": s.get("pix_fmt")}
        if s.get("codec_type") == "audio" and "audio" not in out:
            out["audio"] = {"codec": s.get("codec_name"), "rate": int(s.get("sample_rate", 0)),
                            "channels": s.get("channels")}
    return out


def frame_rgb(path, t, w=64, h=36):
    """Mean RGB of a downscaled frame at time t (seconds), or None."""
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                        "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, timeout=60)
    if len(p.stdout) < w * h * 3:
        return None
    a = np.frombuffer(p.stdout[: w * h * 3], dtype=np.uint8).reshape(h, w, 3).astype(float)
    return a.reshape(-1, 3).mean(axis=0)


def mean_luma_at(path, t):
    rgb = frame_rgb(path, t)
    if rgb is None:
        return None
    return float(0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2])


def read_wav(path):
    with wave.open(str(path)) as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    if sw == 2:
        a = np.frombuffer(raw, dtype="<i2").astype(float) / 32768.0
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        a = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        a = np.where(a >= 1 << 23, a - (1 << 24), a).astype(float) / (1 << 23)
    elif sw == 4:
        a = np.frombuffer(raw, dtype="<i4").astype(float) / 2147483648.0
    else:
        raise ValueError(f"unsupported sample width {sw}")
    return a.reshape(-1, ch), rate
