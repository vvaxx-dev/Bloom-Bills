"""The shop between rounds: relics, extra plots and rerolls."""

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BAD, DIM, GOOD, MAX_PLOTS, PANEL_DARK, RELIC_SLOTS, TEXT


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
            b = Button(4 + i * 62 + 2, 141, 56, 8, "", lambda i=i: self.sell_relic(i), color=(150, 70, 60))
            b.enabled = False
            self.sell_buttons.append(b)
        self.plot_btn = Button(4, 150, 88, 26, "", self.buy_plot)
        self.reroll_btn = Button(96, 150, 64, 26, "", self.reroll)
        self.next_btn = Button(258, 150, 58, 26, "NEXT ROUND >", self.go, color=(70, 130, 70))
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
            self.plot_btn.label, self.plot_btn.enabled = "PLOTS MAXED", False
        else:
            self.plot_btn.label = "BUY PLOT $%s (%d/%d)" % (fmt(run.plot_price()), len(run.plots), MAX_PLOTS)
            self.plot_btn.enabled = run.money >= run.plot_price()
        self.reroll_btn.label = "REROLL $" + fmt(run.reroll_price())
        self.reroll_btn.enabled = run.money >= run.reroll_price()

    def on_click(self, pos):
        return super().on_click(pos)

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
            self.app.goto("title")

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run, "SHOP")

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
        gfx.draw_text(surf, "YOUR RELICS %d/%d" % (len(run.relics), RELIC_SLOTS), 6, 120, DIM)
        if self.msg:
            gfx.draw_text(surf, self.msg, 314, 120, ACCENT, align="right")
        owned_hover = None
        for i in range(RELIC_SLOTS):
            x = 4 + i * 62
            gfx.rect(surf, PANEL_DARK, x, 126, 60, 24)
            if i < len(run.relics):
                rel = data.RELICS[run.relics[i]]
                gfx.rect(surf, data.RARITY_COLORS[rel["rarity"]], x, 126, 60, 1)
                lines = gfx.wrap(rel["name"], 54)
                for k, line in enumerate(lines[:2]):
                    gfx.draw_text(surf, line, x + 30, 129 + k * 7, TEXT, align="center")
                self.sell_buttons[i].draw(surf, self.mouse)
                if x <= self.mouse[0] < x + 60 and 126 <= self.mouse[1] < 150:
                    owned_hover = i
            else:
                gfx.draw_text(surf, "EMPTY", x + 30, 135, (70, 62, 96), align="center")

        # bottom strip
        gfx.panel(surf, 164, 150, 90, 26)
        nxt = run.round + 1
        twist = run.twist(nxt)
        gfx.draw_text(surf, "NEXT: ROUND %d" % nxt, 168, 154, TEXT)
        if run.is_quota_round(nxt):
            gfx.draw_text(surf, "BILL $" + fmt(run.bill_for_round(nxt)), 168, 161, BAD)
            gfx.draw_text(surf, twist["name"].upper(), 168, 168, ACCENT)
        else:
            gfx.draw_text(surf, "NO BILL", 168, 161, GOOD)
        self.plot_btn.draw(surf, self.mouse)
        self.reroll_btn.draw(surf, self.mouse)
        self.next_btn.draw(surf, self.mouse)

        # hover: show a quota twist description
        if 164 <= self.mouse[0] < 254 and 150 <= self.mouse[1] < 176 and run.is_quota_round(nxt):
            gfx.tooltip(surf, [(twist["name"], ACCENT), (twist["desc"], TEXT)], (self.mouse[0] - 60, self.mouse[1] - 36), 100)
        if owned_hover is not None:
            rel = data.RELICS[run.relics[owned_hover]]
            col = data.RARITY_COLORS[rel["rarity"]]
            refund = max(1, int(run.relic_price(run.relics[owned_hover]) * 0.5))
            gfx.tooltip(surf, [
                (rel["name"], col),
                (rel["rarity"].upper(), col),
                (rel["desc"], TEXT),
                ("SELL REFUND: $%s" % fmt(refund), ACCENT),
            ], (self.mouse[0] - 40, self.mouse[1] - 30), 110)