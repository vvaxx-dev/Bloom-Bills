import pygame
from . import gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BAD, DIM, GOOD, PANEL_DARK, TEXT, WATER, WIN_QUOTAS

TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": TEXT}

class SummaryScene(Scene):
    def on_enter(self):
        summary = self.run.last_summary or {}
        pending = bool(summary.get("pending_bill")) or bool(self.run.pending_bill)
        if pending:
            bill = summary.get("bill", self.run.pending_bill)
            self.pay_btn = Button(58, 150, 96, 20, "PAY $%s" % fmt(bill), self.pay_bill, color=(70, 130, 70))
            self.pay_btn.enabled = self.run.money >= bill
            self.decline_btn = Button(166, 150, 96, 20, "DON'T PAY", self.decline_clicked, color=(150, 70, 60))
            self.next_btn = None
            self.buttons = [self.pay_btn, self.decline_btn]
        else:
            self.next_btn = Button(104, 150, 112, 20, "GO TO SHOP >", self.go_shop, color=(70, 130, 70))
            self.pay_btn = None
            self.decline_btn = None
            self.buttons = [self.next_btn]

    def pay_bill(self):
        ok, _ = self.run.pay_pending_bill()
        self.app.save_run()
        if ok:
            if self.run.won:            # the last bill is paid: the run is won
                self.app.finish_run()
                self.app.goto("gameover")
                return
            self.go_shop()

    def decline_clicked(self):
        bill = self.run.pending_bill or (self.run.last_summary or {}).get("bill", 0)
        if bill and self.run.money >= bill and hasattr(self.app, "ask_confirm"):
            self.app.ask_confirm(
                "FORFEIT THIS RUN?",
                "YOU CAN AFFORD $%s! REFUSING TO PAY ENDS THE RUN." % fmt(bill),
                self.decline_bill,
                confirm_label="DON'T PAY",
                danger=True,
            )
        else:
            self.decline_bill()

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
        elif key == pygame.K_ESCAPE:
            if hasattr(self.app, "open_pause"):
                self.app.open_pause()

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run, "ROUND %d DONE" % run.round, mouse=self.mouse)
        summary = run.last_summary or {}

        # --- Left panel: Itemized Round Ledger ---
        lx, ly, lw, lh = 6, 20, 151, 124
        gfx.panel(surf, lx, ly, lw, lh, "ROUND %d BREAKDOWN" % summary.get("round", run.round),
                  fill=(38, 33, 58))
        harvest = int(summary.get("harvest", 0))
        sale = int(summary.get("sale", 0))
        interest = int(summary.get("interest", 0))
        upkeep = int(summary.get("upkeep", 0))
        rate_pct = int(round(run.interest_rate() * 100))
        net = summary.get("net", harvest + sale + interest - upkeep)

        ry = ly + 16
        gfx.draw_text(surf, "HARVESTS", lx + 6, ry, DIM)
        gfx.draw_text(surf, "+$%s" % fmt(harvest), lx + lw - 6, ry, GOOD if harvest else DIM, align="right")
        ry += 11

        gfx.draw_text(surf, "PLANT SALES", lx + 6, ry, DIM)
        gfx.draw_text(surf, "+$%s" % fmt(sale), lx + lw - 6, ry, GOOD if sale else DIM, align="right")
        ry += 11

        int_lbl = ("INTEREST (%d%%)" % rate_pct) if rate_pct else "INTEREST"
        gfx.draw_text(surf, int_lbl, lx + 6, ry, DIM)
        gfx.draw_text(surf, "+$%s" % fmt(interest), lx + lw - 6, ry, ACCENT if interest else DIM, align="right")
        ry += 11

        if upkeep > 0:
            gfx.draw_text(surf, "CURSED UPKEEP", lx + 6, ry, BAD)
            gfx.draw_text(surf, "-$%s" % fmt(upkeep), lx + lw - 6, ry, BAD, align="right")
            ry += 11

        gfx.rect(surf, PANEL_DARK, lx + 6, ry + 1, lw - 12, 1)
        ry += 6

        net_prefix = "+$" if net >= 0 else "-$"
        gfx.draw_text(surf, "NET EARNED", lx + 6, ry, TEXT)
        gfx.draw_text(surf, net_prefix + fmt(abs(net)), lx + lw - 6, ry,
                      GOOD if net >= 0 else BAD, align="right")
        ry += 12

        gfx.draw_text(surf, "TOTAL CASH", lx + 6, ry, TEXT)
        gfx.draw_text(surf, "$%s" % fmt(run.money), lx + lw - 6, ry, ACCENT, align="right")

        gfx.rect(surf, PANEL_DARK, lx + 6, ly + lh - 22, lw - 12, 1)
        gfx.draw_text(surf, "HEIRLOOMS EARNED:", lx + 6, ly + lh - 14, DIM)
        gfx.draw_text(surf, "+%d" % run.heirloom_reward(), lx + lw - 6, ly + lh - 14, ACCENT, align="right")

        # --- Right panel: Bill Status & Next Forecast ---
        rx, ry0, rw, rh = 163, 20, 151, 124
        pending = bool(summary.get("pending_bill")) or bool(run.pending_bill)
        gfx.panel(surf, rx, ry0, rw, rh,
                  "BILL COLLECTOR" if pending else "QUOTA & NEXT ROUND",
                  fill=(38, 33, 58))

        bp = run.bill_progress()
        # Quota ladder pips inside summary
        gfx.draw_text(surf, "BILLS PAID: %d / %d" % (run.quotas_paid, WIN_QUOTAS), rx + 6, ry0 + 16, TEXT)
        for k in range(WIN_QUOTAS):
            px = rx + 6 + k * 17
            pcol = GOOD if k < run.quotas_paid else ((BAD if pending else ACCENT) if k == run.quotas_paid else PANEL_DARK)
            gfx.rect(surf, pcol, px, ry0 + 25, 14, 4)

        if pending:
            bill = summary.get("bill", run.pending_bill)
            can_pay = run.money >= bill
            if self.pay_btn is not None:
                self.pay_btn.enabled = can_pay
            frac = min(1.0, run.money / max(1, bill))

            gfx.draw_text(surf, "BILL #%d DUE" % bp["quota_index"], rx + 6, ry0 + 36, BAD if not can_pay else ACCENT)
            gfx.draw_text(surf, "$%s" % fmt(bill), rx + rw - 6, ry0 + 36, BAD, align="right")

            gfx.draw_text(surf, "YOUR CASH", rx + 6, ry0 + 47, DIM)
            gfx.draw_text(surf, "$%s" % fmt(run.money), rx + rw - 6, ry0 + 47, TEXT, align="right")

            gfx.bar(surf, rx + 6, ry0 + 57, rw - 12, 6, frac, GOOD if can_pay else BAD)

            if can_pay:
                left_after = run.money - bill
                gfx.draw_text(surf, "AFTER PAYING", rx + 6, ry0 + 69, DIM)
                gfx.draw_text(surf, "$%s" % fmt(left_after), rx + rw - 6, ry0 + 69, GOOD, align="right")
                msg = ("PAY TO WIN THE FARM!" if bp["quota_index"] >= WIN_QUOTAS
                       else "QUOTA MET! PAY TO CONTINUE.")
                gfx.draw_wrapped(surf, msg, rx + 6, ry0 + 86, rw - 12, GOOD)
            else:
                short = bill - run.money
                gfx.draw_text(surf, "SHORT BY", rx + 6, ry0 + 69, BAD)
                gfx.draw_text(surf, "-$%s" % fmt(short), rx + rw - 6, ry0 + 69, BAD, align="right")
                gfx.draw_wrapped(surf, "NOT ENOUGH FOR QUOTA. PRESS DON'T PAY TO END RUN.",
                                 rx + 6, ry0 + 84, rw - 12, BAD)
            qr = bp["quota_round"]
            nbill = bp["bill"]
            frac = bp["fraction"]
            pct = min(999, int(run.money * 100 / max(1, nbill)))
            gfx.draw_text(surf, "NEXT BILL (R%d)" % qr, rx + 6, ry0 + 36, DIM)
            gfx.draw_text(surf, "$%s" % fmt(nbill), rx + rw - 6, ry0 + 36, ACCENT, align="right")
            gfx.bar(surf, rx + 6, ry0 + 46, rw - 12, 6, frac, GOOD if frac >= 1.0 else WATER)
            status_txt = ("QUOTA ALREADY MET! (%d%%)" % pct if frac >= 1.0
                          else "%d%% FUNDED ($%s TO GO)" % (pct, fmt(bp["shortfall"])))
            gfx.draw_text(surf, status_txt, rx + 6, ry0 + 56, GOOD if frac >= 1.0 else DIM)

            gfx.rect(surf, PANEL_DARK, rx + 6, ry0 + 68, rw - 12, 1)
            nxt = run.round + 1
            tw = run.twist(nxt)
            tcol = BAD if tw.get("boss") else TONE_COLORS.get(tw.get("tone", "neutral"), TEXT)
            gfx.draw_text(surf, "UP NEXT: ROUND %d" % nxt, rx + 6, ry0 + 74, TEXT)
            gfx.draw_text(surf, tw["name"].upper(), rx + 6, ry0 + 84, tcol)
            desc_lines = gfx.wrap(tw.get("short", tw["desc"]), rw - 12)
            for k, line in enumerate(desc_lines[:3]):
                gfx.draw_text(surf, line, rx + 6, ry0 + 94 + k * 7, DIM)

        for button in self.buttons:
            button.draw(surf, self.mouse)
