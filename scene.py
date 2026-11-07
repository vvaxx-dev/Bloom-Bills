
from . import data, gfx
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

    def on_key(self, key):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def draw_buttons(self, surf):
        for b in self.buttons:
            b.draw(surf, self.mouse)


def draw_topbar(surf, run, label=None):
    gfx.rect(surf, PANEL_DARK, 0, 0, 320, 14)
    gfx.rect(surf, PANEL, 0, 13, 320, 1)
    gfx.draw_text(surf, label or ("ROUND %d" % run.round), 5, 4, TEXT)
    gfx.draw_text(surf, "$" + fmt(run.money), 315, 4, ACCENT, align="right")
    # next bill, in the middle
    qr = run.next_quota_round()
    bill = fmt(run.bill_for_round(qr))
    if run.is_quota_round(run.round):
        text = "BILL DUE THIS ROUND: $" + bill
        color = BAD
    else:
        text = "NEXT BILL: ROUND %d, $%s" % (qr, bill)
        color = DIM
    gfx.draw_text(surf, text, 160, 4, color, align="center")
