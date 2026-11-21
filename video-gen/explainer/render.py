"""Render scene frames with Pillow.

Each scene is drawn once per step: frame *i* shows elements 0..i, with element i
highlighted as the one currently being narrated.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .script import Scene

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation",
             "/Library/Fonts", "C:/Windows/Fonts"]
FONT_FILES = {"regular": ["DejaVuSans.ttf", "LiberationSans-Regular.ttf", "Arial.ttf", "arial.ttf"],
              "bold": ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]}


@dataclass(frozen=True)
class Theme:
    bg: str = "#0f172a"
    panel: str = "#1e293b"
    text: str = "#f1f5f9"
    muted: str = "#94a3b8"
    dim: str = "#64748b"
    accent: str = "#38bdf8"
    accent2: str = "#f472b6"
    caption_bg: tuple = (2, 6, 23, 200)


THEME = Theme()


@lru_cache(maxsize=None)
def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for d in FONT_DIRS:
        for f in FONT_FILES[weight]:
            p = Path(d) / f
            if p.exists():
                return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def text_w(draw: ImageDraw.ImageDraw, s: str, f) -> float:
    return draw.textlength(s, font=f)


def wrap(draw: ImageDraw.ImageDraw, s: str, f, max_w: float) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and text_w(draw, trial, f) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


def fit_font(draw, s: str, max_w: float, max_lines: int, start: int, weight="regular", min_size=14):
    size = start
    while size > min_size:
        f = font(size, weight)
        if len(wrap(draw, s, f, max_w)) <= max_lines:
            return f
        size -= 2
    return font(min_size, weight)


def draw_lines(draw, lines, f, x, y, fill, align="left", box_w=0.0, spacing=1.25):
    lh = f.size * spacing
    for i, line in enumerate(lines):
        lx = x
        if align == "center":
            lx = x + (box_w - text_w(draw, line, f)) / 2
        draw.text((lx, y + i * lh), line, font=f, fill=fill)
    return y + len(lines) * lh


class Renderer:
    def __init__(self, width: int = 1920, height: int = 1080, captions: bool = True, theme: Theme = THEME):
        self.W, self.H = width, height
        self.s = width / 1920  # scale factor; layouts are designed at 1080p
        self.captions = captions
        self.t = theme

    def px(self, v: float) -> int:
        return int(v * self.s)

    # ---- frame chrome -------------------------------------------------
    def _base(self, scene_idx: int, n_scenes: int, video_title: str):
        img = Image.new("RGB", (self.W, self.H), self.t.bg)
        d = ImageDraw.Draw(img, "RGBA")
        # progress bar along the bottom
        bar_h = self.px(6)
        d.rectangle([0, self.H - bar_h, self.W, self.H], fill=self.t.panel)
        d.rectangle([0, self.H - bar_h, int(self.W * (scene_idx + 1) / n_scenes), self.H], fill=self.t.accent)
        d.text((self.px(60), self.H - self.px(52)), video_title, font=font(self.px(22)), fill=self.t.dim)
        return img, d

    def _heading(self, d, heading: str) -> int:
        f = fit_font(d, heading, self.W - self.px(240), 1, self.px(64), "bold")
        d.text((self.px(120), self.px(90)), heading, font=f, fill=self.t.text)
        y = self.px(90) + f.size + self.px(22)
        d.rectangle([self.px(120), y, self.px(240), y + self.px(8)], fill=self.t.accent)
        return y + self.px(60)

    def _caption(self, img, d, narration: str):
        if not self.captions or not narration:
            return
        f = font(self.px(30))
        max_w = self.W - self.px(400)
        lines = wrap(d, narration, f, max_w)[:3]
        lh = f.size * 1.3
        box_h = len(lines) * lh + self.px(30)
        y0 = self.H - self.px(80) - box_h
        d.rounded_rectangle([self.px(160), y0, self.W - self.px(160), y0 + box_h],
                            radius=self.px(14), fill=self.t.caption_bg)
        draw_lines(d, lines, f, self.px(200), y0 + self.px(15), self.t.text, "center", max_w, 1.3)

    # ---- scene kinds --------------------------------------------------
    def _title(self, d, scene: Scene, step: int):
        f = fit_font(d, scene.heading, self.W - self.px(300), 2, self.px(96), "bold")
        lines = wrap(d, scene.heading, f, self.W - self.px(300))
        y = self.H * 0.30
        y = draw_lines(d, lines, f, self.px(150), y, self.t.text, "center", self.W - self.px(300), 1.15)
        cx = self.W / 2
        d.rectangle([cx - self.px(80), y + self.px(24), cx + self.px(80), y + self.px(32)], fill=self.t.accent)
        y += self.px(70)
        for i, st in enumerate(scene.steps[: step + 1]):
            sf = font(self.px(40))
            col = self.t.accent if i == step else self.t.muted
            sl = wrap(d, st.text, sf, self.W - self.px(400))
            y = draw_lines(d, sl, sf, self.px(200), y, col, "center", self.W - self.px(400)) + self.px(10)

    def _bullets(self, d, scene: Scene, step: int, top: int):
        n = len(scene.steps)
        avail = self.H - top - self.px(300 if self.captions else 160)
        row = min(self.px(130), avail / max(n, 1))
        f = font(int(min(self.px(46), row * 0.42)))
        r = int(f.size * 0.75)
        for i, st in enumerate(scene.steps[: step + 1]):
            y = top + i * row
            active = i == step
            cx, cy = self.px(150) + r, y + f.size * 0.6
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=self.t.accent if active else self.t.panel)
            num = str(i + 1)
            nf = font(int(r * 1.1), "bold")
            d.text((cx - text_w(d, num, nf) / 2, cy - nf.size * 0.62), num, font=nf,
                   fill=self.t.bg if active else self.t.muted)
            lines = wrap(d, st.text, f, self.W - self.px(420))[:2]
            draw_lines(d, lines, f, cx + r + self.px(36), y, self.t.text if active else self.t.muted)

    def _box(self, d, x0, y0, x1, y1, label, active, revealed=True):
        if not revealed:
            d.rounded_rectangle([x0, y0, x1, y1], radius=self.px(20), outline=self.t.panel, width=self.px(3))
            return
        d.rounded_rectangle([x0, y0, x1, y1], radius=self.px(20),
                            fill=self.t.accent if active else self.t.panel,
                            outline=self.t.accent, width=self.px(3))
        w = x1 - x0 - self.px(30)
        f = fit_font(d, label, w, 3, self.px(36), "bold")
        lines = wrap(d, label, f, w)[:3]
        th = len(lines) * f.size * 1.2
        draw_lines(d, lines, f, x0 + self.px(15), y0 + (y1 - y0 - th) / 2,
                   self.t.bg if active else self.t.text, "center", w, 1.2)

    def _arrow(self, d, x0, y, x1, color):
        w = self.px(5)
        d.line([x0, y, x1 - self.px(14), y], fill=color, width=w)
        h = self.px(14)
        d.polygon([(x1, y), (x1 - h * 1.4, y - h), (x1 - h * 1.4, y + h)], fill=color)

    def _diagram(self, d, scene: Scene, step: int, top: int):
        n = len(scene.steps)
        per_row = n if n <= 4 else (n + 1) // 2
        rows = (n + per_row - 1) // per_row
        margin, gap = self.px(120), self.px(90)
        box_w = (self.W - 2 * margin - gap * (per_row - 1)) / per_row
        box_h = self.px(200)
        bottom = self.H - self.px(300 if self.captions else 160)
        total_h = rows * box_h + (rows - 1) * self.px(110)
        y_start = top + max(0, (bottom - top - total_h) / 2)
        centers = []
        for i, st in enumerate(scene.steps):
            r, c = divmod(i, per_row)
            x0 = margin + c * (box_w + gap)
            y0 = y_start + r * (box_h + self.px(110))
            centers.append((x0, y0))
            self._box(d, x0, y0, x0 + box_w, y0 + box_h, st.text, i == step, i <= step)
        for i in range(1, min(step + 1, n)):
            (px0, py0), (x0, y0) = centers[i - 1], centers[i]
            if py0 == y0:
                self._arrow(d, px0 + box_w + self.px(10), y0 + box_h / 2, x0 - self.px(10), self.t.accent)
            else:  # wrap to next row: elbow down then left to the next box's top
                sx, sy = px0 + box_w / 2, py0 + box_h + self.px(8)
                ex, ey = x0 + box_w / 2, y0 - self.px(8)
                mid = (sy + ey) / 2
                w = self.px(5)
                d.line([sx, sy, sx, mid], fill=self.t.accent, width=w)
                d.line([sx, mid, ex, mid], fill=self.t.accent, width=w)
                d.line([ex, mid, ex, ey - self.px(14)], fill=self.t.accent, width=w)
                h = self.px(14)
                d.polygon([(ex, ey), (ex - h, ey - h * 1.4), (ex + h, ey - h * 1.4)], fill=self.t.accent)

    def _comparison(self, d, scene: Scene, step: int, top: int):
        margin, gap = self.px(120), self.px(60)
        col_w = (self.W - 2 * margin - gap) / 2
        bottom = self.H - self.px(290 if self.captions else 150)
        cols = {"left": (margin, scene.left_label or "A", self.t.accent),
                "right": (margin + col_w + gap, scene.right_label or "B", self.t.accent2)}
        lf = font(self.px(44), "bold")
        for x, label, color in cols.values():
            d.rounded_rectangle([x, top, x + col_w, bottom], radius=self.px(20), fill=self.t.panel)
            d.text((x + self.px(36), top + self.px(28)), label, font=lf, fill=color)
            d.rectangle([x + self.px(36), top + self.px(90), x + self.px(116), top + self.px(96)], fill=color)
        counts = {"left": 0, "right": 0}
        per_col = max(1, max(sum(1 for s in scene.steps if (s.side if s.side != "none" else "left") == k)
                             for k in counts))
        row = min(self.px(110), (bottom - top - self.px(130)) / per_col)
        f = font(int(min(self.px(36), row * 0.4)))
        for i, st in enumerate(scene.steps[: step + 1]):
            side = st.side if st.side != "none" else "left"
            x, _, color = cols[side]
            y = top + self.px(130) + counts[side] * row
            counts[side] += 1
            active = i == step
            d.ellipse([x + self.px(40), y + f.size * 0.35, x + self.px(40) + f.size * 0.5, y + f.size * 0.85],
                      fill=color if active else self.t.dim)
            lines = wrap(d, st.text, f, col_w - self.px(120))[:2]
            draw_lines(d, lines, f, x + self.px(80), y, self.t.text if active else self.t.muted)

    def _stat(self, d, scene: Scene, step: int, top: int):
        value = scene.stat_value or "?"
        f = fit_font(d, value, self.W - self.px(300), 1, self.px(220), "bold")
        y = top + self.px(20)
        d.text(((self.W - text_w(d, value, f)) / 2, y), value, font=f, fill=self.t.accent)
        y += f.size * 1.2
        for i, st in enumerate(scene.steps[: step + 1]):
            cf = font(self.px(40))
            col = self.t.text if i == step else self.t.dim
            lines = wrap(d, st.text, cf, self.W - self.px(400))
            y = draw_lines(d, lines, cf, self.px(200), y, col, "center", self.W - self.px(400)) + self.px(8)

    # ---- public -------------------------------------------------------
    def render(self, scene: Scene, step: int, scene_idx: int, n_scenes: int, video_title: str) -> Image.Image:
        img, d = self._base(scene_idx, n_scenes, video_title)
        if scene.kind == "title":
            self._title(d, scene, step)
        else:
            top = self._heading(d, scene.heading)
            {"bullets": self._bullets, "diagram": self._diagram,
             "comparison": self._comparison, "stat": self._stat}[scene.kind](d, scene, step, top)
        self._caption(img, d, scene.steps[step].narration)
        return img
