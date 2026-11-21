"""AI explainer video generator: topic -> Claude script -> rendered scenes + narration -> MP4."""

from .render import Renderer
from .script import Scene, Step, VideoScript, generate_script
from .video import build_video

__all__ = ["Renderer", "Scene", "Step", "VideoScript", "build_video", "generate_script"]
