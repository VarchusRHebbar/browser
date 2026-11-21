"""Text-to-speech backends. Every backend writes a 44.1 kHz stereo WAV."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

WORDS_PER_SECOND = 2.6  # used by the silent backend to time steps


def _to_wav(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", "44100", "-ac", "2", str(dst)],
        check=True,
    )


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


def synthesize(text: str, out: Path, backend: str = "espeak", voice: str | None = None) -> None:
    if backend == "espeak":
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
