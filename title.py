"""Title screen."""

import pygame

from . import gfx
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, DIM, PANEL_LIGHT, TEXT


class TitleScene(Scene):
    def on_enter(self):
        profile = self.app.profile
        has_run = bool(self.app.saves.load_run())
        self.has_run = has_run
        self.continue_btn = Button(110, 84, 100, 18, "CONTINUE", self.app.continue_run, color=(70, 130, 70))
        self.continue_btn.enabled = has_run
        self.new_btn = Button(110, 106, 100, 18, "NEW RUN", self.new_run_clicked)
        self.shelf_btn = Button(110, 128, 100, 18, "HEIRLOOM SHELF", lambda: self.app.goto("shelf"),
                                color=(96, 70, 140))
        self.quit_btn = Button(110, 150, 100, 18, "QUIT", self.quit_clicked, color=(150, 70, 60))

        # Flower Index ("Little book") on the main page
        self.book_btn = Button(12, 126, 48, 42, "INDEX", lambda: self.app.goto("index"),
                               color=(112, 72, 48), icon="book", icon_scale=2)
        # Settings cogwheel on the main page
        self.cog_btn = Button(292, 8, 20, 20, "", self.app.open_settings,
                              color=PANEL_LIGHT, icon="cog", icon_scale=1)

        self.buttons = [
            self.continue_btn, self.new_btn, self.shelf_btn, self.quit_btn,
            self.book_btn, self.cog_btn,
        ]
        self.profile = profile

    def draw(self, surf):
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        gfx.draw_text(surf, "BLOOM & BILLS", 160, 35, ACCENT, scale=2, align="center")
        gfx.draw_text(surf, "HEIRLOOMS: %d" % self.profile["heirlooms"], 160, 62, ACCENT, align="center")
        gfx.draw_text(surf, "BEST ROUND: %d   RUNS: %d" % (self.profile["best_round"], self.profile["runs"]),
                      160, 72, DIM, align="center")
        for button in self.buttons:
            button.draw(surf, self.mouse)
        if self.book_btn.hover(self.mouse):
            gfx.tooltip(surf, [
                ("FLOWER INDEX", ACCENT),
                ("BROWSE ALL PLANTS & MUTANTS", TEXT),
            ], self.mouse, 112)
        elif self.cog_btn.hover(self.mouse):
            gfx.tooltip(surf, [("SETTINGS", ACCENT)], self.mouse, 56)

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.continue_btn.enabled:
                self.app.continue_run()
            else:
                self.app.new_run()

    def new_run_clicked(self):
        if self.has_run:
            self.app.ask_confirm(
                "START A NEW RUN?",
                "YOUR SAVED RUN WILL BE OVERWRITTEN.",
                self.app.new_run,
                confirm_label="NEW RUN",
                danger=True,
            )
        else:
            self.app.new_run()

    def quit_clicked(self):
        self.app.ask_confirm(
            "QUIT GAME?",
            "EXIT BLOOM & BILLS?",
            self.app.quit,
            confirm_label="QUIT",
            danger=True,
        )
