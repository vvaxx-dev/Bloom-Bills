
import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, DIM, GOOD, PANEL_DARK, TEXT


class GameOverScene(Scene):
    def on_enter(self):
        self.button = Button(105, 150, 110, 20, "BACK TO TITLE", lambda: self.app.goto("title"), color=(130, 70, 70))
        self.buttons = [self.button]

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            self.app.goto("title")

    def draw(self, surf):
        gfx.rect(surf, (30, 22, 36), 0, 0, 320, 180)
        gfx.draw_text(surf, "THE BILL COLLECTOR CAME", 160, 48, ACCENT, scale=2, align="center")
        result = self.app.last_result or {}
        gfx.draw_text(surf, "ROUNDS: %s  BILLS: %s" % (result.get("round", 0), result.get("quotas_paid", 0)), 160, 78, TEXT, align="center")
        gfx.draw_text(surf, "HEIRLOOMS: %s" % result.get("heirlooms", 0), 160, 88, GOOD, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)


class ShelfScene(Scene):
    def on_enter(self):
        self.buttons = [Button(105, 150, 110, 20, "BACK", lambda: self.app.goto("title"), color=(70, 130, 70))]

    def on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_SPACE, pygame.K_RETURN):
            self.app.goto("title")

    def draw(self, surf):
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, self.run, "UPGRADES") if self.run else gfx.draw_text(surf, "UPGRADES", 160, 20, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "HEIRLOOMS: %d" % self.app.profile["heirlooms"], 160, 50, TEXT, align="center")
        for rid in data.PERK_ORDER:
            perk = data.PERKS[rid]
            level = self.app.profile["perks"].get(rid, 0)
            gfx.draw_text(surf, "%s  %d/%d" % (perk["name"], level, perk["max"]), 160, 70 + data.PERK_ORDER.index(rid) * 12, DIM, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)
