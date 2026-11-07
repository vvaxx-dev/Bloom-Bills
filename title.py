"""Title screen."""

import pygame

from . import gfx
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, DIM


class TitleScene(Scene):
    def on_enter(self):
        profile = self.app.profile
        self.continue_btn = Button(110, 86, 100, 18, "CONTINUE", self.app.continue_run, color=(70, 130, 70))
        has_run = bool(self.app.saves.load_run())
        self.continue_btn.enabled = has_run
        self.new_btn = Button(110, 108, 100, 18, "NEW RUN", self.app.new_run)
        self.shelf_btn = Button(110, 130, 100, 18, "HEIRLOOM SHELF", lambda: self.app.goto("shelf"), color=(96, 70, 140))
        # closes the game: App.quit() stops the main loop in app.py
        self.quit_btn = Button(110, 152, 100, 18, "QUIT", self.app.quit, color=(150, 70, 60))
        self.buttons = [self.continue_btn, self.new_btn, self.shelf_btn, self.quit_btn]
        self.profile = profile

    def draw(self, surf):
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        gfx.draw_text(surf, "BLOOM & BILLS", 160, 35, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "HEIRLOOMS: %d" % self.profile["heirlooms"], 160, 62, ACCENT, align="center")
        gfx.draw_text(surf, "BEST ROUND: %d   RUNS: %d" % (self.profile["best_round"], self.profile["runs"]),
                      160, 72, DIM, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.continue_btn.enabled:
                self.app.continue_run()
            else:
                self.app.new_run()
