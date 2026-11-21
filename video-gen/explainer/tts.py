"""Text-to-speech backends. Every backend writes a 44.1 kHz stereo WAV."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

WORDS_PER_SECOND = 2.6  # used by the silent backend to time steps
DEFAULT_KOKORO_VOICE = "af_heart"

KOKORO_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
KOKORO_FILES = ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
KOKORO_DIR = Path(os.environ.get("EXPLAINER_CACHE", Path.home() / ".cache" / "explainer")) / "kokoro"

# Even out loudness across clips (EBU R128, podcast-style -16 LUFS).
LOUDNORM = "loudnorm=I=-16:TP=-1.5:LRA=11"


def _to_wav(src: Path, dst: Path, normalize: bool = True) -> None:
    af = ["-af", LOUDNORM] if normalize else []
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), *af, "-ar", "44100", "-ac", "2", str(dst)],
        check=True,
    )


_kokoro = None
_kokoro_lock = threading.Lock()


def _ensure_kokoro_model() -> Path:
    KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    for name in KOKORO_FILES:
        dest = KOKORO_DIR / name
        if not dest.exists():
            print(f"Downloading Kokoro voice model {name} (one time) ...", file=sys.stderr)
            tmp = dest.with_suffix(".part")
            urllib.request.urlretrieve(KOKORO_URL + name, tmp)
            tmp.rename(dest)
    return KOKORO_DIR


def _get_kokoro():
    global _kokoro
    with _kokoro_lock:
        if _kokoro is None:
            try:
                from kokoro_onnx import Kokoro  # type: ignore
            except ImportError as e:
                raise RuntimeError("kokoro-onnx is not installed: pip install kokoro-onnx soundfile") from e
            d = _ensure_kokoro_model()
            _kokoro = Kokoro(str(d / KOKORO_FILES[0]), str(d / KOKORO_FILES[1]))
        return _kokoro


def kokoro_available() -> bool:
    try:
        _get_kokoro()
        return True
    except Exception as e:  # missing package, no network, corrupt download ...
        print(f"Kokoro unavailable ({e}); falling back to espeak-ng.", file=sys.stderr)
        return False


def synth_kokoro(text: str, out: Path, voice: str = DEFAULT_KOKORO_VOICE, speed: float = 1.0) -> None:
    import soundfile as sf  # type: ignore

    k = _get_kokoro()
    lang = "en-gb" if voice.startswith(("bf_", "bm_")) else "en-us"
    samples, sr = k.create(text, voice=voice, speed=speed, lang=lang)
    raw = out.with_suffix(".raw.wav")
    sf.write(str(raw), samples, sr)
    _to_wav(raw, out)
    raw.unlink()


def synth_espeak(text: str, out: Path, voice: str = "en-us", speed: int = 160) -> None:
    if not shutil.which("espeak-ng"):
        raise RuntimeError("espeak-ng is not installed (apt-get install espeak-ng), or use --tts silent/edge")
    raw = out.with_suffix(".raw.wav")
    subprocess.run(["espeak-ng", "-v", voice, "-s", str(speed), "-w", str(raw), text], check=True)
    _to_wav(raw, out)
    raw.unlink()


def synth_edge(text: str, out: Path, voice: str = "en-US-AriaNeural") -> None:
    try:
        import edge_tts  # type: ignore
    except ImportError as e:
        raise RuntimeError("edge-tts is not installed: pip install edge-tts") from e
    mp3 = out.with_suffix(".mp3")
    edge_tts.Communicate(text, voice).save_sync(str(mp3))
    _to_wav(mp3, out)
    mp3.unlink()


def synth_silent(text: str, out: Path) -> None:
    seconds = max(1.5, len(text.split()) / WORDS_PER_SECOND)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{seconds:.2f}", str(out)],
        check=True,
    )


def synthesize(text: str, out: Path, backend: str = "kokoro", voice: str | None = None,
               speed: float = 1.0) -> None:
    if backend == "kokoro":
        synth_kokoro(text, out, voice or DEFAULT_KOKORO_VOICE, speed)
    elif backend == "espeak":
        synth_espeak(text, out, **({"voice": voice} if voice else {}))
    elif backend == "edge":
        synth_edge(text, out, **({"voice": voice} if voice else {}))
    elif backend == "silent":
        synth_silent(text, out)
    else:
        raise ValueError(f"unknown TTS backend: {backend}")


def duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip())
