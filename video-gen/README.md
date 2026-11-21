# explainer: AI explainer video generator

Give it a topic and it produces a narrated, captioned MP4 explainer video.

```
topic ──► Claude writes a scene-by-scene script (structured JSON)
      ──► Pillow renders each scene, revealing one element per narration beat
      ──► Kokoro neural TTS reads the narration offline (espeak-ng / edge-tts optional)
      ──► ffmpeg turns each beat into a clip and joins them into one MP4
```

This is a standalone Python tool. It doesn't depend on the Lightpanda browser code in the rest of this repository.

## Setup

```bash
cd video-gen
pip install -r requirements.txt
sudo apt-get install ffmpeg espeak-ng      # macOS: brew install ffmpeg espeak-ng
export ANTHROPIC_API_KEY=...               # or `ant auth login`
```

On the first render, the Kokoro voice model (~120 MB) downloads from GitHub into `~/.cache/explainer/kokoro`; set `EXPLAINER_CACHE` to put it elsewhere. If the download fails, the tool falls back to espeak-ng.

## Usage

```bash
# Topic → script.json + video.mp4
python -m explainer "How does public-key cryptography work?" -o crypto.mp4

# Tune the content
python -m explainer "Photosynthesis" --audience "10-year-olds" --minutes 1.5 --scenes 5

# Review or edit the script before rendering
python -m explainer "How vaccines work" --script-only -o vaccines.mp4   # writes vaccines.json
$EDITOR vaccines.json
python -m explainer --script vaccines.json -o vaccines.mp4

# Try it without an API key, using the bundled sample script
python -m explainer --script examples/how-dns-works.json -o dns.mp4
```

Useful flags:

| Flag | Default | Notes |
|---|---|---|
| `--tts kokoro\|espeak\|edge\|silent` | `kokoro` | `kokoro` is an offline neural voice; `espeak` sounds robotic but is tiny; `edge` needs `pip install edge-tts` and network access; `silent` times each step from its word count |
| `--voice` | `af_heart` | Kokoro voices: `af_*`/`am_*` US female/male, `bf_*`/`bm_*` UK (`--list-voices` shows all). For espeak: `en-gb`; for edge: `en-US-GuyNeural` |
| `--speed` | `1.0` | Kokoro speech rate, e.g. `0.9` for slower, more deliberate narration |
| `--size` | `1920x1080` | e.g. `1080x1920` for vertical shorts, `1280x720` for faster renders |
| `--no-captions` | captions on | burned-in narration captions |
| `--model` / `--effort` | `claude-opus-5-5` / `medium` | model and effort level used to write the script |
| `--keep-workdir DIR` | temp dir | keep the per-step PNG/WAV/MP4 files |

## Script format

Claude's output is validated against `SCRIPT_SCHEMA` in `explainer/script.py`. Each scene has a `kind` and a list of `steps`. Every step reveals one element while its `narration` is spoken.

| kind | What's on screen | Fields used |
|---|---|---|
| `title` | Title card; each step adds a subtitle line | `heading` |
| `bullets` | Numbered points, the current one highlighted | `heading` |
| `diagram` | Boxes joined by arrows, wrapping onto a second row past four boxes | `heading` |
| `comparison` | Two columns; each step adds an item to one side | `left_label`, `right_label`, `step.side` |
| `stat` | One large figure with captions underneath | `stat_value` |

See `examples/how-dns-works.json` for a full example.

## Notes

- Script requests use server-side refusal fallbacks (`fallbacks: "default"`, beta `server-side-fallback-2026-07-01`). If the model declines a topic, the API reruns the request on a fallback model. Remove those two arguments in `generate_script` if you'd rather not use them.
- Every narration clip is loudness-normalized to -16 LUFS, so the volume stays even from scene to scene.
- Steps render in parallel (`-j`). On 4 CPU cores, a 2-minute 1080p video takes about 1.5 minutes with Kokoro and about 30 seconds with espeak.

## Tests

```bash
python -m pytest tests     # offline; the Claude call is mocked
```
