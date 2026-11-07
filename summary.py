
import pygame

from . import gfx
from .gfx import Button
from .scene import Scene, draw_topbar
from .formatting import fmt
from .settings import ACCENT, BAD, DIM, GOOD, TEXT


class SummaryScene(Scene):
    def on_enter(self):
        summary = self.run.last_summary or {}
        pending = bool(summary.get("pending_bill"))
        if pending:
            bill = summary.get("bill", 0)
            self.pay_btn = Button(80, 148, 76, 20, "PAY $%s" % fmt(bill), self.pay_bill, color=(70, 130, 70))
            self.decline_btn = Button(164, 148, 76, 20, "DON'T PAY", self.decline_bill, color=(150, 70, 60))
            self.next_btn = None
            self.buttons = [self.pay_btn, self.decline_btn]
        else:
            self.next_btn = Button(118, 148, 84, 20, "GO TO SHOP", self.go_shop, color=(70, 130, 70))
            self.pay_btn = None
            self.decline_btn = None
            self.buttons = [self.next_btn]

    def pay_bill(self):
        ok, _ = self.run.pay_pending_bill()
        self.app.save_run()
        if ok:
            self.go_shop()

    def decline_bill(self):
        self.run.decline_bill()
        self.app.finish_run()
        self.app.goto("gameover")

    def go_shop(self):
        if self.run.pending_bill:
            return
        self.run.enter_shop()
        self.app.save_run()
        self.app.goto("shop")

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN) and not self.run.pending_bill:
            self.go_shop()

    def draw(self, surf):
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, self.run, "ROUND SUMMARY")
        summary = self.run.last_summary or {}
        gfx.draw_text(surf, "ROUND COMPLETE", 160, 42, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "EARNED: $%s" % summary.get("earned", 0), 160, 72, GOOD, align="center")
        gfx.draw_text(surf, "MONEY: $%s" % summary.get("money", self.run.money), 160, 82, TEXT, align="center")
        if summary.get("paid"):
            gfx.draw_text(surf, "BILL PAID: $%s" % summary.get("bill", 0), 160, 92, GOOD, align="center")
        elif summary.get("pending_bill"):
            gfx.draw_text(surf, "UNPAID BILL: $%s" % summary.get("bill", 0), 160, 92, BAD, align="center")
            gfx.draw_text(surf, "PAY THE BILL OR FORFEIT THE RUN", 160, 118, BAD, align="center")
        else:
            gfx.draw_text(surf, "NEXT: SHOP", 160, 118, DIM, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)
