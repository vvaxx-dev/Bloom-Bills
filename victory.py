"""The deed: after the eighth bill is paid the run is won, and the player
chooses between taking the farm and retiring, or farming on into endless
rounds with an unpayable-in-principle bill ladder that only ends when a
bill goes unpaid."""


from . import gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BG, CANVAS_H, CANVAS_W, DIM, GOOD, PANEL_DARK, TEXT


class VictoryScene(Scene):
    """One-time choice at the win: retire with the farm, or keep farming endless."""

    def on_enter(self):
        self.retire_btn = Button(10, 148, 142, 20, "RETIRE WITH THE FARM", self.retire,
                                 color=(70, 130, 70))
        self.endless_btn = Button(168, 148, 142, 20, "KEEP FARMING (ENDLESS)", self.keep_farming,
                                  color=(96, 70, 140))
        self.buttons = [self.retire_btn, self.endless_btn]

    def retire(self):
        """End the run now; the farm is kept and the win is banked."""
        self.run.retired = True
        self.app.finish_run()
        self.app.goto("gameover")

    def keep_farming(self):
        """Continue into endless rounds; the run only ends when a bill goes unpaid."""
        self.run.endless = True
        self.run.enter_shop()
        self.app.save_run()
        self.app.goto("shop")
        if hasattr(self.app, "start_tutorial"):
            self.app.start_tutorial("shop")

    def on_key(self, key):
        # Esc still opens the pause menu via the app; Space/Return would
        # silently pick a side of the decision, so they do nothing here.
        pass

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (26, 32, 24), 0, 0, CANVAS_W, CANVAS_H)
        draw_topbar(surf, run, "VICTORY", mouse=self.mouse)

        gfx.draw_text(surf, "THE FARM IS YOURS", CANVAS_W // 2, 24, GOOD, scale=2, align="center")
        gfx.draw_text(surf, "EVERY BILL PAID. THE COLLECTOR GIVES UP.", CANVAS_W // 2, 42, GOOD, align="center")
        gfx.draw_text(surf, "MOSS: THIRTY-SIX YEARS OF HERS, AND EIGHT ROUNDS OF YOURS. NOT BAD.",
                      CANVAS_W // 2, 49, DIM, align="center")

        # Moss's line gets its own row, and the divider and the three stat lines
        # below it are spaced to clear it.
        gfx.rect(surf, PANEL_DARK, 40, 57, CANVAS_W - 80, 1)
        gfx.draw_text(surf, "ROUNDS: %d   BILLS PAID: %d" % (run.round, run.quotas_paid),
                      CANVAS_W // 2, 62, TEXT, align="center")
        gfx.draw_text(surf, "TOTAL EARNED: $%s" % fmt(run.total_earned),
                      CANVAS_W // 2, 71, ACCENT, align="center")
        gfx.draw_text(surf, "HEIRLOOMS THIS RUN: +%d" % run.heirloom_reward(),
                      CANVAS_W // 2, 80, ACCENT, align="center")
        gfx.rect(surf, PANEL_DARK, 40, 92, CANVAS_W - 80, 1)

        gfx.draw_text(surf, "RETIRE AND THE RUN ENDS WITH THE DEED IN", CANVAS_W // 2, 100, DIM, align="center")
        gfx.draw_text(surf, "YOUR POCKET.", CANVAS_W // 2, 109, DIM, align="center")
        gfx.draw_text(surf, "OR KEEP FARMING: THE BILLS KEEP COMING,", CANVAS_W // 2, 122, TEXT, align="center")
        gfx.draw_text(surf, "6X BIGGER EACH TIME, UNTIL ONE GOES UNPAID.", CANVAS_W // 2, 131, TEXT, align="center")

        self.draw_buttons(surf)
