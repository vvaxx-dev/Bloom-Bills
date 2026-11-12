"""Immediate-mode pixel-art renderer: cached bitmap text, palette-swapped sprites, and UI widgets."""

import math

import pygame

from .settings import CANVAS_H, CANVAS_W, DIM, PANEL, PANEL_DARK, PANEL_LIGHT, TEXT
from .sprites_data import FONT, GRIDS, PALETTE

_text_cache = {}
_sprite_cache = {}
_overlay_cache = {}

_DEFAULT_GLYPH = FONT["?"]
_GLYPH_WIDTHS = {ch: len(rows[0]) + 1 for ch, rows in FONT.items()}
_DEFAULT_GLYPH_W = len(_DEFAULT_GLYPH[0]) + 1
_SHADOW_SUBS = {k: (20, 16, 28) for k in PALETTE}

COG_HOVER_SUBS = {"w": (255, 248, 210), "d": (250, 210, 70), "D": (200, 145, 45)}
SHOVEL_HOVER_SUBS = {"w": (255, 252, 232), "d": (204, 210, 230), "D": (136, 142, 170), "y": (255, 228, 104)}


def inside(pos, r):
    """Return True if point `pos` lies inside `(x, y, w, h)`."""
    return r[0] <= pos[0] < r[0] + r[2] and r[1] <= pos[1] < r[1] + r[3]


def text_width(text, scale=1):
    if not text:
        return 0
    upper = str(text).upper()
    return (sum(_GLYPH_WIDTHS.get(ch, _DEFAULT_GLYPH_W) for ch in upper) - 1) * scale


def _text_surface(upper_text, color, scale):
    rgb = tuple(color)[:3]
    key = (upper_text, rgb, scale)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 3000:
            _text_cache.clear()
        w = max(1, (sum(_GLYPH_WIDTHS.get(ch, _DEFAULT_GLYPH_W) for ch in upper_text) - 1) * scale)
        surf = pygame.Surface((w, 5 * scale), pygame.SRCALPHA)
        rgba = rgb + (255,)
        cursor = 0
        for ch in upper_text:
            glyph = FONT.get(ch, _DEFAULT_GLYPH)
            for ry, row in enumerate(glyph):
                for rx, pixel in enumerate(row):
                    if pixel == "#":
                        surf.fill(rgba, ((cursor + rx) * scale, ry * scale, scale, scale))
            cursor += len(glyph[0]) + 1
        _text_cache[key] = surf
    return surf


def draw_text(surf, text, x, y, color=TEXT, scale=1, align="left", shadow=None):
    upper = str(text).upper()
    if not upper:
        return 0
    glyph_surf = _text_surface(upper, color, scale)
    w = glyph_surf.get_width()
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    x, y = int(x), int(y)
    if shadow:
        off = max(1, scale // 3)
        surf.blit(_text_surface(upper, shadow, scale), (x + off, y + off))
    surf.blit(glyph_surf, (x, y))
    return w


def wrap(text, max_width, scale=1):
    lines, line = [], ""
    for word in str(text).split():
        trial = word if not line else line + " " + word
        if text_width(trial, scale) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_wrapped(surf, text, x, y, max_width, color=TEXT, scale=1, line_gap=2):
    lines = wrap(text, max_width, scale)
    step = 5 * scale + line_gap
    for i, line in enumerate(lines):
        draw_text(surf, line, x, y + i * step, color, scale)
    return len(lines)


def button_lines(label, max_width, scale=1):
    """Wrap a button label while preserving explicit newline splits (e.g. name above price)."""
    lines = []
    for chunk in str(label).split("\n"):
        lines.extend(wrap(chunk, max_width, scale))
    return lines or [""]


def sprite(name, scale=1, subs=None):
    """Decode and cache a character-grid sprite, falling back to 'unknown' if missing."""
    key = (name, scale, tuple(sorted(subs.items())) if subs else None)
    surf = _sprite_cache.get(key)
    if surf is None:
        grid = GRIDS.get(name) or GRIDS["unknown"]
        palette = dict(PALETTE, **subs) if subs else PALETTE
        h, w = len(grid), len(grid[0])
        surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
        for y, row in enumerate(grid):
            for x, char in enumerate(row):
                if char != ".":
                    surf.fill(tuple(palette[char]) + (255,), (x * scale, y * scale, scale, scale))
        _sprite_cache[key] = surf
    return surf


def plant_anim_style(species_id, species_meta=None, stage_sprite=None):
    """Classify a plant into a movement archetype based on its growth stage and family."""
    if stage_sprite == "seed":
        return "seed"
    if stage_sprite in ("sprout", "leafy"):
        return "sprout"
    meta = species_meta or {}
    base = meta.get("base", species_id)
    tags = set(meta.get("tags", ()))
    if "carnivore" in tags or base == "venus_flytrap":
        return "carnivore"
    if "mushroom" in tags or "fungus" in tags:
        return "mushroom"
    if "grain" in tags or base in ("wheat", "corn", "four_leaf_clover", "devil_ivy"):
        return "reed"
    if "desert" in tags:
        return "cactus"
    if "flower" in tags:
        return "flower"
    return "crop"


def plant_anim(t, index=0, style="flower", started=False, ripe=False, speed=1.0, hovered=False, wind=0.0, glow=False):
    """Compute crisp integer band offsets, squash/stretch, hop, and micro-particles for a plant."""
    if t <= 0 and not hovered:
        return None
    rate = max(0.45, min(2.4, float(speed))) if started else 0.55
    phase = float(index) * 1.37
    w = float(t) * (2.6 * rate) + phase
    breeze = int(round(wind))

    dx0 = dx1 = dx2 = dx3 = 0
    stretch = 0
    hop = 1 if hovered else 0

    if style == "seed":
        if started and math.sin(w * 1.4) > 0.86:
            dx2 = dx3 = 1 if int(w * 3) % 2 == 0 else -1
    elif style == "sprout":
        dx0 = int(round(math.sin(w) * (1.1 + 0.4 * abs(wind)))) + breeze
        dx1 = int(round(dx0 * 0.5))
        stretch = 1 if math.sin(w * 1.5) > 0.45 else 0
    elif style == "carnivore":
        # Predatory coil-and-snap rhythm.
        snap = math.sin(w * 1.35)
        dx1 = int(round(math.sin(w * 0.8) * 1.0)) + breeze
        if snap > 0.72:
            stretch = 1
            dx0 = dx1 + (1 if math.cos(w * 0.8) >= 0 else -1)
        elif snap < -0.55:
            stretch = -1
            dx0 = dx1
        else:
            dx0 = dx1
    elif style == "mushroom":
        # Stout jelly-cap pulse with anchored stem.
        pulse = math.sin(w * 1.25)
        if pulse > 0.52:
            stretch = 1
        elif pulse < -0.52:
            stretch = -1
        dx0 = int(round(math.sin(w * 0.65) * 0.8)) + breeze
    elif style == "tree":
        # Grounded woody trunk with counter-rustling leafy crown.
        dx0 = int(round(math.sin(w * 1.15) * (1.15 + 0.5 * abs(wind)))) + breeze
        dx1 = int(round(math.sin(w * 1.15 + 1.9) * 0.9)) + breeze
    elif style == "cactus":
        # Mostly stoic, with an occasional proud desert shimmy.
        burst = math.sin(w * 0.75)
        if burst > 0.78:
            dx0 = 1 if int(w * 4) % 2 == 0 else -1
            stretch = 1
        elif wind:
            dx0 = breeze
    elif style == "reed":
        # Travelling wave cascading from lower stalk to tip.
        dx2 = int(round(math.sin(w) * 0.7))
        dx1 = int(round(math.sin(w - 0.7) * 1.2)) + breeze
        dx0 = int(round(math.sin(w - 1.35) * (1.6 + 0.5 * abs(wind)))) + breeze
        stretch = 1 if math.cos(w * 2.0) > 0.65 else 0
    elif style == "flower":
        # Graceful wind-nodding blossom with pendular sun-bob.
        amp = 1.25 + 0.55 * abs(wind)
        s = math.sin(w)
        dx0 = int(round(s * amp)) + breeze
        dx1 = int(round(s * 0.65)) + (breeze // 2)
        dx2 = int(round(s * 0.25))
        c2 = math.cos(w * 2.0)
        stretch = 1 if c2 > 0.55 else (-1 if c2 < -0.68 else 0)
    else:
        # Plump garden crop bounce and leafy top wiggle.
        bounce = math.sin(w * 1.2)
        stretch = 1 if bounce > 0.55 else (-1 if bounce < -0.58 else 0)
        dx0 = int(round(math.sin(w * 0.9) * 1.0)) + breeze
        dx1 = int(round(dx0 * 0.45))

    if ripe and t > 0:
        hop_wave = math.sin(float(t) * 4.4 + phase)
        if hop_wave > 0.45:
            hop = max(hop, 2 if hop_wave > 0.84 else 1)
            stretch = max(stretch, 0)

    return {
        "dx": (dx0, dx1, dx2, dx3),
        "stretch": stretch,
        "hop": hop,
        "style": style,
        "ripe": ripe,
        "started": started,
        "glow": glow,
        "t": float(t),
        "phase": phase,
    }


def _blit_animated_plant(surf, base, x, y, scale, anim):
    w, h = base.get_width(), base.get_height()
    dx0, dx1, dx2, dx3 = anim.get("dx", (0, 0, 0, 0))
    stretch = int(anim.get("stretch", 0))
    hop = int(anim.get("hop", 0))
    if h < 8:
        surf.blit(base, (x + dx0, y - hop))
        return

    s1 = max(2, (h * 7) // 24)
    s2 = max(s1 + 2, (h * 14) // 24)
    s3 = max(s2 + 1, (h * 19) // 24)
    top_y = y - hop

    if stretch > 0:
        surf.blit(base, (x + dx0, top_y - 1), (0, 0, w, s1))
        surf.blit(base, (x + dx1, top_y + s1 - 1), (0, s1, w, 1))
        surf.blit(base, (x + dx1, top_y + s1), (0, s1, w, s2 - s1))
    elif stretch < 0 and s2 - s1 > 1:
        surf.blit(base, (x + dx0, top_y + 1), (0, 0, w, s1))
        surf.blit(base, (x + dx1, top_y + s1 + 1), (0, s1 + 1, w, s2 - s1 - 1))
    else:
        surf.blit(base, (x + dx0, top_y), (0, 0, w, s1))
        surf.blit(base, (x + dx1, top_y + s1), (0, s1, w, s2 - s1))

    surf.blit(base, (x + dx2, top_y + s2), (0, s2, w, s3 - s2))
    surf.blit(base, (x + dx3, top_y + s3), (0, s3, w, h - s3))

    t = anim.get("t", 0.0)
    phase = anim.get("phase", 0.0)
    if anim.get("style") == "mushroom" and anim.get("started") and t > 0:
        cyc = (t * 0.9 + phase) % 1.0
        if cyc < 0.72:
            sx = x + w // 2 + int(round(math.sin(cyc * 6.2 + phase) * 4)) + dx0
            sy = top_y + s1 - int(cyc * 7)
            col = (130, 240, 225) if anim.get("glow") else (235, 224, 196)
            surf.fill(col, (sx, sy, 1, 1))
    if anim.get("ripe") and t > 0:
        tw = (t * 2.2 + phase) % 1.0
        if tw < 0.48:
            gx = x + (3 if int(t * 2.2 + phase) % 2 == 0 else w - 4) + dx0
            gy = top_y + 2
            surf.fill((255, 246, 160), (gx, gy, 1, 1))
            if tw < 0.24:
                surf.fill((255, 255, 235), (gx - 1, gy, 3, 1))
                surf.fill((255, 255, 235), (gx, gy - 1, 1, 3))


def draw_sprite(surf, name, x, y, scale=1, subs=None, anim=None):
    base = sprite(name, scale, subs)
    if not anim:
        surf.blit(base, (int(x), int(y)))
        return
    _blit_animated_plant(surf, base, int(x), int(y), scale, anim)


def draw_cursor(surf, pos, kind="cursor"):
    """Draw the custom pixel cursor anchored at `pos` (shovel blade tip when digging)."""
    x, y = int(pos[0]), int(pos[1])
    if kind == "shovel":
        sh = sprite("shovel", 1)
        sx, sy = x, y - (sh.get_height() - 1)
        surf.blit(sprite("shovel", 1, _SHADOW_SUBS), (sx + 1, sy + 1))
        surf.blit(sh, (sx, sy))
        return
    surf.blit(sprite("cursor", 1, {"w": (20, 16, 28), "s": (20, 16, 28)}), (x + 1, y + 1))
    surf.blit(sprite("cursor", 1), (x, y))


def plant_sprite_name(species, fraction):
    """Map growth progress (0.0..1.0) through shared juvenile stages to mature species art."""
    if fraction < 0.15:
        return "seed"
    if fraction < 0.45:
        return "sprout"
    if fraction < 0.75:
        return "leafy"
    return species


def pack_subs(pack):
    return {"1": pack["color"], "2": pack["dark"]}


def rect(surf, color, x, y, w, h):
    surf.fill(color, (int(x), int(y), int(w), int(h)))


def panel(surf, x, y, w, h, title=None, fill=PANEL, border=PANEL_DARK):
    rect(surf, border, x, y, w, h)
    rect(surf, fill, x + 1, y + 1, w - 2, h - 2)
    if title:
        draw_text(surf, title, x + 5, y + 4, DIM)


def bar(surf, x, y, w, h, fraction, color, back=PANEL_DARK):
    rect(surf, back, x, y, w, h)
    fraction = max(0.0, min(1.0, fraction))
    if fraction > 0:
        rect(surf, color, x, y, max(1, int(w * fraction)), h)


def dim_overlay(surf, alpha=150):
    key = (surf.get_size(), alpha)
    shade = _overlay_cache.get(key)
    if shade is None:
        shade = pygame.Surface(key[0], pygame.SRCALPHA)
        shade.fill((0, 0, 0, alpha))
        _overlay_cache[key] = shade
    surf.blit(shade, (0, 0))


class Button:
    """Clickable pixel-UI button supporting text, icons, or standalone chromeless sprites."""

    def __init__(self, x, y, w, h, label="", action=None, color=PANEL_LIGHT, text_color=TEXT,
                 icon=None, icon_scale=1, icon_subs=None, chromeless=False, hover_subs=None):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.action = action
        self.color = color
        self.text_color = text_color
        self.icon = icon
        self.icon_scale = icon_scale
        self.icon_subs = icon_subs
        self.chromeless = chromeless
        self.hover_subs = hover_subs
        self.active = False
        self.border_color = None
        self.enabled = True

    def hover(self, pos):
        return self.x <= pos[0] < self.x + self.w and self.y <= pos[1] < self.y + self.h

    def hit(self, pos):
        return self.enabled and self.hover(pos)

    def click(self, pos):
        if self.hit(pos):
            if self.action:
                self.action()
            return True
        return False

    def draw(self, surf, mouse):
        hovered = self.hover(mouse)
        if self.chromeless and self.icon:
            subs = self.hover_subs if (self.enabled and hovered and self.hover_subs) else self.icon_subs
            sp = sprite(self.icon, self.icon_scale, subs)
            ix = self.x + (self.w - sp.get_width()) // 2
            iy = self.y + (self.h - sp.get_height()) // 2
            surf.blit(sprite(self.icon, self.icon_scale, _SHADOW_SUBS), (ix + 1, iy + 1))
            surf.blit(sp, (ix, iy))
            return

        if not self.enabled:
            face, edge, ink = PANEL, PANEL_DARK, DIM
        else:
            lift = 22 if hovered else (10 if self.active else 0)
            face = tuple(min(255, c + lift) for c in self.color)
            edge = self.border_color if (self.active and self.border_color) else PANEL_DARK
            ink = self.text_color

        rect(surf, edge, self.x, self.y, self.w, self.h)
        rect(surf, face, self.x + 1, self.y + 1, self.w - 2, self.h - 3)
        rect(surf, tuple(max(0, c - 30) for c in face), self.x + 1, self.y + self.h - 3, self.w - 2, 2)

        icon_subs = (
            self.hover_subs
            if (self.enabled and (hovered or self.active) and self.hover_subs)
            else self.icon_subs
        )
        if self.icon and not self.label:
            sp = sprite(self.icon, self.icon_scale, icon_subs)
            ix = self.x + (self.w - sp.get_width()) // 2
            iy = self.y + (self.h - 2 - sp.get_height()) // 2
            surf.blit(sprite(self.icon, self.icon_scale, _SHADOW_SUBS), (ix + 1, iy + 1))
            surf.blit(sp, (ix, iy))
            return

        lines = button_lines(self.label, self.w - 6)
        text_h = len(lines) * 6 - 1
        if self.icon:
            sp = sprite(self.icon, self.icon_scale, icon_subs)
            total = sp.get_height() + 2 + text_h
            iy = self.y + max(2, (self.h - 2 - total) // 2)
            ix = self.x + (self.w - sp.get_width()) // 2
            surf.blit(sprite(self.icon, self.icon_scale, _SHADOW_SUBS), (ix + 1, iy + 1))
            surf.blit(sp, (ix, iy))
            ty = iy + sp.get_height() + 2
        else:
            ty = self.y + (self.h - 2 - text_h) // 2
        for i, line in enumerate(lines):
            draw_text(surf, line, self.x + self.w // 2, ty + i * 6, ink, align="center")


def tooltip(surf, lines, pos, width=96):
    """Draw a floating info panel anchored above-right of the cursor tip.

    Positioning the bottom-left corner at `pos` keeps the cursor arrow outside
    the text area; near the top edge, the panel flips below the cursor instead.
    """
    wrapped = []
    for text, color in lines:
        for part in wrap(text, width - 8):
            wrapped.append((part, color))
    h = len(wrapped) * 7 + 6
    x = max(2, min(pos[0], CANVAS_W - width - 2))
    y = pos[1] + 15 if pos[1] - h < 2 else pos[1] - h
    y = max(2, min(y, CANVAS_H - h - 2))
    rect(surf, PANEL_DARK, x, y, width, h)
    rect(surf, (20, 16, 32), x + 1, y + 1, width - 2, h - 2)
    for i, (part, color) in enumerate(wrapped):
        draw_text(surf, part, x + 4, y + 4 + i * 7, color)
