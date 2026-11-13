"""Reusable click-through dialogue boxes and the first-run Moss tutorial.

The dialogue layer is deliberately scene-agnostic: any screen can pass a list of
`DialogueStep`s, optionally pointing at a rectangle or a callable that resolves
one against the active scene.  The first-run scripts below are just one user of
that layer, so story beats and later tutorials can reuse the same presentation.
"""

import pygame

from . import gfx
from .gfx import Button
from .settings import ACCENT, CANVAS_H, CANVAS_W, PANEL_DARK

# Moss is a full-height portrait anchored at the bottom-left, Crazy-Dave style.
# The white box sits beside him and still covers about a fifth of the canvas.
# If a highlighted control would be covered by the box, the box lifts just
# enough to keep it visible; if Moss himself would stand over the control, he
# steps to the right edge and the box moves to the left.
BOX_X, BOX_Y, BOX_W, BOX_H = 100, 118, 216, 54
PORTRAIT_GAP = 4
TEXT_PAD = 8
BODY_LINES = 3
LINE_STEP = 7
WHITE = (245, 240, 230)
INK = (32, 27, 50)
FOOT = (106, 110, 132)


def button_rect(button):
    return (button.x, button.y, button.w, button.h)


def _overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


class DialogueStep:
    """One beat of dialogue. `target` may be a rect or a callable(scene)->rect."""

    def __init__(self, text, target=None, speaker="MOSS", portrait="moss"):
        self.text = text
        self.target = target
        self.speaker = speaker
        self.portrait = portrait


class DialogueOverlay:
    """Modal white text box: click/Space advances, Esc skips, arrows highlight UI."""

    def __init__(self, app, steps, on_finish=None, on_skip=None):
        self.app = app
        self.on_finish = on_finish
        self.on_skip = on_skip
        self.t = 0.0
        self.pages = []
        width = BOX_W - TEXT_PAD * 2
        for step in steps:
            lines = gfx.wrap(step.text, width) or [""]
            for i in range(0, len(lines), BODY_LINES):
                self.pages.append((step, lines[i:i + BODY_LINES]))
        if not self.pages:
            self.pages.append((DialogueStep(""), [""]))
        self.index = 0
        self.skip_btn = Button(0, 0, 34, 9, "SKIP", self.skip, color=PANEL_DARK)
        self._place_skip()

    @property
    def step(self):
        return self.pages[self.index][0]

    @property
    def lines(self):
        return self.pages[self.index][1]

    def target_rect(self):
        target = self.step.target
        if callable(target):
            target = target(self.app.scene)
        if not target:
            return None
        try:
            x, y, w, h = (int(v) for v in target)
        except (TypeError, ValueError):
            return None
        if w <= 0 or h <= 0:
            return None
        return (x, y, w, h)

    def portrait_rect(self):
        """Bottom-anchored Moss; he steps aside if he would cover the target."""
        portrait = gfx.sprite(self.step.portrait)
        w, h = portrait.get_size()
        y = CANVAS_H - h
        left = (0, y, w, h)
        right = (CANVAS_W - w, y, w, h)
        target = self.target_rect()
        if target and _overlaps(left, target) and not _overlaps(right, target):
            return right
        return left

    def box_rect(self):
        px, _py, pw, _ph = self.portrait_rect()
        if px < CANVAS_W // 2:
            x = px + pw + PORTRAIT_GAP
        else:
            x = px - BOX_W - PORTRAIT_GAP
        x = max(0, min(x, CANVAS_W - BOX_W))
        y, w, h = BOX_Y, BOX_W, BOX_H
        target = self.target_rect()
        if target:
            tx, ty, _tw, th = target
            # Keep the highlighted control out from under the white box.
            if ty < y + h and ty + th > y:
                if ty >= y - h:
                    y = max(18, ty - h - 10)
                else:
                    y = min(CANVAS_H - h - 8, ty + th + 10)
        return (x, y, w, h)

    def _place_skip(self):
        x, y, w, h = self.box_rect()
        self.skip_btn.x = x + w - 40
        self.skip_btn.y = y + h - 12

    def update(self, dt):
        self.t += dt

    def advance(self):
        self.index += 1
        if self.index >= len(self.pages):
            self.finish()
        else:
            self._place_skip()

    def back(self):
        if self.index > 0:
            self.index -= 1
            self._place_skip()

    def _close(self, callback):
        self.app.dialogue_modal = None
        if callback:
            callback()

    def finish(self):
        self._close(self.on_finish)

    def skip(self):
        self._close(self.on_skip)

    def on_click(self, pos):
        self._place_skip()
        if self.skip_btn.click(pos):
            return True
        self.advance()
        return True

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_RIGHT):
            self.advance()
        elif key == pygame.K_LEFT:
            self.back()
        elif key == pygame.K_ESCAPE:
            self.skip()

    def _draw_arrow(self, surf, box, target):
        tx, ty, tw, th = target
        bx, by, bw, bh = box
        cx = max(bx + 12, min(tx + tw // 2, bx + bw - 12))
        bob = int(self.t * 4) % 2
        if ty + th <= by:
            tip_y = min(ty + th + 2 + bob, by - 5)
            shaft_top, shaft_bottom = tip_y + 4, by - 2
            direction = 1
        elif ty >= by + bh:
            tip_y = max(ty - 2 - bob, by + bh + 4)
            shaft_top, shaft_bottom = by + bh + 2, tip_y - 4
            direction = -1
        else:
            return
        if shaft_bottom >= shaft_top:
            gfx.rect(surf, PANEL_DARK, cx - 2, shaft_top, 4, shaft_bottom - shaft_top + 1)
            gfx.rect(surf, ACCENT, cx - 1, shaft_top, 2, shaft_bottom - shaft_top + 1)
        for row in range(4):
            half = row
            yy = tip_y + direction * row
            gfx.rect(surf, PANEL_DARK, cx - half - 1, yy, half * 2 + 3, 1)
            gfx.rect(surf, ACCENT, cx - half, yy, half * 2 + 1, 1)

    def draw(self, surf, mouse):
        self._place_skip()
        box = self.box_rect()
        target = self.target_rect()
        if target:
            tx, ty, tw, th = target
            for edge in (
                (tx - 2, ty - 2, tw + 4, 1), (tx - 2, ty + th + 1, tw + 4, 1),
                (tx - 2, ty - 1, 1, th + 2), (tx + tw + 1, ty - 1, 1, th + 2),
            ):
                gfx.rect(surf, PANEL_DARK, *edge)
            for edge in (
                (tx - 1, ty - 1, tw + 2, 1), (tx - 1, ty + th, tw + 2, 1),
                (tx - 1, ty, 1, th), (tx + tw, ty, 1, th),
            ):
                gfx.rect(surf, ACCENT, *edge)
            self._draw_arrow(surf, box, target)
        x, y, w, h = box
        portrait = gfx.sprite(self.step.portrait)
        surf.blit(portrait, self.portrait_rect()[:2])
        gfx.panel(surf, x, y, w, h, fill=WHITE, border=PANEL_DARK)
        gfx.rect(surf, ACCENT, x + 1, y + 1, w - 2, 2)
        gfx.draw_text(surf, self.step.speaker, x + TEXT_PAD, y + 5, (46, 120, 62))
        for i, line in enumerate(self.lines):
            gfx.draw_text(surf, line, x + TEXT_PAD, y + 13 + i * LINE_STEP, INK)
        gfx.draw_text(surf, "CLICK / SPACE: NEXT", x + TEXT_PAD, y + h - 8, FOOT)
        gfx.draw_text(surf, "%d/%d" % (self.index + 1, len(self.pages)), x + w - 48, y + h - 8, FOOT, align="right")
        self.skip_btn.draw(surf, mouse)


def _packs_steps():
    from .packs import FORECAST_BOX, GO_BTN, SEED_BOX, SELL_ONE_BTN, SELL_ALL_BTN

    sell_rect = (
        SELL_ONE_BTN[0], SELL_ONE_BTN[1],
        SELL_ALL_BTN[0] + SELL_ALL_BTN[2] - SELL_ONE_BTN[0], SELL_ONE_BTN[3],
    )
    return [
        DialogueStep("HEY THERE! I'M MOSS. EIGHT BILLS STAND BETWEEN YOU AND THIS GARDEN. LET'S GET YOU PLANTING."),
        DialogueStep("OPEN YOUR FREE PACKS HERE. EACH PACK GIVES THREE SEEDS. RARER SEEDS PAY MORE BUT GROW SLOWER.",
                     lambda scene: button_rect(scene.open_btn)),
        DialogueStep("YOUR SEEDS LAND ON THIS SHELF. HOVER ONE TO SEE ITS GROW TIME, HARVEST VALUE AND RESALE PRICE.",
                     SEED_BOX),
        DialogueStep("UNWANTED SEEDS CAN BE SOLD HERE BEFORE THE ROUND. PICK A SEED, THEN SELL 1 OR SELL ALL.",
                     sell_rect),
        DialogueStep("CHECK THE FORECAST. WEATHER CAN SPEED GROWTH, CUT PAYOUTS, OR BAN CERTAIN PLANTS.",
                     FORECAST_BOX),
        DialogueStep("WHEN YOU'RE READY, START THE ROUND. YOU CAN PLANT SEEDS BEFORE THE CLOCK STARTS.",
                     GO_BTN),
    ]


def _round_steps():
    from .round import TRAY_Y, plot_rect

    return [
        DialogueStep("PICK A SEED IN THE TRAY, THEN CLICK AN EMPTY PLOT. PLANT A FEW BEFORE STARTING THE CLOCK.",
                     lambda scene: scene.tray_rect(0) if scene.visible_seeds() else (4, TRAY_Y, 208, 28)),
        DialogueStep("PRESS START OR SPACE WHEN READY. YOU HAVE 45 SECONDS. EVERYTHING LEFT IS SOLD AT THE END.",
                     lambda scene: button_rect(scene.start_btn)),
        DialogueStep("CLICK A GROWING PLANT TO WATER IT: DOUBLE SPEED FOR A FEW SECONDS, THEN A SHORT COOLDOWN.",
                     lambda scene: plot_rect(0)),
        DialogueStep("CLICK A MATURE PLANT TO HARVEST CASH AND START ITS NEXT CYCLE. DON'T LET IT SIT TOO LONG!",
                     lambda scene: plot_rect(0)),
        DialogueStep("THE SHOVEL DIGS UP A CROP WITHOUT RETURNING THE SEED. USE IT TO CLEAR SPACE OR ESCAPE TROUBLE.",
                     lambda scene: button_rect(scene.shovel_btn)),
        DialogueStep("EVERY THIRD ROUND A BILL IS DUE. SAVE ENOUGH TO PAY IT, OR THE RUN ENDS. GOOD LUCK!"),
    ]


def _shop_steps():
    return [
        DialogueStep("SPEND HARVEST CASH ON RELICS. THEIR BONUSES STACK EVERY ROUND, BUT YOU ONLY HAVE FIVE SLOTS.",
                     lambda scene: button_rect(scene.buy_buttons[0]) if scene.buy_buttons else None),
        DialogueStep("BUY PLOTS TO GROW MORE AT ONCE. PRICES CLIMB FAST, SO BALANCE EXPANSION AGAINST RELICS.",
                     lambda scene: button_rect(scene.plot_btn)),
        DialogueStep("REROLL SWAPS THE RELIC OFFERS. IT COSTS CASH, SO SAVE IF YOU'RE HUNTING SOMETHING SPECIFIC.",
                     lambda scene: button_rect(scene.reroll_btn)),
        DialogueStep("NEXT ROUND BRINGS NEW FREE PACKS. KEEP AN EYE ON THE FORECAST AND THE NEXT BILL.",
                     lambda scene: button_rect(scene.next_btn)),
    ]


TUTORIAL_BUILDERS = {"packs": _packs_steps, "round": _round_steps, "shop": _shop_steps}
TUTORIAL_STAGES = tuple(TUTORIAL_BUILDERS)


def tutorial_steps(stage, scene):
    builder = TUTORIAL_BUILDERS.get(stage)
    return builder() if builder else []


def guide_steps():
    """Title-screen replay: the same dialogue layer, without scene-specific arrows."""
    return [
        DialogueStep("HEY! MOSS HERE. YOU'VE GOT EIGHT BILLS TO PAY AND A GARDEN TO PAY THEM WITH."),
        DialogueStep("OPEN PACKS, PLANT SEEDS, WATER GROWING PLANTS, AND HARVEST MATURE ONES BEFORE THE CLOCK RUNS OUT."),
        DialogueStep("EVERY THIRD ROUND A BILL IS DUE. MISS ONE AND THE RUN ENDS, BUT HEIRLOOMS MAKE THE NEXT RUN STRONGER."),
        DialogueStep("START A NEW RUN FOR THE FULL WALKTHROUGH, OR CHECK THE GARDEN INDEX FOR EVERY PLANT, RELIC AND HEIRLOOM."),
    ]