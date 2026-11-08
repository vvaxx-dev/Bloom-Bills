from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, DIM, PANEL_DARK, TEXT

SEEDS_PER_PAGE = 12         
SEED_COLS = 6

class PacksScene(Scene):
    def on_enter(self):
        self.run.phase = "packs"
        self.reveal = None
        self.reveal_t = 0.0
        self.seed_page = 0
        self.open_btn = Button(10, 70, 88, 14, "OPEN PACK", self.open_pack, color=(70, 130, 70))
        self.go_btn = Button(276, 128, 40, 48, "START ROUND >", self.go, color=(70, 130, 70))
        self.seed_left = Button(250, 137, 6, 22, "<", self.page_left)
        self.seed_right = Button(258, 137, 6, 22, ">", self.page_right)
        self.buttons = [self.open_btn, self.go_btn, self.seed_left, self.seed_right]
        self.buy_buttons = []
        for i, kind in enumerate(self.run.unlocked_packs()):
            b = Button(4, 92 + i * 12, 100, 12, "", lambda k=kind: self.buy(k))
            b.kind = kind
            self.buy_buttons.append(b)
        self.buttons += self.buy_buttons
        self.refresh()
        self.announce_season()

    # ------------------------------------------------------- seed shelf
    @property
    def seed_pages(self):
        return max(1, (len(data.PLANT_ORDER) + SEEDS_PER_PAGE - 1) // SEEDS_PER_PAGE)

    def page_left(self):
        self.seed_page = max(0, self.seed_page - 1)

    def page_right(self):
        self.seed_page = min(self.seed_pages - 1, self.seed_page + 1)

    def on_wheel(self, dy):
        if dy > 0:
            self.page_left()
        else:
            self.page_right()

    def visible_seed_order(self):
        start = self.seed_page * SEEDS_PER_PAGE
        return data.PLANT_ORDER[start:start + SEEDS_PER_PAGE]

    # ---------------------------------------------------------- seasons
    def announce_season(self):
        """Round 1 of a season: say so, once, when the packs screen opens."""
        run = self.run
        if not data.is_new_season(run.round):
            return
        season = run.season()
        self.app.toast("SEASON %d: %s" % (run.season_number(), season["name"].upper()), 3.0)

    def refresh(self):
        run = self.run
        self.open_btn.enabled = bool(run.packs)
        for b in self.buy_buttons:
            price = run.pack_price(b.kind)
            b.label = "%s $%s" % (data.PACKS[b.kind]["short"], fmt(price))
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
        self.seed_left.enabled = self.seed_page > 0
        self.seed_right.enabled = self.seed_page < self.seed_pages - 1

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run)

        gfx.panel(surf, 4, 18, 100, 70, "YOUR PACKS")
        for i, kind in enumerate(run.packs[:12]):
            x, y = 10 + (i % 6) * 15, 28 + (i // 6) * 15
            gfx.draw_sprite(surf, "pack", x, y, 1, gfx.pack_subs(data.PACKS[kind]))
        if len(run.packs) > 12:
            gfx.draw_text(surf, "+%d MORE" % (len(run.packs) - 12), 98, 44, DIM, align="right")
        n = len(run.packs)
        gfx.draw_text(surf, "%d UNOPENED" % n, 10, 58, TEXT if n else DIM)
        self.open_btn.draw(surf, self.mouse)

        gfx.panel(surf, 4, 90, 100, 86)
        for b in self.buy_buttons:
            b.draw(surf, self.mouse)

        gfx.panel(surf, 108, 18, 208, 106, "JUST OPENED")
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
                x, y = 114 + i * 66, 34 - hop
                gfx.rect(surf, col, x, y, 62, 54)
                gfx.rect(surf, PANEL_DARK, x + 1, y + 1, 60, 52)
                gfx.draw_sprite(surf, sid, x + 19, y + 4, 2)
                gfx.draw_text(surf, sp["name"], x + 31, y + 32, TEXT, align="center")
                gfx.draw_text(surf, sp["rarity"], x + 31, y + 41, col, align="center")
        else:
            gfx.draw_text(surf, "OPEN A PACK TO SEE", 212, 58, DIM, align="center")
            gfx.draw_text(surf, "WHAT YOU GET", 212, 68, DIM, align="center")

        gfx.panel(surf, 4, 128, 268, 48, "YOUR SEEDS")
        seeds_shown = self.visible_seed_order()
        for i, sid in enumerate(seeds_shown):
            x = 10 + (i % SEED_COLS) * 42
            y = 138 + (i // SEED_COLS) * 17
            count = run.seeds.get(sid, 0)
            gfx.draw_sprite(surf, sid, x, y, 1)
            gfx.draw_text(surf, "x%d" % count, x + 14, y + 4, TEXT if count else DIM)
            if self.seed_pages > 1:
                self.seed_left.enabled = self.seed_page > 0
                self.seed_right.enabled = self.seed_page < self.seed_pages - 1
                self.seed_left.draw(surf, self.mouse)
                self.seed_right.draw(surf, self.mouse)
                gfx.draw_text(surf, "%d/%d" % (self.seed_page + 1, self.seed_pages), 252, 169, DIM)
        self.go_btn.draw(surf, self.mouse)

        for i, b in enumerate(self.buy_buttons):
            if b.hover(self.mouse):
                pack = data.PACKS[b.kind]
                total = sum(pack["pool"].values())
                lines = [(pack["name"].upper() + ":", DIM)]
                if pack.get("luck"):
                    lines.append(("RARE SEEDS x%s LIKELIER" % fmt(pack["luck"]), ACCENT))
                for sid, w in pack["pool"].items():
                    lines.append(("%s %d%%" % (data.PLANTS[sid]["name"], round(100 * w / total)),
                                  data.RARITY_COLORS[data.PLANTS[sid]["rarity"]]))
                gfx.tooltip(surf, lines, self.mouse, 96)
