import json
import shutil
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from explainer import Renderer, VideoScript, build_video  # noqa: E402
from explainer import script as script_mod  # noqa: E402

SAMPLE = ROOT / "examples" / "how-dns-works.json"


def test_sample_script_loads_and_covers_every_kind():
    s = VideoScript.load(SAMPLE)
    assert {sc.kind for sc in s.scenes} == {"title", "bullets", "diagram", "comparison", "stat"}


def test_comparison_defaults_side_to_left():
    s = VideoScript.model_validate({"title": "t", "scenes": [{"kind": "comparison", "heading": "h",
                                    "steps": [{"text": "a", "narration": "b"}]}]})
    assert s.scenes[0].steps[0].side == "left"


def test_renders_every_step_of_every_scene():
    s = VideoScript.load(SAMPLE)
    r = Renderer(640, 360)
    for i, sc in enumerate(s.scenes):
        for st in range(len(sc.steps)):
            img = r.render(sc, st, i, len(s.scenes), s.title)
            assert img.size == (640, 360)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_build_video_with_silent_tts(tmp_path):
    s = VideoScript.load(SAMPLE)
    s.scenes = s.scenes[:2]
    out = build_video(s, tmp_path / "out.mp4", tmp_path / "work", renderer=Renderer(640, 360),
                      tts_backend="silent", fps=10, log=lambda m: None)
    assert out.exists() and out.stat().st_size > 0


def test_generate_script_parses_structured_output(monkeypatch):
    payload = json.loads(SAMPLE.read_text())
    captured = {}

    class FakeMessages:
        def create(self, **kw):
            captured.update(kw)
            return types.SimpleNamespace(
                stop_reason="end_turn",
                content=[types.SimpleNamespace(type="thinking", thinking=""),
                         types.SimpleNamespace(type="text", text=json.dumps(payload))])

    fake = types.SimpleNamespace(Anthropic=lambda: types.SimpleNamespace(
        beta=types.SimpleNamespace(messages=FakeMessages())))
    monkeypatch.setitem(sys.modules, "anthropic", fake)

    s = script_mod.generate_script("DNS", scenes=6)
    assert s.title == "How DNS Works"
    assert captured["model"] == "claude-opus-5-5"
    assert captured["output_config"]["format"]["schema"] is script_mod.SCRIPT_SCHEMA


def test_generate_script_reports_refusal(monkeypatch):
    class FakeMessages:
        def create(self, **kw):
            return types.SimpleNamespace(stop_reason="refusal", content=[])

    fake = types.SimpleNamespace(Anthropic=lambda: types.SimpleNamespace(
        beta=types.SimpleNamespace(messages=FakeMessages())))
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    with pytest.raises(script_mod.ScriptGenerationError):
        script_mod.generate_script("x")


def test_kokoro_voice(tmp_path):
    pytest.importorskip("kokoro_onnx")
    from explainer import tts
    if not all((tts.KOKORO_DIR / f).exists() for f in tts.KOKORO_FILES):
        pytest.skip("Kokoro model not downloaded")
    out = tmp_path / "k.wav"
    tts.synthesize("Hello from the explainer.", out, "kokoro")
    assert tts.duration(out) > 0.5
