"""The shop between rounds: relics, extra plots and rerolls."""

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BAD, DIM, GOOD, MAX_PLOTS, PANEL_DARK, RELIC_SLOTS, TEXT

FORECAST_RECT = (152, 150, 98, 26)
TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": TEXT}


class ShopScene(Scene):
    def on_enter(self):
        self.run.phase = "shop"
        self.msg = ""
        self.buy_buttons = []
        for i in range(3):
            b = Button(9 + i * 104, 98, 90, 16, "", lambda i=i: self.buy_relic(i), color=(70, 130, 70))
            self.buy_buttons.append(b)
        self.sell_buttons = []
        for i in range(RELIC_SLOTS):
            b = Button(4 + i * 62 + 2, 141, 56, 8, "", lambda i=i: self.sell_relic_clicked(i), color=(150, 70, 60))
            b.enabled = False
            self.sell_buttons.append(b)
        self.plot_btn = Button(4, 150, 88, 26, "", self.buy_plot)
        self.reroll_btn = Button(95, 150, 54, 26, "", self.reroll)
        self.next_btn = Button(253, 150, 63, 26, "NEXT\nROUND >", self.go, color=(70, 130, 70))
        self.buttons = self.buy_buttons + self.sell_buttons + [self.plot_btn, self.reroll_btn, self.next_btn]
        self.refresh()

    def refresh(self):
        run = self.run
        for i, b in enumerate(self.buy_buttons):
            rid = run.shop_offers[i] if i < len(run.shop_offers) else None
            if rid is None:
                b.label, b.enabled = "SOLD", False
            else:
                price = run.relic_price(rid)
                b.label = "BUY $" + fmt(price)
                b.enabled = run.money >= price and len(run.relics) < RELIC_SLOTS
        for i, b in enumerate(self.sell_buttons):
            if i < len(run.relics):
                refund = max(1, int(run.relic_price(run.relics[i]) * 0.5))
                b.label, b.enabled = "SELL $" + fmt(refund), True
            else:
                b.label, b.enabled = "", False
        if len(run.plots) >= MAX_PLOTS:
            self.plot_btn.label, self.plot_btn.enabled = "PLOTS\nMAXED", False
        else:
            self.plot_btn.label = "PLOT (%d/%d)\n$%s" % (len(run.plots), MAX_PLOTS, fmt(run.plot_price()))
            self.plot_btn.enabled = run.money >= run.plot_price()
        self.reroll_btn.label = "REROLL\n$" + fmt(run.reroll_price())
        self.reroll_btn.enabled = run.money >= run.reroll_price()

    def on_click(self, pos):
        return super().on_click(pos)

    def sell_relic_clicked(self, i):
        if not 0 <= i < len(self.run.relics):
            return
        rid = self.run.relics[i]
        rel = data.RELICS[rid]
        refund = max(1, int(self.run.relic_price(rid) * 0.5))
        if hasattr(self.app, "ask_confirm"):
            self.app.ask_confirm(
                "SELL %s?" % rel["name"].upper(),
                "SELL FOR $%s? THIS CANNOT BE UNDONE." % fmt(refund),
                lambda idx=i: self.sell_relic(idx),
                confirm_label="SELL",
                danger=True,
            )
        else:
            self.sell_relic(i)

    def sell_relic(self, i):
        ok, msg, _ = self.run.sell_relic(i)
        self.msg = msg
        if ok:
            self.app.save_run()
        self.refresh()

    def buy_relic(self, i):
        ok, msg = self.run.buy_relic(i)
        self.msg = msg
        if ok:
            self.app.save_run()
        self.refresh()

    def buy_plot(self):
        if self.run.buy_plot():
            self.msg = "NEW PLOT!"
            self.app.save_run()
        self.refresh()

    def reroll(self):
        if self.run.reroll():
            self.msg = "FRESH STOCK."
            self.app.save_run()
        self.refresh()

    def go(self):
        self.run.start_next_round()
        self.app.save_run()
        self.app.goto("packs")

    def on_key(self, key):
        import pygame
        if key == pygame.K_ESCAPE:
            if hasattr(self.app, "open_pause"):
                self.app.open_pause()
            else:
                self.app.goto("title")

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run, "SHOP", mouse=self.mouse)

        for i in range(3):
            x, y = 4 + i * 104, 18
            rid = run.shop_offers[i] if i < len(run.shop_offers) else None
            if rid is None:
                gfx.panel(surf, x, y, 100, 98, fill=(36, 31, 56))
                gfx.draw_text(surf, "SOLD OUT", x + 50, y + 44, DIM, align="center")
                continue
            rel = data.RELICS[rid]
            col = data.RARITY_COLORS[rel["rarity"]]
            gfx.rect(surf, col, x, y, 100, 98)
            gfx.rect(surf, (44, 38, 66), x + 1, y + 1, 98, 96)
            gfx.rect(surf, col, x + 5, y + 5, 16, 16)
            gfx.draw_text(surf, rel["name"][0], x + 13, y + 10, PANEL_DARK, scale=1, align="center")
            gfx.draw_text(surf, rel["name"], x + 26, y + 6, TEXT)
            gfx.draw_text(surf, rel["rarity"], x + 26, y + 14, col)
            gfx.draw_wrapped(surf, rel["desc"], x + 6, y + 28, 90, TEXT)
        for b in self.buy_buttons:
            b.draw(surf, self.mouse)

        # owned relics
        gfx.draw_text(surf, "YOUR RELICS %d/%d" % (len(run.relics), RELIC_SLOTS), 6, 119, DIM)
        if self.msg:
            gfx.draw_text(surf, self.msg, 314, 119, ACCENT, align="right")
        owned_hover = None
        for i in range(RELIC_SLOTS):
            x = 4 + i * 62
            gfx.rect(surf, PANEL_DARK, x, 125, 60, 24)
            if i < len(run.relics):
                rel = data.RELICS[run.relics[i]]
                gfx.rect(surf, data.RARITY_COLORS[rel["rarity"]], x, 125, 60, 1)
                lines = gfx.wrap(rel["name"], 54)
                for k, line in enumerate(lines[:2]):
                    gfx.draw_text(surf, line, x + 30, 128 + k * 7, TEXT, align="center")
                self.sell_buttons[i].draw(surf, self.mouse)
                if x <= self.mouse[0] < x + 60 and 125 <= self.mouse[1] < 149:
                    owned_hover = i
            else:
                gfx.draw_text(surf, "EMPTY", x + 30, 134, (70, 62, 96), align="center")

        # Next round weather & bill forecast panel (never obscured by buttons)
        fx, fy, fw, fh = FORECAST_RECT
        nxt = run.round + 1
        twist = run.twist(nxt)
        season = run.season(nxt)
        tcol = BAD if twist.get("boss") else TONE_COLORS.get(twist.get("tone", "neutral"), TEXT)
        gfx.panel(surf, fx, fy, fw, fh, fill=(38, 33, 58))
        gfx.rect(surf, tcol, fx, fy, 2, fh)
        gfx.draw_text(surf, "R%d" % nxt, fx + 5, fy + 3, TEXT)
        gfx.draw_text(surf, season["short"], fx + 24, fy + 3, season["color"])
        if run.is_quota_round(nxt):
            gfx.draw_text(surf, "$" + fmt(run.bill_for_round(nxt)), fx + fw - 4, fy + 3, BAD, align="right")
        else:
            gfx.draw_text(surf, "NO BILL", fx + fw - 4, fy + 3, GOOD, align="right")

        wname = twist["name"].upper()
        while len(wname) > 1 and gfx.text_width(wname) > fw - 8:
            wname = wname[:-1]
        gfx.draw_text(surf, wname, fx + 5, fy + 11, tcol)
        sub = "BOSS!" if twist.get("boss") else ("HOVER INFO" if twist["name"] != "Fair Weather" else "CALM SKIES")
        gfx.draw_text(surf, sub, fx + 5, fy + 18, DIM)

        self.plot_btn.draw(surf, self.mouse)
        self.reroll_btn.draw(surf, self.mouse)
        self.next_btn.draw(surf, self.mouse)

        # Hover tooltips
        if fx <= self.mouse[0] < fx + fw and fy <= self.mouse[1] < fy + fh:
            bill_line = (("BILL DUE: $%s" % fmt(run.bill_for_round(nxt)), BAD)
                         if run.is_quota_round(nxt) else ("NO BILL DUE", GOOD))
            gfx.tooltip(surf, [
                ("NEXT: ROUND %d (%s)" % (nxt, season["name"].upper()), ACCENT),
                ("WEATHER: " + twist["name"].upper(), tcol),
                (twist["desc"], TEXT),
                bill_line,
            ], self.mouse, 118)
        elif owned_hover is not None:
            rel = data.RELICS[run.relics[owned_hover]]
            col = data.RARITY_COLORS[rel["rarity"]]
            refund = max(1, int(run.relic_price(run.relics[owned_hover]) * 0.5))
            gfx.tooltip(surf, [
                (rel["name"], col),
                (rel["rarity"].upper(), col),
                (rel["desc"], TEXT),
                ("SELL REFUND: $%s" % fmt(refund), ACCENT),
            ], self.mouse, 110)