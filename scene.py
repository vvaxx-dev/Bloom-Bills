"""Base scene interface and the shared run topbar (round, season, next bill, cash, timer, pause)."""

from . import gfx
from .formatting import fmt
from .settings import ACCENT, BAD, CANVAS_W, DIM, PANEL, PANEL_DARK, PANEL_LIGHT, TEXT

TOPBAR_PAUSE_RECT = (296, 0, 24, 14)


def draw_topbar_tooltip(surf, mouse):
    if gfx.inside(mouse, TOPBAR_PAUSE_RECT):
        gfx.tooltip(surf, [("PAUSE", ACCENT)], mouse, 72)


class Scene:
    """Lifecycle and input base class for all full-screen UI states."""

    def __init__(self, app):
        self.app = app
        self.buttons = []

    @property
    def run(self):
        return self.app.run

    @property
    def mouse(self):
        return self.app.mouse

    def on_enter(self):
        pass

    def on_click(self, pos):
        for b in self.buttons:
            if b.click(pos):
                return True
        return False

    def on_key(self, _key):
        pass

    def on_wheel(self, _dy):
        return False

    def update(self, _dt):
        pass

    def draw(self, _surf):
        pass

    def draw_buttons(self, surf):
        for b in self.buttons:
            b.draw(surf, self.mouse)


def draw_topbar(surf, run, label=None, timer=None, mouse=None):
    """Draw the 14px status bar, compacting the centered bill readout if cash or timer grows wide."""
    gfx.rect(surf, PANEL_DARK, 0, 0, CANVAS_W, 14)
    gfx.rect(surf, PANEL, 0, 13, CANVAS_W, 1)
    top = 2
    left = label or ("ROUND %d" % run.round)
    money = "$" + fmt(run.money)
    left_w = gfx.draw_text(surf, left, 5, top, TEXT)
    season = run.season()
    season_x = 5 + left_w + 3
    season_art = season.get("art")
    art_w = 0
    if season_art:
        icon = gfx.sprite(season_art)
        art_w = icon.get_width() + 2
        surf.blit(icon, (season_x, max(1, (14 - icon.get_height()) // 2)))
    season_w = gfx.draw_text(surf, season["short"], season_x + art_w, top, season["color"])

    right_x = TOPBAR_PAUSE_RECT[0] - 2
    timer_slot_w = max(
        gfx.text_width("0:00") + 8,
        gfx.text_width(timer) + 8 if timer is not None else 0,
    )
    if timer is not None:
        gfx.draw_text(surf, timer, right_x, top, TEXT, align="right")
    money_x = right_x - timer_slot_w
    money_w = gfx.draw_text(surf, money, money_x, top, ACCENT, align="right")

    left_end = season_x + art_w + season_w
    right_start = money_x - money_w
    center_x = CANVAS_W // 2
    room = 2 * min(center_x - left_end - 4, right_start - center_x - 4)
    bp = run.bill_progress()
    due = "BILL DUE THIS ROUND" if bp["due_now"] else "NEXT BILL R%d" % bp["quota_round"]
    bill = "$" + fmt(bp["bill"])
    color = BAD if bp["due_now"] else DIM
    for text in (due + ": " + bill, due + " " + bill, bill):
        if gfx.text_width(text) <= room:
            break
    gfx.draw_text(surf, text, center_x, top, color, align="center")

    hover = mouse is not None and gfx.inside(mouse, TOPBAR_PAUSE_RECT)
    border = ACCENT if hover else PANEL_LIGHT
    fill = PANEL_LIGHT if hover else PANEL
    bar_col = ACCENT if hover else TEXT
    gfx.rect(surf, border, 300, 2, 16, 10)
    gfx.rect(surf, fill, 301, 3, 14, 8)
    gfx.rect(surf, bar_col, 305, 4, 2, 6)
    gfx.rect(surf, bar_col, 309, 4, 2, 6)
