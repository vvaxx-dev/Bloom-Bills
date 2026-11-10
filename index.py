"""Flower Index compendium: browse plant stats, pack sources, mutations, and lifetime harvests."""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, BAD, CANVAS_H, CANVAS_W, DIM, GOOD, PANEL_DARK, PANEL_LIGHT, TEXT, WATER

GRID_COLS, GRID_ROWS = 3, 3
PER_PAGE = GRID_COLS * GRID_ROWS

CATEGORIES = [
    ("all", "ALL"),
    ("garden", "GARDEN"),
    ("farmer", "FARMER"),
    ("night", "NIGHT"),
    ("mutant", "MUTANTS"),
]
_CATEGORY_LABELS = dict(CATEGORIES)
_GARDEN_PLANTS = [s for s in data.SURFACE_PLANTS if s not in data.FARMER_PLANTS]


def _category_ids(cat):
    if cat == "garden":
        return list(_GARDEN_PLANTS)
    if cat == "farmer":
        return list(data.FARMER_PLANTS)
    if cat == "night":
        return list(data.NOCTURNAL_PLANTS)
    if cat == "mutant":
        return list(data.MUTANTS)
    return list(data.PLANT_ORDER) + list(data.MUTANTS)


class IndexScene(Scene):
    def on_enter(self):
        self.category = "all"
        self.page = 0
        self.selected = data.PLANT_ORDER[0]
        self.tab_buttons = []
        tx = 88
        for cid, label in CATEGORIES:
            bw = gfx.text_width(label) + 10
            b = Button(tx, 2, bw, 13, label, lambda c=cid: self.set_category(c))
            b.cid = cid
            self.tab_buttons.append(b)
            tx += bw + 3
        self.back_btn = Button(282, 2, 34, 13, "BACK", lambda: self.app.goto("title"), color=(130, 70, 70))
        self.prev_btn = Button(18, 154, 20, 13, "<", self.prev_page)
        self.next_btn = Button(132, 154, 20, 13, ">", self.next_page)
        self.mutant_rects = []
        self.base_rect = None
        self.buttons = self.tab_buttons + [self.back_btn, self.prev_btn, self.next_btn]
        self.sync()

    def entries(self):
        return _category_ids(self.category)

    @property
    def pages(self):
        return max(1, (len(self.entries()) + PER_PAGE - 1) // PER_PAGE)

    def set_category(self, cid):
        self.category = cid
        self.page = 0
        ids = self.entries()
        if ids and self.selected not in ids:
            self.selected = ids[0]
        self.sync()

    def select_plant(self, sid):
        """Focus `sid`, switching tabs and page if it is hidden by the current category filter."""
        if sid not in data.PLANTS:
            return
        self.selected = sid
        ids = self.entries()
        if sid not in ids:
            self.category = "mutant" if data.PLANTS[sid].get("mutant") else "all"
            ids = self.entries()
        if sid in ids:
            self.page = ids.index(sid) // PER_PAGE
        self.sync()

    def prev_page(self):
        self.page = max(0, self.page - 1)
        self.sync()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.sync()

    def sync(self):
        self.page = max(0, min(self.page, self.pages - 1))
        self.prev_btn.enabled = self.page > 0
        self.next_btn.enabled = self.page < self.pages - 1
        for b in self.tab_buttons:
            b.active = (b.cid == self.category)
            b.border_color = ACCENT
            b.color = (84, 68, 120) if b.active else PANEL_LIGHT

    def visible_entries(self):
        ids = self.entries()
        start = self.page * PER_PAGE
        return ids[start:start + PER_PAGE]

    def card_rect(self, i):
        row, col = divmod(i, GRID_COLS)
        return (16 + col * 46, 33 + row * 39, 43, 36)

    def on_wheel(self, dy):
        if dy > 0:
            self.prev_page()
        elif dy < 0:
            self.next_page()

    def on_click(self, pos):
        if super().on_click(pos):
            return True
        for i, sid in enumerate(self.visible_entries()):
            if gfx.inside(pos, self.card_rect(i)):
                self.selected = sid
                return True
        for mid, r in self.mutant_rects:
            if gfx.inside(pos, r):
                self.select_plant(mid)
                return True
        if self.base_rect and gfx.inside(pos, self.base_rect[1]):
            self.select_plant(self.base_rect[0])
            return True
        return False

    def on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.goto("title")
        elif key == pygame.K_LEFT:
            self.prev_page()
        elif key == pygame.K_RIGHT:
            self.next_page()

    def draw(self, surf):
        gfx.rect(surf, (28, 24, 42), 0, 0, CANVAS_W, CANVAS_H)
        gfx.draw_sprite(surf, "book", 5, 2, 1)
        gfx.draw_text(surf, "INDEX", 22, 6, ACCENT)

        for b in self.tab_buttons:
            b.draw(surf, self.mouse)
        self.back_btn.draw(surf, self.mouse)

        gfx.rect(surf, (46, 26, 20), 6, 17, 308, 158)
        gfx.rect(surf, (98, 60, 40), 7, 18, 306, 156)
        gfx.panel(surf, 11, 21, 146, 150, fill=(38, 33, 56), border=PANEL_DARK)
        gfx.panel(surf, 163, 21, 146, 150, fill=(38, 33, 56), border=PANEL_DARK)
        gfx.rect(surf, (58, 34, 24), 157, 19, 6, 154)
        gfx.rect(surf, (126, 82, 54), 159, 20, 2, 152)

        ids = self.entries()
        cat_label = _CATEGORY_LABELS.get(self.category, "ALL")
        gfx.draw_text(surf, "%s (%d)" % (cat_label, len(ids)), 16, 25, DIM)

        for i, sid in enumerate(self.visible_entries()):
            r = self.card_rect(i)
            x, y, w, h = r
            sp = data.PLANTS[sid]
            rcol = data.RARITY_COLORS[sp["rarity"]]
            is_sel = (sid == self.selected)
            hovered = gfx.inside(self.mouse, r)
            border = ACCENT if is_sel else (rcol if hovered else PANEL_DARK)
            fill = (58, 50, 86) if is_sel else ((48, 42, 72) if hovered else (32, 27, 48))
            gfx.rect(surf, border, x, y, w, h)
            gfx.rect(surf, fill, x + 1, y + 1, w - 2, h - 2)
            gfx.rect(surf, rcol, x + 1, y + 1, w - 2, 2)
            gfx.draw_sprite(surf, sp.get("base", sid), x + (w - 24) // 2, y + 3, 2, sp.get("subs"))
            short = sp["name"]
            while len(short) > 1 and gfx.text_width(short) > w - 4:
                short = short[:-1]
            gfx.draw_text(surf, short, x + w // 2, y + 29, TEXT if is_sel else DIM, align="center")

        self.prev_btn.draw(surf, self.mouse)
        self.next_btn.draw(surf, self.mouse)
        gfx.draw_text(surf, "%d / %d" % (self.page + 1, self.pages), 85, 158, DIM, align="center")

        self.mutant_rects = []
        self.base_rect = None
        if self.selected not in data.PLANTS:
            return
        sp = data.PLANTS[self.selected]
        rcol = data.RARITY_COLORS[sp["rarity"]]

        px, py = 168, 26
        gfx.rect(surf, rcol, px, py, 30, 30)
        gfx.rect(surf, (28, 24, 42), px + 1, py + 1, 28, 28)
        gfx.draw_sprite(surf, sp.get("base", self.selected), px + 3, py + 3, 2, sp.get("subs"))

        name_lines = gfx.wrap(sp["name"], 102)
        for k, line in enumerate(name_lines[:2]):
            gfx.draw_text(surf, line, 202, 26 + k * 7, TEXT)
        ry_tag = 26 + min(2, len(name_lines)) * 7 + 1
        gfx.draw_text(surf, sp["rarity"].upper(), 202, ry_tag, rcol)
        gfx.draw_text(surf, "/".join(t.upper() for t in sp["tags"][:3]), 202, ry_tag + 8, DIM)

        gfx.rect(surf, PANEL_DARK, 168, 59, 136, 1)

        dps = sp["yield"] / sp["grow"] if sp["grow"] > 0 else 0
        gfx.draw_text(surf, "GROW TIME:", 168, 63, DIM)
        gfx.draw_text(surf, "%gs" % sp["grow"], 304, 63, TEXT, align="right")
        gfx.draw_text(surf, "HARVEST:", 168, 71, DIM)
        gfx.draw_text(surf, "$%s ($%.1f/S)" % (fmt(sp["yield"]), dps), 304, 71, GOOD, align="right")
        gfx.draw_text(surf, "END-ROUND SELL:", 168, 79, DIM)
        gfx.draw_text(surf, "$%s" % fmt(sp["sell"]), 304, 79, ACCENT, align="right")

        y = 89
        if "nocturnal" in sp["tags"]:
            gfx.draw_text(surf, "NEEDS CELLAR OR ECLIPSE", 168, y, WATER)
            y += 8
        if sp.get("upkeep"):
            gfx.draw_text(surf, "CURSED UPKEEP: -$%s/RND" % fmt(sp["upkeep"]), 168, y, BAD)
            y += 8
        if sp.get("aura") == "jealous":
            gfx.draw_text(surf, "JEALOUS: OTHERS -50% VAL", 168, y, BAD)
            y += 8

        gfx.rect(surf, PANEL_DARK, 168, y + 1, 136, 1)
        y += 5

        if sp.get("mutant"):
            base_id = sp["base"]
            base_name = data.PLANTS[base_id]["name"]
            y += gfx.draw_wrapped(surf, sp.get("desc", ""), 168, y, 136, rcol) * 7 + 3
            btn_r = (168, min(145, y), 136, 13)
            hov = gfx.inside(self.mouse, btn_r)
            gfx.rect(surf, ACCENT if hov else PANEL_LIGHT, *btn_r)
            gfx.rect(surf, (58, 50, 86) if hov else (44, 38, 66), btn_r[0] + 1, btn_r[1] + 1, btn_r[2] - 2, btn_r[3] - 2)
            gfx.draw_text(surf, "< BASE: " + base_name, btn_r[0] + btn_r[2] // 2, btn_r[1] + 4, TEXT, align="center")
            self.base_rect = (base_id, btn_r)
        else:
            packs = [data.PACKS[k]["short"] for k in data.packs_for_plant(self.selected)]
            pack_str = "PACKS: " + (", ".join(packs) if packs else "NONE")
            y += gfx.draw_wrapped(surf, pack_str, 168, y, 136, TEXT) * 7 + 2

            muts = data.mutants_for(self.selected)
            if muts:
                thresh = data.mutation_threshold(self.selected)
                gfx.draw_text(surf, "MUTATIONS (%d+ HARV):" % thresh, 168, y, data.RARITY_COLORS["mutant"])
                y += 8
                for mid in muts[:2]:
                    msp = data.PLANTS[mid]
                    mr = (168, y, 136, 12)
                    hov = gfx.inside(self.mouse, mr)
                    gfx.rect(surf, ACCENT if hov else data.RARITY_COLORS["mutant"], *mr)
                    gfx.rect(surf, (52, 44, 78) if hov else (32, 27, 48), mr[0] + 1, mr[1] + 1, mr[2] - 2, mr[3] - 2)
                    gfx.draw_sprite(surf, sp.get("base", self.selected), mr[0] + 2, mr[1], 1, msp.get("subs"))
                    gfx.draw_text(surf, msp["name"], mr[0] + 16, mr[1] + 4, TEXT)
                    gfx.draw_text(surf, ">", mr[0] + mr[2] - 5, mr[1] + 4, ACCENT, align="right")
                    self.mutant_rects.append((mid, mr))
                    y += 14

        harvested = int(self.app.profile.get("harvested", {}).get(self.selected, 0))
        if self.app.run:
            harvested += int(self.app.run.mastery.get(self.selected, 0))
        gfx.draw_text(surf, "HARVESTED: %s" % fmt(harvested), 236, 163, DIM, align="center")
