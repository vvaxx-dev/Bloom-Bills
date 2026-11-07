
import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, DIM, GOOD, PANEL_DARK, TEXT


class GameOverScene(Scene):
    def on_enter(self):
        self.shelf_btn = Button(100, 114, 120, 16, "HEIRLOOM SHELF", lambda: self.app.goto("shelf"), color=(96, 70, 140))
        self.new_btn = Button(100, 134, 120, 16, "NEW RUN", self.app.new_run, color=(70, 130, 70))
        self.title_btn = Button(100, 154, 120, 16, "BACK TO TITLE", lambda: self.app.goto("title"), color=(130, 70, 70))
        self.buttons = [self.shelf_btn, self.new_btn, self.title_btn]

    def on_key(self, key):
        if key in (pygame.K_ESCAPE,):
            self.app.goto("title")
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self.app.new_run()

    def draw(self, surf):
        gfx.rect(surf, (30, 22, 36), 0, 0, 320, 180)
        result = self.app.last_result or {}
        won = bool(result.get("won"))
        new_best = result.get("new_best")
        if won:
            gfx.draw_text(surf, "THE FARM IS YOURS", 160, 14, GOOD, scale=2, align="center")
        else:
            gfx.draw_text(surf, "THE BILL COLLECTOR CAME", 160, 14, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "ROUNDS: %s   BILLS PAID: %s" % (result.get("round", 0), result.get("quotas_paid", 0)),
                      160, 40, TEXT, align="center")
        gfx.draw_text(surf, "EARNED: $%s" % fmt(result.get("total_earned", 0)), 160, 51, TEXT, align="center")
        if won:
            gfx.draw_text(surf, "EVERY BILL PAID. THE BILL COLLECTOR GIVES UP.", 160, 64, GOOD, align="center")
        elif new_best:
            gfx.draw_text(surf, "NEW BEST ROUND!", 160, 64, ACCENT, align="center")
        else:
            gfx.draw_text(surf, "BEST ROUND: %d" % self.app.profile["best_round"], 160, 64, DIM, align="center")

        gfx.rect(surf, PANEL_DARK, 50, 78, 220, 1)
        gfx.draw_text(surf, "HEIRLOOMS EARNED THIS RUN", 160, 82, DIM, align="center")
        gfx.draw_text(surf, "+%d" % result.get("heirlooms", 0), 160, 91, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "BANKED: %d" % self.app.profile["heirlooms"], 160, 105, GOOD, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)


class ShelfScene(Scene):

    ROW_Y = 30
    ROW_H = 25

    def on_enter(self):
        self.msg = ""
        self.buy_buttons = []
        for i, key in enumerate(data.PERK_ORDER):
            b = Button(214, self.ROW_Y + i * self.ROW_H + 2, 100, 21, "",
                       lambda k=key: self.buy(k), color=(70, 130, 70))
            b.key = key
            self.buy_buttons.append(b)
        self.back_btn = Button(126, 156, 68, 18, "BACK", lambda: self.app.goto("title"), color=(70, 130, 70))
        self.buttons = self.buy_buttons + [self.back_btn]
        self.refresh()

    def profile_level(self, key):
        return int(self.app.profile["perks"].get(key, 0))

    def level(self, key):
        """The run, if one is going, owns the live numbers; otherwise the save."""
        return self.run.perk(key) if self.run else self.profile_level(key)

    def cost(self, key):
        return data.perk_cost(key, self.level(key))

    def refresh(self):
        for b in self.buy_buttons:
            perk = data.PERKS[b.key]
            level = self.level(b.key)
            if level >= perk["max"]:
                b.label, b.enabled = "MAXED", False
            else:
                b.label = "BUY %d" % self.cost(b.key)
                b.enabled = self.app.profile["heirlooms"] >= self.cost(b.key)

    def buy(self, key):
        if self.run:
            ok, msg, cost = self.run.buy_heirloom(key, self.app.profile["heirlooms"])
        else:
            ok, msg, cost = self._buy_without_a_run(key)
        self.msg = msg.upper()
        if ok:
            bank = self.app.profile
            bank["heirlooms"] = max(0, bank["heirlooms"] - cost)
            if self.run:                     # keep the saved run in step with it
                bank["perks"] = dict(self.run.perks)
                self.app.save_run()
            self.app.saves.save_profile(bank)
        self.refresh()

    def _buy_without_a_run(self, key):
        """A brand new player can level up before ever starting a run."""
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
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        gfx.draw_text(surf, "HEIRLOOM SHELF", 6, 4, ACCENT, scale=2)
        gfx.draw_text(surf, "BANKED: %d" % self.app.profile["heirlooms"], 314, 5, ACCENT, align="right")
        gfx.draw_text(surf, "PERMANENT. THEY COME WITH YOU INTO EVERY RUN.", 6, 19, DIM)
        if self.msg:
            gfx.draw_text(surf, self.msg, 314, 19, GOOD, align="right")

        for i, key in enumerate(data.PERK_ORDER):
            self.draw_row(surf, key, self.ROW_Y + i * self.ROW_H)

        gfx.draw_text(surf, "EARN MORE: +1 FOR EVERY ROUND SURVIVED, +3 FOR EVERY BILL PAID.", 6, 136, DIM)
        gfx.draw_text(surf, "BUY AS SOON AS YOU CAN - THE PRICE CLIMBS EACH LEVEL.", 6, 145, DIM)
        self.back_btn.draw(surf, self.mouse)

    def draw_row(self, surf, key, y):
        perk = data.PERKS[key]
        level = self.level(key)
        owned = level > 0
        gfx.panel(surf, 4, y, 312, 23, fill=(38, 33, 58))
        gfx.rect(surf, GOOD if owned else (66, 58, 92), 4, y, 2, 23)   # owned stripe
        gfx.draw_text(surf, perk["name"], 12, y + 3, TEXT)
        gfx.draw_text(surf, "%d/%d" % (level, perk["max"]), 206, y + 3,
                      GOOD if owned else DIM, align="right")
        # line 2: what you have now -> what the next level would give you
        x = 12
        if owned:
            x += gfx.draw_text(surf, "HAVE " + self.heirloom_now(key), x, y + 9, GOOD) + 7
        if level < perk["max"]:
            gfx.draw_text(surf, "> " + self.heirloom_now(key, level + 1), x, y + 9, ACCENT)
        gfx.draw_text(surf, perk["desc"], 12, y + 16, DIM)
        self.buy_buttons[data.PERK_ORDER.index(key)].draw(surf, self.mouse)

    def heirloom_now(self, key, level=None):
        return data.perk_text(key, self.level(key) if level is None else level)
