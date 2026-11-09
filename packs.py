from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, DIM, PANEL_DARK, TEXT

SEED_COLS, SEED_ROWS = 4, 2
SEEDS_PER_PAGE = SEED_COLS * SEED_ROWS

PACK_COLS, PACK_ROWS = 6, 2
PACKS_PER_PAGE = PACK_COLS * PACK_ROWS

BUY_COLS, BUY_ROWS = 2, 2
BUYS_PER_PAGE = BUY_COLS * BUY_ROWS

PACKS_BOX = (4, 18, 100, 106)
SEED_BOX = (4, 128, 138, 48)
BUY_BOX = (146, 128, 126, 48)
GO_BTN = (276, 128, 40, 48)
PAGER_Y = 131                       
PAGER_H = 9


def inside(pos, r):
    return r[0] <= pos[0] < r[0] + r[2] and r[1] <= pos[1] < r[1] + r[3]

class PacksScene(Scene):
    def on_enter(self):
        self.run.phase = "packs"
        self.reveal = None
        self.reveal_t = 0.0
        self.seed_page = 0
        self.pack_page = 0
        self.buy_page = 0
        self.pack_rects = []
        self.buy_rects = []
        self._buy_buttons = []
        bx, by, bw, _bh = PACKS_BOX
        self.open_btn = Button(bx + 6, by + 66, bw - 12, 15, "OPEN PACK", self.open_pack,
                               color=(70, 130, 70))
        self.go_btn = Button(*GO_BTN, "START ROUND >", self.go, color=(70, 130, 70))
        sx, _sy, sw, _sh = SEED_BOX
        self.seed_left = Button(sx + sw - 24, PAGER_Y, 8, PAGER_H, "<", self.page_left)
        self.seed_right = Button(sx + sw - 12, PAGER_Y, 8, PAGER_H, ">", self.page_right)
        ux, _uy, uw, _uh = BUY_BOX
        self.buy_up = Button(ux + uw - 24, PAGER_Y, 8, PAGER_H, "^", self.buy_page_up)
        self.buy_down = Button(ux + uw - 12, PAGER_Y, 8, PAGER_H, "V", self.buy_page_down)
        # the unopened-pack tray keeps its own pager, inside its own panel
        self.pack_up = Button(bx + bw - 24, by + 4, 8, PAGER_H, "^", self.pack_page_up)
        self.pack_down = Button(bx + bw - 12, by + 4, 8, PAGER_H, "V", self.pack_page_down)
        self.buttons = [self.open_btn, self.go_btn, self.seed_left, self.seed_right,
                        self.pack_up, self.pack_down, self.buy_up, self.buy_down]
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
        """One notch, one page - on whichever shelf the cursor is over, and on
        the seed shelf when it is over none of them. Wheel up reads upwards,
        which is pygame's positive y (the same way the round's tray does it)."""
        down = dy < 0
        target = self.wheel_target()
        if target == "packs":
            self.pack_page_down() if down else self.pack_page_up()
        elif target == "buy":
            self.buy_page_down() if down else self.buy_page_up()
        else:
            self.page_right() if down else self.page_left()

    def wheel_target(self):
        if inside(self.mouse, PACKS_BOX):
            return "packs"
        if inside(self.mouse, BUY_BOX):
            return "buy"
        return "seeds"

    # ------------------------------------------------------- pack shelf
    @property
    def pack_pages(self):
        return max(1, (len(self.run.packs) + PACKS_PER_PAGE - 1) // PACKS_PER_PAGE)

    def pack_page_up(self):
        self.pack_page = max(0, self.pack_page - 1)

    def pack_page_down(self):
        self.pack_page = min(self.pack_pages - 1, self.pack_page + 1)

    def visible_packs(self):
        """(kind, packed index) for the packs on the current page."""
        self.pack_page = max(0, min(self.pack_page, self.pack_pages - 1))
        start = self.pack_page * PACKS_PER_PAGE
        return [(kind, start + i) for i, kind in enumerate(self.run.packs[start:start + PACKS_PER_PAGE])]

    def pack_rect(self, i):
        """Slot i on the current page, in the unopened-packs tray."""
        x, y = PACKS_BOX[0] + 5, PACKS_BOX[1] + 14
        return (x + (i % PACK_COLS) * 14, y + (i // PACK_COLS) * 14, 12, 12)

    # ------------------------------------------------------- buying shelf
    @property
    def buy_buttons(self):
        """Every for-sale button, in PACK_ORDER; only its page is drawn."""
        return self._buy_buttons

    @property
    def buy_pages(self):
        kinds = self.run.unlocked_packs()
        return max(1, (len(kinds) + BUYS_PER_PAGE - 1) // BUYS_PER_PAGE)

    def buy_page_up(self):
        self.buy_page = max(0, self.buy_page - 1)

    def buy_page_down(self):
        self.buy_page = min(self.buy_pages - 1, self.buy_page + 1)

    def buy_slot_rect(self, i):
        """Where slot i of a page sits on the shelf."""
        x, y = BUY_BOX[0] + 5, BUY_BOX[1] + 14
        return (x + (i % BUY_COLS) * 60, y + (i // BUY_COLS) * 16, 56, 15)

    def visible_buys(self):
        """(kind, button) for the packs on sale on the current page."""
        kinds = self.run.unlocked_packs()
        if len(kinds) != len(self.buy_buttons):   
            self.setup_buy_buttons()
        self.buy_page = max(0, min(self.buy_page, self.buy_pages - 1))
        start = self.buy_page * BUYS_PER_PAGE
        return [(kind, self.buy_buttons[start + i])
                for i, kind in enumerate(kinds[start:start + BUYS_PER_PAGE])]

    def setup_buy_buttons(self):
        """One button per unlocked pack, in shelf order. Where each one sits is
        worked out when it is drawn or clicked, so a pack unlocking mid-run can
        never leave a button stranded off-screen."""
        self._buy_buttons = []
        for i, kind in enumerate(self.run.unlocked_packs()):
            b = Button(0, 0, 0, 0, "", lambda k=kind: self.buy(k))
            b.kind = kind
            b.slot = i
            self._buy_buttons.append(b)
        self.place_buy_buttons()

    def pack_lines(self, kind, index=None):
        """Tooltip body for a pack: name, odds, and whether it opens next."""
        pack = data.PACKS[kind]
        total = sum(pack["pool"].values())
        lines = [(pack["name"].upper() + ":", DIM)]
        if pack.get("luck"):
            lines.append(("RARE SEEDS x%s LIKELIER" % fmt(pack["luck"]), ACCENT))
        for sid, w in pack["pool"].items():
            lines.append(("%s %d%%" % (data.PLANTS[sid]["name"], round(100 * w / total)),
                          data.RARITY_COLORS[data.PLANTS[sid]["rarity"]]))
        if index == 0:
            lines.append(("NEXT TO OPEN", ACCENT))
        return lines

    def seed_rect(self, i):
        """Slot i on the current seed page."""
        return (SEED_BOX[0] + 6 + (i % SEED_COLS) * 33,
                SEED_BOX[1] + 13 + (i // SEED_COLS) * 16, 32, 14)

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
        self.visible_packs()  
        self.visible_buys()   
        self.open_btn.enabled = bool(run.packs)
        for b in self.buy_buttons:
            price = run.pack_price(b.kind)
            b.label = "%s\n$%s" % (data.PACKS[b.kind]["short"], fmt(price))
            b.enabled = run.money >= price
        self.sync_pagers()

    def sync_pagers(self):
        """A pager with nowhere to go is disabled, so a click on an arrow that
        is not drawn cannot page anything."""
        self.pack_up.enabled = self.pack_page > 0
        self.pack_down.enabled = self.pack_page < self.pack_pages - 1
        self.buy_up.enabled = self.buy_page > 0
        self.buy_down.enabled = self.buy_page < self.buy_pages - 1
        self.seed_left.enabled = self.seed_page > 0
        self.seed_right.enabled = self.seed_page < self.seed_pages - 1

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

    def on_click(self, pos):
        """Only buttons that are actually on screen take the click: a buy
        button on another page has no rectangle to be clicked in."""
        self.place_buy_buttons()
        if super().on_click(pos):
            return True
        for _kind, b in self.visible_buys():
            if b.click(pos):
                return True
        return False

    def place_buy_buttons(self):
        """Move each button onto its slot when it is on the current page and
        park it off-canvas when it is not, so hidden rows can never swallow a
        click meant for the seed shelf underneath."""
        for b in self.buy_buttons:
            if b.slot // BUYS_PER_PAGE == self.buy_page:
                x, y, w, h = self.buy_slot_rect(b.slot % BUYS_PER_PAGE)
                b.x, b.y, b.w, b.h = x, y, w, h
            else:
                b.x, b.y, b.w, b.h = -9999, -9999, 1, 1

    def on_key(self, key):
        import pygame
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.run.packs:
                self.open_pack()
            else:
                self.go()
        elif key == pygame.K_ESCAPE:
            self.app.goto("title")
        elif key == pygame.K_LEFT:
            self.page_left()
        elif key == pygame.K_RIGHT:
            self.page_right()
        elif key == pygame.K_UP:
            self.pack_page_up()
            self.buy_page_up()
        elif key == pygame.K_DOWN:
            self.pack_page_down()
            self.buy_page_down()

    def update(self, dt):
        self.reveal_t += dt
        self.sync_pagers()

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run)

        # --- unopened packs -------------------------------------------
        gfx.panel(surf, *PACKS_BOX, "YOUR PACKS")
        self.pack_rects = []
        for i, (kind, index) in enumerate(self.visible_packs()):
            r = self.pack_rect(i)
            gfx.draw_sprite(surf, "pack", r[0], r[1], 1, gfx.pack_subs(data.PACKS[kind]))
            if inside(self.mouse, r):
                gfx.rect(surf, ACCENT, r[0] - 1, r[1] - 1, r[2] + 2, 1)
                gfx.rect(surf, ACCENT, r[0] - 1, r[1] + r[3], r[2] + 2, 1)
            self.pack_rects.append((kind, index, r))
        n = len(run.packs)
        pages = self.pack_pages
        gfx.draw_text(surf, "%d PACK%s" % (n, "" if n == 1 else "S"), 10, 62, TEXT if n else DIM)
        if pages > 1:
            self.pack_up.draw(surf, self.mouse)
            self.pack_down.draw(surf, self.mouse)
            gfx.draw_text(surf, "%d/%d" % (self.pack_page + 1, pages), 88, 62, DIM, align="right")
        elif not n:
            gfx.draw_text(surf, "NONE YET", 88, 62, DIM, align="right")

        self.open_btn.draw(surf, self.mouse)

        # --- just opened ----------------------------------------------
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

        # --- your seeds -----------------------------------------------
        gfx.panel(surf, *SEED_BOX, "YOUR SEEDS")
        for i, sid in enumerate(self.visible_seed_order()):
            r = self.seed_rect(i)
            count = run.seeds.get(sid, 0)
            gfx.draw_sprite(surf, sid, r[0], r[1], 1)
            gfx.draw_text(surf, "x%d" % count, r[0] + 13, r[1] + 4, TEXT if count else DIM)
        if self.seed_pages > 1:
            self.seed_left.draw(surf, self.mouse)
            self.seed_right.draw(surf, self.mouse)
            gfx.draw_text(surf, "%d/%d" % (self.seed_page + 1, self.seed_pages),
                          SEED_BOX[0] + SEED_BOX[2] - 30, SEED_BOX[1] + 4, DIM, align="right")

        # --- packs for sale, paged ------------------------------------
        gfx.panel(surf, *BUY_BOX, "PACKS FOR SALE")
        self.place_buy_buttons()
        self.buy_rects = []
        for i, (kind, b) in enumerate(self.visible_buys()):
            b.draw(surf, self.mouse)
            self.buy_rects.append((kind, self.buy_slot_rect(i)))
        if self.buy_pages > 1:
            self.buy_up.draw(surf, self.mouse)
            self.buy_down.draw(surf, self.mouse)
            gfx.draw_text(surf, "%d/%d" % (self.buy_page + 1, self.buy_pages),
                          BUY_BOX[0] + BUY_BOX[2] - 30, BUY_BOX[1] + 4, DIM, align="right")

        self.go_btn.draw(surf, self.mouse)

        # --- tooltips -------------------------------------------------
        for kind, index, r in self.pack_rects:
            if inside(self.mouse, r):
                gfx.tooltip(surf, self.pack_lines(kind, index), self.mouse, 96)
                return
        for kind, r in self.buy_rects:
            if inside(self.mouse, r):
                gfx.tooltip(surf, self.pack_lines(kind), self.mouse, 96)
                return
