"""Pre-round preparation screen: open seed packs, buy extra packs, and preview weather."""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import ACCENT, BAD, BG, CANVAS_H, CANVAS_W, DIM, GOOD, PANEL_DARK, TEXT, WATER

SEED_COLS, SEED_ROWS = 4, 2
SEEDS_PER_PAGE = SEED_COLS * SEED_ROWS

PACK_COLS, PACK_ROWS = 6, 2
PACKS_PER_PAGE = PACK_COLS * PACK_ROWS

BUY_COLS, BUY_ROWS = 2, 2
BUYS_PER_PAGE = BUY_COLS * BUY_ROWS

PACKS_BOX = (4, 18, 100, 106)
REVEAL_BOX = (108, 18, 208, 74)
FORECAST_BOX = (108, 95, 208, 29)
# The bottom row is four pixels taller than it used to be so the seed shelf can
# carry a resale strip under its two rows of tiles. All three panels keep the
# same bottom edge, which is what makes them line up.
SEED_BOX = (4, 124, 138, 52)
BUY_BOX = (146, 124, 126, 52)
GO_BTN = (276, 124, 40, 52)
PAGER_Y = 131
PAGER_H = 9

# Seed resale: highlight a seed on the shelf, then the strip under it sells one
# or the whole stack for a quarter of what the grown plant would fetch. Buying
# happens here anyway, so unwanted seeds turn into cash before the round starts
# instead of cluttering the tray mid-round.
SEED_TILE_H = 14
SELL_Y = SEED_BOX[1] + 43
SELL_ONE_BTN = (SEED_BOX[0] + 2, SELL_Y, 66, 8)
SELL_ALL_BTN = (SEED_BOX[0] + 70, SELL_Y, 66, 8)

TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": TEXT}


class PacksScene(Scene):
    def on_enter(self):
        self.run.phase = "packs"
        self.reveal = None
        self.reveal_t = 0.0
        self.seed_page = 0
        self.pack_page = 0
        self.buy_page = 0
        self.seed_selected = None
        self.pack_rects = []
        self.buy_rects = []
        self._buy_buttons = []

        bx, by, bw, _bh = PACKS_BOX
        self.open_btn = Button(bx + 6, by + 66, bw - 12, 15, "OPEN PACK", self.open_pack, color=(70, 130, 70))
        self.go_btn = Button(*GO_BTN, "START ROUND >", self.go, color=(70, 130, 70))

        sx, _sy, sw, _sh = SEED_BOX
        self.sell_one_btn = Button(*SELL_ONE_BTN, "SELL 1", self.sell_one, color=(150, 70, 60))
        self.sell_all_btn = Button(*SELL_ALL_BTN, "SELL ALL", self.sell_all, color=(150, 70, 60))
        self.seed_left = Button(sx + sw - 24, PAGER_Y - 4, 8, 8, "<", self.page_left)
        self.seed_right = Button(sx + sw - 12, PAGER_Y - 4, 8, 8, ">", self.page_right)

        ux, _uy, uw, _uh = BUY_BOX
        self.buy_up = Button(ux + uw - 24, PAGER_Y, 8, PAGER_H, "^", self.buy_page_up)
        self.buy_down = Button(ux + uw - 12, PAGER_Y, 8, PAGER_H, "V", self.buy_page_down)

        self.pack_up = Button(bx + bw - 24, by + 4, 8, PAGER_H, "^", self.pack_page_up)
        self.pack_down = Button(bx + bw - 12, by + 4, 8, PAGER_H, "V", self.pack_page_down)

        self.buttons = [
            self.open_btn, self.go_btn, self.sell_one_btn, self.sell_all_btn,
            self.seed_left, self.seed_right,
            self.pack_up, self.pack_down, self.buy_up, self.buy_down,
        ]
        self.refresh()
        self.announce_season()

    @property
    def seed_pages(self):
        return max(1, (len(data.PLANT_ORDER) + SEEDS_PER_PAGE - 1) // SEEDS_PER_PAGE)

    def page_left(self):
        self.seed_page = max(0, self.seed_page - 1)

    def page_right(self):
        self.seed_page = min(self.seed_pages - 1, self.seed_page + 1)

    def on_wheel(self, dy):
        """Page whichever shelf lies under the cursor, defaulting to the seed shelf."""
        down = dy < 0
        target = self.wheel_target()
        if target == "packs":
            self.pack_page_down() if down else self.pack_page_up()
        elif target == "buy":
            self.buy_page_down() if down else self.buy_page_up()
        else:
            self.page_right() if down else self.page_left()

    def wheel_target(self):
        if gfx.inside(self.mouse, PACKS_BOX):
            return "packs"
        if gfx.inside(self.mouse, BUY_BOX):
            return "buy"
        return "seeds"

    @property
    def pack_pages(self):
        return max(1, (len(self.run.packs) + PACKS_PER_PAGE - 1) // PACKS_PER_PAGE)

    def pack_page_up(self):
        self.pack_page = max(0, self.pack_page - 1)

    def pack_page_down(self):
        self.pack_page = min(self.pack_pages - 1, self.pack_page + 1)

    def visible_packs(self):
        self.pack_page = max(0, min(self.pack_page, self.pack_pages - 1))
        start = self.pack_page * PACKS_PER_PAGE
        return [(kind, start + i) for i, kind in enumerate(self.run.packs[start:start + PACKS_PER_PAGE])]

    def pack_rect(self, i):
        x, y = PACKS_BOX[0] + 5, PACKS_BOX[1] + 14
        return (x + (i % PACK_COLS) * 14, y + (i // PACK_COLS) * 14, 12, 12)

    @property
    def buy_buttons(self):
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
        x, y = BUY_BOX[0] + 5, BUY_BOX[1] + 18
        return (x + (i % BUY_COLS) * 60, y + (i // BUY_COLS) * 16, 56, 15)

    def visible_buys(self):
        kinds = self.run.unlocked_packs()
        if len(kinds) != len(self.buy_buttons):
            self.setup_buy_buttons()
        self.buy_page = max(0, min(self.buy_page, self.buy_pages - 1))
        start = self.buy_page * BUYS_PER_PAGE
        return [(kind, self.buy_buttons[start + i]) for i, kind in enumerate(kinds[start:start + BUYS_PER_PAGE])]

    def setup_buy_buttons(self):
        self._buy_buttons = []
        for i, kind in enumerate(self.run.unlocked_packs()):
            b = Button(0, 0, 0, 0, "", lambda k=kind: self.buy(k))
            b.kind = kind
            b.slot = i
            self._buy_buttons.append(b)
        self.place_buy_buttons()

    def pack_lines(self, kind, index=None):
        pack = data.PACKS[kind]
        total = sum(pack["pool"].values())
        lines = [(pack["name"].upper() + ":", DIM)]
        if pack.get("luck"):
            lines.append(("RARE SEEDS x%s LIKELIER" % fmt(pack["luck"]), ACCENT))
        for sid, w in pack["pool"].items():
            sp = data.PLANTS[sid]
            lines.append(("%s %d%%" % (sp["name"], round(100 * w / total)), data.RARITY_COLORS[sp["rarity"]]))
        if index == 0:
            lines.append(("NEXT TO OPEN", ACCENT))
        return lines

    def seed_rect(self, i):
        return (
            SEED_BOX[0] + 6 + (i % SEED_COLS) * 33,
            SEED_BOX[1] + 13 + (i // SEED_COLS) * (SEED_TILE_H + 1),
            32,
            SEED_TILE_H,
        )

    def visible_seed_order(self):
        start = self.seed_page * SEEDS_PER_PAGE
        return data.PLANT_ORDER[start:start + SEEDS_PER_PAGE]

    def pick_seed(self, sid):
        """Highlight one seed on the shelf so the resale strip knows its target."""
        if self.run.seeds.get(sid, 0) <= 0:
            self.seed_selected = None
            self.app.toast("NO %s SEEDS - OPEN A PACK" % data.PLANTS[sid]["name"].upper())
            return False
        self.seed_selected = sid
        self.ensure_seed_visible(sid)
        return True

    def ensure_seed_visible(self, sid):
        """Turn the shelf to the page that holds `sid`, so a pick is never hidden."""
        if sid in data.PLANT_ORDER:
            self.seed_page = data.PLANT_ORDER.index(sid) // SEEDS_PER_PAGE

    def sell_target(self):
        """The seed the resale strip acts on: whatever is highlighted on the shelf."""
        sid = self.seed_selected
        if not sid:
            return None, 0, 0
        return sid, self.run.seeds.get(sid, 0), self.run.seed_price(sid)

    def _sync_sell_buttons(self):
        """Refresh the strip from the highlighted seed; returns (seed, owned, unit price)."""
        sid, owned, price = self.sell_target()
        self.sell_one_btn.enabled = owned > 0
        self.sell_all_btn.enabled = owned > 0
        self.sell_one_btn.label = ("SELL 1 $" + fmt(price)) if owned else "SELL 1"
        self.sell_all_btn.label = ("SELL ALL $" + fmt(price * owned)) if owned else "SELL ALL"
        return sid, owned, price

    def sell_seed(self, all_of=False):
        """Sell one seed, or the whole stack, from the highlighted shelf tile."""
        sid, owned, _price = self.sell_target()
        if not sid or owned <= 0:
            self.app.toast("PICK A SEED IN YOUR SEEDS FIRST")
            return
        ok, msg, _refund = self.run.sell_seed(sid, owned if all_of else 1)
        if not ok:
            return
        self.app.toast(msg, 2.5)
        if hasattr(self.app, "save_run"):
            self.app.save_run()
        if self.run.seeds.get(sid, 0) <= 0:
            self.seed_selected = None
        self.refresh()

    def sell_one(self):
        self.sell_seed(all_of=False)

    def sell_all(self):
        self.sell_seed(all_of=True)

    def announce_season(self):
        run = self.run
        if data.is_new_season(run.round):
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
        self._sync_sell_buttons()
        self.sync_pagers()

    def sync_pagers(self):
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
        self.place_buy_buttons()
        if super().on_click(pos):
            return True
        for _kind, b in self.visible_buys():
            if b.click(pos):
                return True
        for i, sid in enumerate(self.visible_seed_order()):
            if gfx.inside(pos, self.seed_rect(i)):
                self.pick_seed(sid)
                return True
        return False

    def place_buy_buttons(self):
        """Position active-page buy buttons and park inactive-page buttons off-canvas."""
        for b in self.buy_buttons:
            if b.slot // BUYS_PER_PAGE == self.buy_page:
                b.x, b.y, b.w, b.h = self.buy_slot_rect(b.slot % BUYS_PER_PAGE)
            else:
                b.x, b.y, b.w, b.h = -9999, -9999, 1, 1

    def on_key(self, key):
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if self.run.packs:
                self.open_pack()
            else:
                self.go()
        elif key == pygame.K_ESCAPE:
            if hasattr(self.app, "open_pause"):
                self.app.open_pause()
            else:
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
        elif pygame.K_1 <= key <= pygame.K_8:
            order = self.visible_seed_order()
            idx = key - pygame.K_1
            if idx < len(order):
                self.pick_seed(order[idx])

    def update(self, dt):
        self.reveal_t += dt
        self.sync_pagers()

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, BG, 0, 0, CANVAS_W, CANVAS_H)
        draw_topbar(surf, run, mouse=self.mouse)

        gfx.panel(surf, *PACKS_BOX, "YOUR PACKS")
        self.pack_rects = []
        for i, (kind, index) in enumerate(self.visible_packs()):
            r = self.pack_rect(i)
            gfx.draw_sprite(surf, "pack", r[0], r[1], 1, gfx.pack_subs(data.PACKS[kind]))
            if gfx.inside(self.mouse, r):
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

        gfx.panel(surf, *REVEAL_BOX, "JUST OPENED")
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
                x, y = 114 + i * 66, 32 - hop
                gfx.rect(surf, col, x, y, 62, 54)
                gfx.rect(surf, PANEL_DARK, x + 1, y + 1, 60, 52)
                anim = gfx.plant_anim(
                    self.reveal_t, index=i,
                    style=gfx.plant_anim_style(sid, sp, sid),
                    started=True,
                )
                gfx.draw_sprite(surf, sid, x + 19, y + 4, 2, anim=anim)
                gfx.draw_text(surf, sp["name"], x + 31, y + 32, TEXT, align="center")
                gfx.draw_text(surf, sp["rarity"], x + 31, y + 41, col, align="center")
        else:
            gfx.draw_text(surf, "OPEN A PACK TO SEE", 212, 48, DIM, align="center")
            gfx.draw_text(surf, "WHAT YOU GET", 212, 58, DIM, align="center")

        fx, fy, fw, fh = FORECAST_BOX
        twist = run.twist(run.round)
        tcol = BAD if twist.get("boss") else TONE_COLORS.get(twist.get("tone", "neutral"), TEXT)
        gfx.panel(surf, fx, fy, fw, fh, fill=(38, 33, 58))
        gfx.rect(surf, tcol, fx, fy, 3, fh)
        prefix = "BOSS FORECAST: " if twist.get("boss") else "WEATHER FORECAST: "
        gfx.draw_text(surf, prefix + twist["name"].upper(), fx + 7, fy + 4, tcol)
        gfx.draw_text(surf, "%dS" % run.round_time(), fx + fw - 5, fy + 4, DIM, align="right")
        desc_lines = gfx.wrap(twist.get("short", twist["desc"]), fw - 12)
        for k, line in enumerate(desc_lines[:2]):
            gfx.draw_text(surf, line, fx + 7, fy + 13 + k * 7, DIM if k else TEXT)

        gfx.panel(surf, *SEED_BOX, "YOUR SEEDS")
        target, owned, price = self._sync_sell_buttons()
        seed_hover = None
        for i, sid in enumerate(self.visible_seed_order()):
            r = self.seed_rect(i)
            count = run.seeds.get(sid, 0)
            picked = sid == target
            gfx.rect(surf, ACCENT if picked else PANEL_DARK, *r)
            gfx.rect(surf, (54, 47, 80) if count else (36, 31, 56), r[0] + 1, r[1] + 1, r[2] - 2, r[3] - 2)
            gfx.draw_sprite(surf, sid, r[0] + 1, r[1] + 1, 1)
            gfx.draw_text(surf, "x%d" % count, r[0] + 15, r[1] + 4, TEXT if count else DIM)
            if gfx.inside(self.mouse, r):
                seed_hover = sid
        self.sell_one_btn.draw(surf, self.mouse)
        self.sell_all_btn.draw(surf, self.mouse)
        if self.seed_pages > 1:
            self.seed_left.draw(surf, self.mouse)
            self.seed_right.draw(surf, self.mouse)
            gfx.draw_text(
                surf, "%d/%d" % (self.seed_page + 1, self.seed_pages),
                SEED_BOX[0] + SEED_BOX[2] - 30, SEED_BOX[1] + 4, DIM, align="right",
            )

        gfx.panel(surf, *BUY_BOX, "PACKS FOR SALE")
        self.place_buy_buttons()
        self.buy_rects = []
        for i, (kind, b) in enumerate(self.visible_buys()):
            b.draw(surf, self.mouse)
            self.buy_rects.append((kind, self.buy_slot_rect(i)))
        if self.buy_pages > 1:
            self.buy_up.draw(surf, self.mouse)
            self.buy_down.draw(surf, self.mouse)
            gfx.draw_text(
                surf, "%d/%d" % (self.buy_page + 1, self.buy_pages),
                BUY_BOX[0] + BUY_BOX[2] - 30, BUY_BOX[1] + 4, DIM, align="right",
            )

        self.go_btn.draw(surf, self.mouse)

        for kind, index, r in self.pack_rects:
            if gfx.inside(self.mouse, r):
                gfx.tooltip(surf, self.pack_lines(kind, index), self.mouse, 96)
                return
        for kind, r in self.buy_rects:
            if gfx.inside(self.mouse, r):
                gfx.tooltip(surf, self.pack_lines(kind), self.mouse, 96)
                return
        if gfx.inside(self.mouse, FORECAST_BOX):
            gfx.tooltip(surf, [
                ("ROUND %d WEATHER" % run.round, ACCENT),
                (twist["name"].upper(), tcol),
                (twist["desc"], TEXT),
                ("ROUND TIME: %dS" % run.round_time(), DIM),
            ], self.mouse, 120)
            return
        if self.sell_one_btn.hover(self.mouse) or self.sell_all_btn.hover(self.mouse):
            lines = [("SELL SEEDS", ACCENT)]
            if owned:
                lines.append(("%s: $%s EACH, %d OWNED" % (data.PLANTS[target]["name"], fmt(price), owned), GOOD))
                lines.append(("SELL ALL: $" + fmt(price * owned), ACCENT))
                lines.append(("A QUARTER OF THE GROWN PLANT'S VALUE.", DIM))
            else:
                lines.append(("PICK A SEED ON THE SHELF FIRST.", DIM))
            gfx.tooltip(surf, lines, self.mouse, 112)
            return
        if seed_hover:
            sp = data.PLANTS[seed_hover]
            rcol = data.RARITY_COLORS[sp["rarity"]]
            lines = [
                (sp["name"], rcol),
                ("%s - %gS GROW" % (sp["rarity"].upper(), sp["grow"]), DIM),
                ("HARVEST $%s / SELL $%s" % (fmt(sp["yield"]), fmt(sp["sell"])), GOOD),
                ("SEED RESALE: $%s EACH" % fmt(run.seed_price(seed_hover)), ACCENT),
            ]
            if run.seeds.get(seed_hover, 0) > 0:
                lines.append(("CLICK IT TO PICK IT, THEN SELL", DIM))
            if "nocturnal" in sp["tags"]:
                lines.append(("NOCTURNAL: CELLAR OR ECLIPSE", WATER))
            if sp.get("upkeep"):
                lines.append(("CURSED: -$%s UPKEEP" % fmt(sp["upkeep"]), BAD))
            if sp.get("aura") == "jealous":
                lines.append(("JEALOUS: OTHERS -50%", BAD))
            if sp.get("pays", True) is False:
                lines.append(("PAYS NOTHING ITSELF", ACCENT))
            if sp.get("note"):
                lines.append((sp["note"], GOOD))
            if twist["ban"] and twist["ban"] in sp["tags"]:
                lines.append(("BANNED BY %s THIS ROUND!" % twist["name"].upper(), BAD))
            gfx.tooltip(surf, lines, self.mouse, 112)
