
from turtle import pos

import pygame

from .settings import DIM, PANEL, PANEL_DARK, PANEL_LIGHT, TEXT
from .sprites_data import FONT, GRIDS, PALETTE

_text_cache = {}
_sprite_cache = {}


def _glyph(ch):
    return FONT.get(ch, FONT["?"])


def text_width(text, scale=1):
    if not text:
        return 0
    return (sum(len(_glyph(ch)[0]) + 1 for ch in str(text).upper()) - 1) * scale


def _text_surface(text, color, scale):
    key = (text, color, scale)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) > 3000:
            _text_cache.clear()
        w = max(1, text_width(text, scale))
        surf = pygame.Surface((w, 5 * scale), pygame.SRCALPHA)
        rgba = tuple(color)[:3] + (255,)
        cursor = 0
        for ch in str(text).upper():
            glyph = _glyph(ch)
            for ry, row in enumerate(glyph):
                for rx, char in enumerate(row):
                    if char == "#":
                        surf.fill(rgba, ((cursor + rx) * scale, ry * scale, scale, scale))
            cursor += len(glyph[0]) + 1
        _text_cache[key] = surf
    return surf


def draw_text(surf, text, x, y, color=TEXT, scale=1, align="left", shadow=None):
    text = str(text)
    w = text_width(text, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    x, y = int(x), int(y)
    if shadow:
        off = max(1, scale // 3)
        surf.blit(_text_surface(text, shadow, scale), (x + off, y + off))
    surf.blit(_text_surface(text, color, scale), (x, y))
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
    for i, line in enumerate(wrap(text, max_width, scale)):
        draw_text(surf, line, x, y + i * (5 * scale + line_gap), color, scale)
    return len(wrap(text, max_width, scale))


def sprite(name, scale=1, subs=None):
    key = (name, scale, tuple(sorted(subs.items())) if subs else None)
    surf = _sprite_cache.get(key)
    if surf is None:
        grid = GRIDS.get(name) or GRIDS["unknown"]
        palette = dict(PALETTE)
        if subs:
            palette.update(subs)
        h, w = len(grid), len(grid[0])
        surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
        for y, row in enumerate(grid):
            for x, char in enumerate(row):
                if char != ".":
                    surf.fill(tuple(palette[char]) + (255,), (x * scale, y * scale, scale, scale))
        _sprite_cache[key] = surf
    return surf


def draw_sprite(surf, name, x, y, scale=1, subs=None):
    surf.blit(sprite(name, scale, subs), (int(x), int(y)))

def draw_cursor(surf, pos):
    """The mouse pointer, drawn in the same 1px chunks as the font. Its tip
    is the hotspot, so it lands exactly where a click does."""
    surf.blit(sprite("cursor"), (int(pos[0]), int(pos[1])))

def plant_sprite_name(species, fraction):
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
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, alpha))
    surf.blit(shade, (0, 0))


class Button:
    def __init__(self, x, y, w, h, label, action=None, color=PANEL_LIGHT, text_color=TEXT):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.label = label
        self.action = action
        self.color = color
        self.text_color = text_color
        self.enabled = True

    def hit(self, pos):
        return self.enabled and self.x <= pos[0] < self.x + self.w and self.y <= pos[1] < self.y + self.h

    def hover(self, pos):
        return self.x <= pos[0] < self.x + self.w and self.y <= pos[1] < self.y + self.h

    def click(self, pos):
        if self.hit(pos):
            if self.action:
                self.action()
            return True
        return False

    def draw(self, surf, mouse):
        if not self.enabled:
            face, edge, ink = PANEL, PANEL_DARK, DIM
        else:
            lift = 22 if self.hover(mouse) else 0
            face = tuple(min(255, c + lift) for c in self.color)
            edge = PANEL_DARK
            ink = self.text_color
        rect(surf, edge, self.x, self.y, self.w, self.h)
        rect(surf, face, self.x + 1, self.y + 1, self.w - 2, self.h - 3)
        rect(surf, tuple(max(0, c - 30) for c in face), self.x + 1, self.y + self.h - 3, self.w - 2, 2)
        lines = wrap(self.label, self.w - 6)
        total = len(lines) * 6 - 1
        ty = self.y + (self.h - 2 - total) // 2
        for i, line in enumerate(lines):
            draw_text(surf, line, self.x + self.w // 2, ty + i * 6, ink, align="center")


def tooltip(surf, lines, pos, width=96):
    """Panel whose top-left corner sits right on the pixel cursor's tip, so
    the pointer always marks the corner of the box it opened."""
    wrapped = []
    for text, color in lines:
        for part in wrap(text, width - 8):
            wrapped.append((part, color))
    h = len(wrapped) * 7 + 6
    x = max(2, min(pos[0], 320 - width - 2))
    y = max(2, min(pos[1], 180 - h - 2))
    rect(surf, PANEL_DARK, x, y, width, h)
    rect(surf, (20, 16, 32), x + 1, y + 1, width - 2, h - 2)
    for i, (part, color) in enumerate(wrapped):
        draw_text(surf, part, x + 4, y + 4 + i * 7, color)
