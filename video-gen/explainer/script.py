"""Video script model and Claude-backed script generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SceneKind = Literal["title", "bullets", "diagram", "comparison", "stat"]
Side = Literal["none", "left", "right"]


class Step(BaseModel):
    """One beat of a scene: a visual element revealed while its narration plays."""

    text: str = Field(description="Short on-screen label revealed in this step (max ~8 words).")
    narration: str = Field(description="What the narrator says while this element appears (1-3 sentences).")
    side: Side = "none"


class Scene(BaseModel):
    kind: SceneKind
    heading: str
    steps: list[Step] = Field(min_length=1)
    left_label: str = ""
    right_label: str = ""
    stat_value: str = ""

    @model_validator(mode="after")
    def _check_kind(self) -> "Scene":
        if self.kind == "comparison":
            for s in self.steps:
                if s.side == "none":
                    s.side = "left"
        return self


class VideoScript(BaseModel):
    title: str
    scenes: list[Scene] = Field(min_length=1)

    @classmethod
    def load(cls, path: str | Path) -> "VideoScript":
        return cls.model_validate_json(Path(path).read_text())

    def save(self, path: str | Path) -> None:
        Path(path).write_text(self.model_dump_json(indent=2))


# Hand-written so it stays within what structured outputs accepts
# (every property required, no nulls, additionalProperties false).
_STEP_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {"type": "string"},
        "narration": {"type": "string"},
        "side": {"type": "string", "enum": ["none", "left", "right"]},
    },
    "required": ["text", "narration", "side"],
    "additionalProperties": False,
}

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": ["title", "bullets", "diagram", "comparison", "stat"]},
                    "heading": {"type": "string"},
                    "steps": {"type": "array", "items": _STEP_SCHEMA},
                    "left_label": {"type": "string"},
                    "right_label": {"type": "string"},
                    "stat_value": {"type": "string"},
                },
                "required": ["kind", "heading", "steps", "left_label", "right_label", "stat_value"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title", "scenes"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are a scriptwriter for short animated explainer videos.
You turn a topic into a sequence of scenes. Each scene is a slide whose elements
appear one at a time ("steps") while the narrator speaks that step's narration.

Scene kinds and how their fields are used:
- title: opening card. heading = video title. Each step's text is a subtitle line. Use exactly once, first.
- bullets: heading + a list of key points; one point per step.
- diagram: a left-to-right flow of 2-6 boxes connected by arrows (a process, pipeline or cause-and-effect chain).
  Each step adds one box; text is the box label (1-3 words).
- comparison: two columns. Set left_label and right_label. Each step adds one item to a column; set side to
  "left" or "right" accordingly.
- stat: one striking number or fact. stat_value is the big figure (e.g. "8 min", "70%"); each step's text is a
  short caption shown under it.

Rules:
- Fields a scene kind doesn't use are empty strings; side is "none" except in comparison scenes.
- On-screen text is terse (at most ~8 words); the narration carries the explanation in plain, spoken language.
- Narration must be speakable by a text-to-speech engine: no markdown, no symbols that read badly, spell out
  abbreviations on first use.
- Build intuition first, then mechanism, then a concrete example, then a one-line recap in the last scene.
- Prefer diagram and comparison scenes where they genuinely clarify; don't use the same kind three times in a row.
- Be factually accurate. If the topic is ambiguous, pick the most common interpretation."""


class ScriptGenerationError(RuntimeError):
    pass


def generate_script(
    topic: str,
    *,
    scenes: int = 6,
    audience: str = "curious beginners",
    minutes: float = 2.0,
    model: str = "claude-opus-5-5",
    effort: str = "medium",
) -> VideoScript:
    """Ask Claude for a structured, scene-by-scene script."""
    import anthropic

    client = anthropic.Anthropic()
    words = int(minutes * 150)
    user = (
        f"Topic: {topic}\n"
        f"Audience: {audience}\n"
        f"Target: about {scenes} scenes (including the title scene) and roughly {words} spoken words in total."
    )
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        output_config={
            "effort": effort,
            "format": {"type": "json_schema", "schema": SCRIPT_SCHEMA},
        },
        messages=[{"role": "user", "content": user}],
    )
    if response.stop_reason == "refusal":
        raise ScriptGenerationError("Claude declined to write a script for this topic.")
    if response.stop_reason == "max_tokens":
        raise ScriptGenerationError("Script was cut off (max_tokens); try fewer scenes or a shorter duration.")
    text = "".join(b.text for b in response.content if b.type == "text")
    try:
        return VideoScript.model_validate(json.loads(text))
    except (json.JSONDecodeError, ValueError) as e:
        raise ScriptGenerationError(f"Claude returned an invalid script: {e}") from e
