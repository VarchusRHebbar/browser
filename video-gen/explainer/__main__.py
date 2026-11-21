"""CLI: python -m explainer "How does TCP work?" -o tcp.mp4"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
from pathlib import Path

from .render import Renderer
from .script import ScriptGenerationError, VideoScript, generate_script
from .video import build_video


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:60] or "explainer"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="explainer", description="Generate a narrated explainer video from a topic.")
    p.add_argument("topic", nargs="?", help="what the video should explain")
    p.add_argument("-o", "--output", type=Path, help="output .mp4 (default: <topic-slug>.mp4)")
    p.add_argument("--script", type=Path, help="render an existing script JSON instead of calling Claude")
    p.add_argument("--script-only", action="store_true", help="write the script JSON and stop")
    p.add_argument("--scenes", type=int, default=6, help="approximate number of scenes (default 6)")
    p.add_argument("--minutes", type=float, default=2.0, help="approximate length in minutes (default 2)")
    p.add_argument("--audience", default="curious beginners", help="who the video is for")
    p.add_argument("--model", default="claude-opus-5-5")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--tts", default="kokoro", choices=["kokoro", "espeak", "edge", "silent"],
                   help="narration voice engine (default kokoro: offline neural voice)")
    p.add_argument("--voice", help="voice for the TTS engine (kokoro: af_heart, am_michael, bf_emma, bm_george, ...)")
    p.add_argument("--speed", type=float, default=1.0, help="speech rate for kokoro (e.g. 0.9 slower, 1.1 faster)")
    p.add_argument("--list-voices", action="store_true", help="list kokoro voices and exit")
    p.add_argument("--size", default="1920x1080", help="WIDTHxHEIGHT (default 1920x1080)")
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--no-captions", action="store_true", help="don't burn narration captions into the video")
    p.add_argument("--keep-workdir", type=Path, help="keep intermediate frames/audio in this directory")
    p.add_argument("-j", "--jobs", type=int, default=4, help="parallel render jobs")
    a = p.parse_args(argv)

    if a.list_voices:
        from .tts import _get_kokoro
        print("\n".join(sorted(v for v in _get_kokoro().get_voices() if v[:2] in ("af", "am", "bf", "bm"))))
        return 0
    if not a.topic and not a.script:
        p.error("give a topic, or --script path/to/script.json")

    if a.script:
        script = VideoScript.load(a.script)
    else:
        print(f"Writing script with {a.model} ...", file=sys.stderr)
        try:
            script = generate_script(a.topic, scenes=a.scenes, audience=a.audience, minutes=a.minutes,
                                     model=a.model, effort=a.effort)
        except ScriptGenerationError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1

    base = a.output or Path(slug(script.title) + ".mp4")
    if not a.script:
        script_path = base.with_suffix(".json")
        script.save(script_path)
        print(f"Script saved to {script_path}", file=sys.stderr)
    if a.script_only:
        return 0

    w, h = (int(x) for x in a.size.lower().split("x"))
    renderer = Renderer(w, h, captions=not a.no_captions)
    work = a.keep_workdir or Path(tempfile.mkdtemp(prefix="explainer-"))
    try:
        build_video(script, base, work, renderer=renderer, tts_backend=a.tts, voice=a.voice, speed=a.speed,
                    fps=a.fps, jobs=a.jobs, log=lambda m: print(m, file=sys.stderr))
    finally:
        if not a.keep_workdir:
            shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
