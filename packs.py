
from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, DIM, PANEL_DARK, TEXT


class PacksScene(Scene):
    def on_enter(self):
        self.run.phase = "packs"
        self.reveal = None
        self.reveal_t = 0.0
        self.open_btn = Button(10, 104, 88, 14, "OPEN PACK", self.open_pack, color=(70, 130, 70))
        self.go_btn = Button(236, 128, 80, 48, "START ROUND >", self.go, color=(70, 130, 70))
        self.buttons = [self.open_btn, self.go_btn]
        self.buy_buttons = []
        for i, kind in enumerate(self.run.unlocked_packs()):
            b = Button(7 + i * 57, 158, 49, 14, "", lambda k=kind: self.buy(k))
            b.kind = kind
            self.buy_buttons.append(b)
        self.buttons += self.buy_buttons
        self.refresh()

    def refresh(self):
        run = self.run
        self.open_btn.enabled = bool(run.packs)
        for b in self.buy_buttons:
            price = run.pack_price(b.kind)
            b.label = "$" + fmt(price)
            b.enabled = run.money >= price

    def open_pack(self):
        result = self.run.open_pack()
        if result:
            self.reveal = result
            self.reveal_t = 0.0
            self.app.save_run()
            self.refresh()

    def buy(self, kind):
        if self.run.buy_pack(kind):
            self.app.save_run()
            self.refresh()

    def go(self):
        self.app.goto("round")

    def on_key(self, key):
        import pygame
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.run.packs:
                self.open_pack()
            else:
                self.go()
        elif key == pygame.K_ESCAPE:
            self.app.goto("title")

    def update(self, dt):
        self.reveal_t += dt

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run)

        gfx.panel(surf, 4, 18, 100, 106, "YOUR PACKS")
        for i, kind in enumerate(run.packs[:12]):
            x, y = 10 + (i % 6) * 15, 30 + (i // 6) * 15
            gfx.draw_sprite(surf, "pack", x, y, 1, gfx.pack_subs(data.PACKS[kind]))
        if len(run.packs) > 12:
            gfx.draw_text(surf, "+%d MORE" % (len(run.packs) - 12), 98, 62, DIM, align="right")
        n = len(run.packs)
        gfx.draw_text(surf, "%d UNOPENED" % n, 10, 66, TEXT if n else DIM)
        gfx.draw_wrapped(surf, "EACH PACK HOLDS 3 SEEDS. WHAT YOU GET IS NEVER GUARANTEED.", 10, 78, 88, DIM)
        self.open_btn.draw(surf, self.mouse)

        gfx.panel(surf, 108, 18, 208, 70, "JUST OPENED")
        if self.reveal:
            kind, seeds = self.reveal
            pack = data.PACKS[kind]
            gfx.draw_text(surf, pack["name"], 311, 22, pack["color"], align="right")
            for i, sid in enumerate(seeds):
                appear = i * 0.3
                if self.reveal_t < appear:
                    continue
                hop = max(0, int(6 - (self.reveal_t - appear) * 30))
                sp = data.PLANTS[sid]
                col = data.RARITY_COLORS[sp["rarity"]]
                x, y = 114 + i * 66, 30 - hop
                gfx.rect(surf, col, x, y, 62, 54)
                gfx.rect(surf, PANEL_DARK, x + 1, y + 1, 60, 52)
                gfx.draw_sprite(surf, sid, x + 19, y + 4, 2)
                gfx.draw_text(surf, sp["name"], x + 31, y + 32, TEXT, align="center")
                gfx.draw_text(surf, sp["rarity"], x + 31, y + 41, col, align="center")
        else:
            gfx.draw_text(surf, "OPEN A PACK TO SEE WHAT YOU GET", 212, 50, DIM, align="center")

        gfx.panel(surf, 108, 92, 208, 32, "YOUR SEEDS")
        for i, sid in enumerate(data.PLANT_ORDER):
            x = 114 + i * 34
            count = run.seeds.get(sid, 0)
            gfx.draw_sprite(surf, sid, x, 104, 1)
            gfx.draw_text(surf, "x%d" % count, x + 14, 108, TEXT if count else DIM)

        for b in self.buy_buttons:
            i = self.buy_buttons.index(b)
            x = 4 + i * 57
            pack = data.PACKS[b.kind]
            gfx.panel(surf, x, 128, 55, 48)
            gfx.draw_text(surf, pack["name"], x + 27, 132, pack["color"], align="center")
            for k, sid in enumerate(pack["pool"]):
                gfx.draw_sprite(surf, sid, x + 2 + k * 13, 141, 1)
        for b in self.buy_buttons:
            b.draw(surf, self.mouse)
        self.go_btn.draw(surf, self.mouse)

        for i, b in enumerate(self.buy_buttons):
            x = 4 + i * 57
            if x <= self.mouse[0] < x + 55 and 128 <= self.mouse[1] < 176:
                pack = data.PACKS[b.kind]
                total = sum(pack["pool"].values())
                lines = [("COULD CONTAIN:", DIM)]
                for sid, w in pack["pool"].items():
                    lines.append(("%s %d%%" % (data.PLANTS[sid]["name"], round(100 * w / total)),
                                  data.RARITY_COLORS[data.PLANTS[sid]["rarity"]]))
                gfx.tooltip(surf, lines, (self.mouse[0], self.mouse[1] - 46), 84)
