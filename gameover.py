"""End-of-run summary screen and the permanent Heirloom Shelf upgrade shop."""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, BG, CANVAS_H, CANVAS_W, DIM, GOOD, PANEL_DARK, TEXT


class GameOverScene(Scene):
    def on_enter(self):
        self.shelf_btn = Button(100, 114, 120, 16, "HEIRLOOM SHELF", lambda: self.app.goto("shelf"), color=(96, 70, 140))
        self.new_btn = Button(100, 134, 120, 16, "NEW RUN", self.app.new_run, color=(70, 130, 70))
        self.title_btn = Button(100, 154, 120, 16, "BACK TO TITLE", lambda: self.app.goto("title"), color=(130, 70, 70))
        self.buttons = [self.shelf_btn, self.new_btn, self.title_btn]

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            self.app.goto("title")
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self.app.new_run()

    def draw(self, surf):
        gfx.rect(surf, (30, 22, 36), 0, 0, CANVAS_W, CANVAS_H)
        result = self.app.last_result or {}
        won = bool(result.get("won"))
        headline = "THE FARM IS YOURS" if won else "THE BILL COLLECTOR CAME"
        gfx.draw_text(surf, headline, 160, 14, GOOD if won else ACCENT, scale=2, align="center")
        gfx.draw_text(
            surf,
            "ROUNDS: %s   BILLS PAID: %s" % (result.get("round", 0), result.get("quotas_paid", 0)),
            160, 40, TEXT, align="center",
        )
        gfx.draw_text(surf, "EARNED: $%s" % fmt(result.get("total_earned", 0)), 160, 51, TEXT, align="center")
        if won:
            gfx.draw_text(surf, "EVERY BILL PAID. THE BILL COLLECTOR GIVES UP.", 160, 64, GOOD, align="center")
        elif result.get("new_best"):
            gfx.draw_text(surf, "NEW BEST ROUND!", 160, 64, ACCENT, align="center")
        else:
            gfx.draw_text(surf, "BEST ROUND: %d" % self.app.profile["best_round"], 160, 64, DIM, align="center")

        gfx.rect(surf, PANEL_DARK, 50, 78, 220, 1)
        gfx.draw_text(surf, "HEIRLOOMS EARNED THIS RUN", 160, 82, DIM, align="center")
        gfx.draw_text(surf, "+%d" % result.get("heirlooms", 0), 160, 91, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "BANKED: %d" % self.app.profile["heirlooms"], 160, 105, GOOD, align="center")
        self.draw_buttons(surf)


class ShelfScene(Scene):
    """Meta-progression shop spending banked heirlooms on permanent run perks."""

    ROW_Y = 27
    ROW_H = 23

    def on_enter(self):
        self.msg = ""
        self.buy_buttons = []
        for i, key in enumerate(data.PERK_ORDER):
            b = Button(
                214, self.ROW_Y + i * self.ROW_H + 1, 100, 20, "",
                lambda k=key: self.buy(k), color=(70, 130, 70),
            )
            b.key = key
            self.buy_buttons.append(b)
        self.back_btn = Button(126, 156, 68, 18, "BACK", lambda: self.app.goto("title"), color=(70, 130, 70))
        self.buttons = self.buy_buttons + [self.back_btn]
        self.refresh()

    def profile_level(self, key):
        return int(self.app.profile["perks"].get(key, 0))

    def level(self, key):
        return self.run.perk(key) if self.run else self.profile_level(key)

    def cost(self, key):
        return data.perk_cost(key, self.level(key))

    def refresh(self):
        banked = self.app.profile["heirlooms"]
        for b in self.buy_buttons:
            perk = data.PERKS[b.key]
            level = self.level(b.key)
            if level >= perk["max"]:
                b.label, b.enabled = "MAXED", False
            else:
                price = self.cost(b.key)
                b.label = "BUY %d" % price
                b.enabled = banked >= price

    def buy(self, key):
        if self.run:
            ok, msg, cost = self.run.buy_heirloom(key, self.app.profile["heirlooms"])
        else:
            ok, msg, cost = self._buy_on_profile(key)
        self.msg = msg.upper()
        if ok:
            bank = self.app.profile
            bank["heirlooms"] = max(0, bank["heirlooms"] - cost)
            if self.run:
                bank["perks"] = dict(self.run.perks)
                self.app.save_run()
            self.app.saves.save_profile(bank)
        self.refresh()

    def _buy_on_profile(self, key):
        perk = data.PERKS[key]
        level = self.profile_level(key)
        if level >= perk["max"]:
            return False, "Already maxed.", 0
        cost = self.cost(key)
        if self.app.profile["heirlooms"] < cost:
            return False, "Not enough heirlooms.", cost
        self.app.profile["perks"] = dict(self.app.profile["perks"], **{key: level + 1})
        return True, "%s is level %d!" % (perk["name"], level + 1), cost

    def on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.goto("title")

    def draw(self, surf):
        gfx.rect(surf, BG, 0, 0, CANVAS_W, CANVAS_H)
        gfx.draw_text(surf, "HEIRLOOM SHELF", 6, 4, ACCENT, scale=2)
        gfx.draw_text(surf, "BANKED: %d" % self.app.profile["heirlooms"], 314, 5, ACCENT, align="right")
        gfx.draw_text(surf, "PERMANENT. THEY COME WITH YOU INTO EVERY RUN.", 6, 19, DIM)
        if self.msg:
            gfx.draw_text(surf, self.msg, 314, 19, GOOD, align="right")

        for i, key in enumerate(data.PERK_ORDER):
            self.draw_row(surf, i, key, self.ROW_Y + i * self.ROW_H)

        gfx.draw_text(surf, "EARN MORE: +1 FOR EVERY ROUND SURVIVED, +3 FOR EVERY BILL PAID.", 6, 145, DIM)
        self.back_btn.draw(surf, self.mouse)

    def draw_row(self, surf, idx, key, y):
        perk = data.PERKS[key]
        level = self.level(key)
        owned = level > 0
        gfx.panel(surf, 4, y, 312, 23, fill=(38, 33, 58))
        gfx.rect(surf, GOOD if owned else (66, 58, 92), 4, y, 2, 23)
        gfx.draw_text(surf, perk["name"], 12, y + 3, TEXT)
        gfx.draw_text(surf, "%d/%d" % (level, perk["max"]), 206, y + 3, GOOD if owned else DIM, align="right")
        if key == "relics":
            gfx.draw_text(surf, "HAVE " + self.heirloom_now(key) if owned else perk["desc"],
                          12, y + 9, GOOD if owned else DIM)
            if level < perk["max"]:
                gfx.draw_text(surf, "> " + self.heirloom_now(key, level + 1), 12, y + 16, ACCENT)
        else:
            x = 12
            if owned:
                x += gfx.draw_text(surf, "HAVE " + self.heirloom_now(key), x, y + 9, GOOD) + 7
            if level < perk["max"]:
                gfx.draw_text(surf, "> " + self.heirloom_now(key, level + 1), x, y + 9, ACCENT)
            gfx.draw_text(surf, perk["desc"], 12, y + 16, DIM)
        self.buy_buttons[idx].draw(surf, self.mouse)

    def heirloom_now(self, key, level=None):
        return data.perk_text(key, self.level(key) if level is None else level)
