from . import gfx
from .formatting import fmt
from .settings import ACCENT, BAD, DIM, PANEL, PANEL_DARK, PANEL_LIGHT, TEXT

TOPBAR_PAUSE_RECT = (296, 0, 24, 14)


def draw_topbar_tooltip(surf, run, mouse):
    if not (TOPBAR_PAUSE_RECT[0] <= mouse[0] < TOPBAR_PAUSE_RECT[0] + TOPBAR_PAUSE_RECT[2]
            and TOPBAR_PAUSE_RECT[1] <= mouse[1] < TOPBAR_PAUSE_RECT[1] + TOPBAR_PAUSE_RECT[3]):
        return
    gfx.tooltip(surf, [("PAUSE", ACCENT)], mouse, 72)


class Scene:
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
        """Mouse wheel: scenes that scroll a list page through it."""
        return False

    def update(self, _dt):
        pass

    def draw(self, _surf):
        pass

    def draw_buttons(self, surf):
        for b in self.buttons:
            b.draw(surf, self.mouse)


def draw_topbar(surf, run, label=None, timer=None, mouse=None):
    gfx.rect(surf, PANEL_DARK, 0, 0, 320, 14)
    gfx.rect(surf, PANEL, 0, 13, 320, 1)
    top = 2
    left = label or ("ROUND %d" % run.round)
    money = "$" + fmt(run.money)
    left_w = gfx.draw_text(surf, left, 5, top, TEXT)
    season = run.season()
    season_w = gfx.draw_text(surf, season["short"], 5 + left_w + 4, top, season["color"])
    right_x = TOPBAR_PAUSE_RECT[0] - 2
    timer_w = gfx.text_width(timer) + 8 if timer is not None else 0
    if timer is not None:
        gfx.draw_text(surf, timer, 315, top, TEXT, align="right")
    money_w = gfx.draw_text(surf, money, 315 - timer_w, top, ACCENT, align="right") + timer_w

    # next bill, in the middle - shorten it rather than letting a seven-figure
    # cash pile on the right run into it
    left_end = 5 + left_w + 4 + season_w
    right_start = right_x - money_w
    room = 2 * min(160 - left_end - 4, right_start - 160 - 4)
    bp = run.bill_progress()
    qr = bp["quota_round"]
    due = "BILL DUE THIS ROUND" if bp["due_now"] else "NEXT BILL R%d" % qr
    bill = "$" + fmt(bp["bill"])
    color = BAD if bp["due_now"] else DIM
    for text in (due + ": " + bill, due + " " + bill, bill):
        if gfx.text_width(text) <= room:
            break
    gfx.draw_text(surf, text, 160, top, color, align="center")

    # pause indicator
    pause_x, pause_y, pause_w, pause_h = TOPBAR_PAUSE_RECT
    hover = mouse is not None and pause_x <= mouse[0] < pause_x + pause_w and pause_y <= mouse[1] < pause_y + pause_h
    border = ACCENT if hover else PANEL_LIGHT
    fill = PANEL_LIGHT if hover else PANEL
    bar_col = ACCENT if hover else TEXT
    gfx.rect(surf, border, 300, 2, 16, 10)
    gfx.rect(surf, fill, 301, 3, 14, 8)
    gfx.rect(surf, bar_col, 305, 4, 2, 6)
    gfx.rect(surf, bar_col, 309, 4, 2, 6)
