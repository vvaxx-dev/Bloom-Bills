
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

    def update(self, _dt):
        pass

    def draw(self, _surf):
        pass

    def draw_buttons(self, surf):
        for b in self.buttons:
            b.draw(surf, self.mouse)


def draw_topbar(surf, run, label=None):
    gfx.rect(surf, PANEL_DARK, 0, 0, 320, 14)
    gfx.rect(surf, PANEL, 0, 13, 320, 1)
    left = label or ("ROUND %d" % run.round)
    money = "$" + fmt(run.money)
    left_w = gfx.draw_text(surf, left, 5, 4, TEXT)
    money_w = gfx.draw_text(surf, money, 315, 4, ACCENT, align="right")

    # next bill, in the middle - shorten it rather than letting a seven-figure
    # cash pile on the right run into it
    room = 320 - 2 * max(left_w + 5, money_w + 5) - 10
    qr = run.next_quota_round()
    due = "BILL DUE THIS ROUND" if run.is_quota_round(run.round) else "NEXT BILL R%d" % qr
    bill = "$" + fmt(run.bill_for_round(qr))
    color = BAD if run.is_quota_round(run.round) else DIM
    for text in (due + ": " + bill, due + " " + bill, bill):
        if gfx.text_width(text) <= room:
            break
    gfx.draw_text(surf, text, 160, 4, color, align="center")
