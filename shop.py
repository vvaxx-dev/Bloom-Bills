"""Between-round shop: relic offers, relic resale, plot expansion, rerolls, and forecast."""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BAD, BG, CANVAS_H, CANVAS_W, DIM, GOOD, MAX_PLOTS, PANEL, PANEL_DARK, TEXT

FORECAST_RECT = (152, 150, 98, 26)
TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": TEXT}


class ShopScene(Scene):
    def on_enter(self):
        self.run.phase = "shop"
        self.msg = ""
        self.buy_buttons = [
            Button(9 + i * (104 if self.run.relic_offer_slots() == 3 else 78), 98, (90 if self.run.relic_offer_slots() == 3 else 68), 16, "", lambda i=i: self.buy_relic(i), color=(70, 130, 70))
            for i in range(self.run.relic_offer_slots())
        ]
        self.sell_buttons = []
        for i in range(self.run.relic_slots()):
            b = Button(6 + i * (62 if self.run.relic_slots() == 5 else 52), 141, (56 if self.run.relic_slots() == 5 else 46), 8, "", lambda i=i: self.sell_relic_clicked(i), color=(150, 70, 60))
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
                b.enabled = run.money >= price and len(run.relics) < run.relic_slots()
        for i, b in enumerate(self.sell_buttons):
            if i < len(run.relics):
                refund = max(1, int(run.relic_price(run.relics[i]) * 0.5))
                b.label, b.enabled = "SELL $" + fmt(refund), True
            else:
                b.label, b.enabled = "", False
        if len(run.plots) >= MAX_PLOTS:
            self.plot_btn.label, self.plot_btn.enabled = "PLOTS\nMAXED", False
        else:
            plot_price = run.plot_price()
            self.plot_btn.label = "PLOT (%d/%d)\n$%s" % (len(run.plots), MAX_PLOTS, fmt(plot_price))
            self.plot_btn.enabled = run.money >= plot_price
        reroll_price = run.reroll_price()
        self.reroll_btn.label = "REROLL\n$" + fmt(reroll_price)
        self.reroll_btn.enabled = run.money >= reroll_price

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
        if key == pygame.K_ESCAPE:
            if hasattr(self.app, "open_pause"):
                self.app.open_pause()
            else:
                self.app.goto("title")

    def _relic_tooltip_lines(self, rid, extra_lines=()):
        rel = data.RELICS[rid]
        col = data.RARITY_COLORS[rel["rarity"]]
        lv = self.run.relic_level(rid)
        lines = [
            (rel["name"] + (" +%d" % lv if lv else ""), col),
            (rel["rarity"].upper(), col),
            (rel["desc"], TEXT),
        ]
        for step in rel.get("levels", [])[:lv]:
            lines.append((step["desc"], GOOD))
        for step in rel.get("levels", [])[lv:]:
            lines.append(("EVOLVES AT %d %sS" % (step["goal"], step["stat"].upper()), DIM))
        lines.extend(extra_lines)
        return lines

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, BG, 0, 0, CANVAS_W, CANVAS_H)
        draw_topbar(surf, run, "SHOP", mouse=self.mouse)

        offer_hover = None
        card_w = 100 if run.relic_offer_slots() == 3 else 74
        card_step = 104 if run.relic_offer_slots() == 3 else 78
        for i in range(run.relic_offer_slots()):
            x, y = 4 + i * card_step, 18
            rid = run.shop_offers[i] if i < len(run.shop_offers) else None
            if rid is None:
                gfx.panel(surf, x, y, card_w, 98, fill=(36, 31, 56))
                gfx.draw_text(surf, "SOLD OUT", x + card_w // 2, y + 44, DIM, align="center")
                continue
            rel = data.RELICS[rid]
            col = data.RARITY_COLORS[rel["rarity"]]
            gfx.rect(surf, col, x, y, card_w, 98)
            gfx.rect(surf, PANEL, x + 1, y + 1, card_w - 2, 96)
            gfx.rect(surf, col, x + 5, y + 5, 16, 16)
            gfx.rect(surf, PANEL_DARK, x + 6, y + 6, 14, 14)
            gfx.draw_sprite(surf, rid, x + 7, y + 7)
            name = rel["name"]
            while len(name) > 1 and gfx.text_width(name) > card_w - 27:
                name = name[:-1]
            gfx.draw_text(surf, name, x + 25, y + 6, TEXT)
            gfx.draw_text(surf, rel["rarity"], x + 25, y + 14, col)
            for line_no, line in enumerate(gfx.wrap(rel["desc"], card_w - 12)[:7]):
                gfx.draw_text(surf, line, x + 6, y + 26 + line_no * 7, TEXT)
            if gfx.inside(self.mouse, (x, y, card_w, 78)):
                offer_hover = rid
        for b in self.buy_buttons:
            b.draw(surf, self.mouse)

        gfx.draw_text(surf, "YOUR RELICS %d/%d" % (len(run.relics), run.relic_slots()), 6, 119, DIM)
        if self.msg:
            gfx.draw_text(surf, self.msg, 314, 119, ACCENT, align="right")

        owned_hover = None
        slot_w = 60 if run.relic_slots() == 5 else 50
        for i in range(run.relic_slots()):
            x = 4 + i * (slot_w + 2)
            slot_rect = (x, 125, slot_w, 24)
            gfx.rect(surf, PANEL_DARK, *slot_rect)
            if i < len(run.relics):
                rel = data.RELICS[run.relics[i]]
                gfx.rect(surf, data.RARITY_COLORS[rel["rarity"]], x, 125, slot_w, 1)
                lines = gfx.wrap(rel["name"], slot_w - 6)
                for k, line in enumerate(lines[:2]):
                    gfx.draw_text(surf, line, x + slot_w // 2, 128 + k * 7, TEXT, align="center")
                self.sell_buttons[i].draw(surf, self.mouse)
                if gfx.inside(self.mouse, slot_rect):
                    owned_hover = i
            else:
                gfx.draw_text(surf, "EMPTY", x + slot_w // 2, 134, (70, 62, 96), align="center")

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

        if gfx.inside(self.mouse, FORECAST_RECT):
            bill_line = (
                ("BILL DUE: $%s" % fmt(run.bill_for_round(nxt)), BAD)
                if run.is_quota_round(nxt) else ("NO BILL DUE", GOOD)
            )
            gfx.tooltip(surf, [
                ("NEXT: ROUND %d (%s)" % (nxt, season["name"].upper()), ACCENT),
                ("WEATHER: " + twist["name"].upper(), tcol),
                (twist["desc"], TEXT),
                bill_line,
            ], self.mouse, 118)
        elif owned_hover is not None:
            rid = run.relics[owned_hover]
            refund = max(1, int(run.relic_price(rid) * 0.5))
            gfx.tooltip(
                surf,
                self._relic_tooltip_lines(rid, [("SELL REFUND: $%s" % fmt(refund), ACCENT)]),
                self.mouse, 110,
            )
        elif offer_hover is not None:
            gfx.tooltip(surf, self._relic_tooltip_lines(offer_hover), self.mouse, 110)
