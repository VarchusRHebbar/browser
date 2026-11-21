# explainer: AI explainer video generator

Give it a topic and it produces a narrated, captioned MP4 explainer video.

```
topic ──► Claude writes a scene-by-scene script (structured JSON)
      ──► Pillow renders each scene, revealing one element per narration beat
      ──► TTS reads the narration (espeak-ng offline, or edge-tts neural voices)
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
| `--tts espeak\|edge\|silent` | `espeak` | `edge` needs `pip install edge-tts` and network access; `silent` times each step from its word count |
| `--voice` | engine default | e.g. `en-gb` (espeak) or `en-US-GuyNeural` (edge) |
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
- Steps render in parallel (`-j`). A 2-minute 1080p video takes about 30 seconds on 4 cores.

## Tests

```bash
python -m pytest tests     # offline; the Claude call is mocked
```
