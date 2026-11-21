"""Assemble rendered frames and narration into an MP4 with ffmpeg."""

from __future__ import annotations

import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import tts
from .render import Renderer
from .script import VideoScript

PAUSE_AFTER_STEP = 0.35   # seconds of breathing room after each step
PAUSE_AFTER_SCENE = 0.8   # extra hold on the last step of a scene
FADE_IN = 0.3


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def _clip(img: Path, wav: Path, out: Path, seconds: float, fade: bool, fps: int) -> None:
    vf = "format=yuv420p"
    if fade:
        vf = f"fade=t=in:st=0:d={FADE_IN}," + vf
    _ffmpeg(
        "-loop", "1", "-framerate", str(fps), "-i", str(img), "-i", str(wav),
        "-filter_complex", f"[0:v]{vf}[v];[1:a]apad[a]", "-map", "[v]", "-map", "[a]",
        "-t", f"{seconds:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage",
        "-r", str(fps), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2", str(out),
    )


def build_video(
    script: VideoScript,
    out: Path,
    workdir: Path,
    *,
    renderer: Renderer,
    tts_backend: str = "espeak",
    voice: str | None = None,
    fps: int = 30,
    jobs: int = 4,
    log: Callable[[str], None] = print,
) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    n = len(script.scenes)
    tasks = []
    for si, scene in enumerate(script.scenes):
        for st_i, step in enumerate(scene.steps):
            tasks.append((si, st_i, scene, step))

    def one(task) -> Path:
        si, st_i, scene, step = task
        stem = workdir / f"s{si:02d}_{st_i:02d}"
        png, wav, mp4 = stem.with_suffix(".png"), stem.with_suffix(".wav"), stem.with_suffix(".mp4")
        renderer.render(scene, st_i, si, n, script.title).save(png)
        tts.synthesize(step.narration, wav, tts_backend, voice)
        last = st_i == len(scene.steps) - 1
        seconds = tts.duration(wav) + PAUSE_AFTER_STEP + (PAUSE_AFTER_SCENE if last else 0)
        _clip(png, wav, mp4, seconds, fade=st_i == 0, fps=fps)
        return mp4

    log(f"Rendering {len(tasks)} steps across {n} scenes ...")
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        clips = list(pool.map(one, tasks))

    listing = workdir / "clips.txt"
    listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", "-movflags", "+faststart", str(out))
    log(f"Wrote {out} ({tts.duration(out):.1f}s)")
    return out
