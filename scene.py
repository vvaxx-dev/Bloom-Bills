
from . import gfx
from .formatting import fmt
from .settings import ACCENT, BAD, DIM, PANEL, PANEL_DARK, TEXT


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


def draw_topbar(surf, run, label=None, timer=None):
    gfx.rect(surf, PANEL_DARK, 0, 0, 320, 14)
    gfx.rect(surf, PANEL, 0, 13, 320, 1)
    top = 2
    left = label or ("ROUND %d" % run.round)
    money = "$" + fmt(run.money)
    left_w = gfx.draw_text(surf, left, 5, top, TEXT)
    season = run.season()
    season_w = gfx.draw_text(surf, season["short"], 5 + left_w + 4, top, season["color"])
    timer_w = gfx.text_width(timer) + 8 if timer is not None else 0
    if timer is not None:
        gfx.draw_text(surf, timer, 315, top, TEXT, align="right")
    money_w = gfx.draw_text(surf, money, 315 - timer_w, top, ACCENT, align="right") + timer_w

    # next bill, in the middle - shorten it rather than letting a seven-figure
    # cash pile on the right run into it
    room = 320 - 2 * max(left_w + season_w + 9, money_w + 5) - 10
    qr = run.next_quota_round()
    due = "BILL DUE THIS ROUND" if run.is_quota_round(run.round) else "NEXT BILL R%d" % qr
    bill = "$" + fmt(run.bill_for_round(qr))
    color = BAD if run.is_quota_round(run.round) else DIM
    for text in (due + ": " + bill, due + " " + bill, bill):
        if gfx.text_width(text) <= room:
            break
    gfx.draw_text(surf, text, 160, top, color, align="center")
