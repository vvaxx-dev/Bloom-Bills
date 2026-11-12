"""Garden index for plants and permanent run upgrades."""

import pygame

from . import data, gfx
from .formatting import fmt
from .gfx import Button
from .scene import Scene
from .settings import ACCENT, BAD, CANVAS_H, CANVAS_W, DIM, GOOD, PANEL_DARK, PANEL_LIGHT, TEXT, WATER

GRID_COLS, GRID_ROWS = 3, 3
PER_PAGE = GRID_COLS * GRID_ROWS

# The book has two large top-level sections. Each section exposes its own
# smaller index tabs on the left page.
SECTIONS = [
    ("plants", "PLANTS"),
    ("upgrades", "UPGRADES"),
]
_SECTION_LABELS = dict(SECTIONS)

CATEGORIES = [
    ("all", "ALL"),
    ("garden", "GARDEN"),
    ("desert", "DESERT"),
    ("farmer", "FARMER"),
    ("night", "NIGHT"),
    ("mutant", "MUTANTS"),
]
UPGRADE_SUBSECTIONS = [
    ("relics", "RELICS"),
    ("heirlooms", "HEIRLOOMS"),
]

_GARDEN_PLANTS = [sid for sid in data.SURFACE_PLANTS if sid not in data.FARMER_PLANTS]
_DESERT_PLANTS = [sid for sid in data.SURFACE_PLANTS if "desert" in data.PLANTS[sid]["tags"]]


def _category_ids(cat):
    """Return the plant ids in one garden-index category."""
    if cat == "garden":
        return list(_GARDEN_PLANTS)
    if cat == "desert":
        return list(_DESERT_PLANTS)
    if cat == "farmer":
        return list(data.FARMER_PLANTS)
    if cat == "night":
        return list(data.NOCTURNAL_PLANTS)
    if cat == "mutant":
        return list(data.MUTANTS)
    return list(data.PLANT_ORDER) + list(data.MUTANTS)


def _shorten(text, width):
    text = str(text)
    while len(text) > 1 and gfx.text_width(text) > width:
        text = text[:-1]
    return text


class IndexScene(Scene):
    """A garden book split into Plants and Upgrades, each with index tabs."""

    @property
    def entry_type(self):
        """The kind of cards currently shown on the left page."""
        return "plants" if self.section == "plants" else self.subsection

    def on_enter(self):
        self.section = "plants"
        self.subsection = "all"
        # `category` is retained as a compatibility alias for older tools.
        self.category = self.subsection
        self.page = 0
        self.selected = data.PLANT_ORDER[0]
        self.subsection_by_section = {"plants": "all", "upgrades": "relics"}
        self.selected_by_section = {
            "plants": self.selected,
            "relics": data.RELIC_ORDER[0],
            "heirlooms": data.PERK_ORDER[0],
        }
        self.selected_by_view = {
            ("plants", "all"): self.selected,
            ("upgrades", "relics"): data.RELIC_ORDER[0],
            ("upgrades", "heirlooms"): data.PERK_ORDER[0],
        }

        self.section_buttons = []
        for x, w, (sid, label) in zip((74, 121), (44, 54), SECTIONS):
            button = Button(x, 2, w, 13, label, lambda s=sid: self.set_section(s))
            button.sid = sid
            self.section_buttons.append(button)
        # Older integrations called the top controls tab_buttons.
        self.tab_buttons = self.section_buttons

        self.plant_subsection_buttons = []
        for index, (sid, label) in enumerate(CATEGORIES):
            col, row = index % 3, index // 3
            button = Button(
                16 + col * 46, 21 + row * 14, 43, 12, label,
                lambda s=sid: self.set_subsection(s),
            )
            button.subsection = sid
            self.plant_subsection_buttons.append(button)

        self.upgrade_subsection_buttons = []
        for x, (sid, label) in zip((16, 85), UPGRADE_SUBSECTIONS):
            button = Button(x, 22, 67, 13, label, lambda s=sid: self.set_subsection(s))
            button.subsection = sid
            self.upgrade_subsection_buttons.append(button)

        self.subsection_buttons = self.plant_subsection_buttons
        self.back_btn = Button(279, 2, 37, 13, "BACK", lambda: self.app.goto("title"), color=(130, 70, 70))
        self.prev_btn = Button(18, 154, 20, 13, "<", self.prev_page)
        self.next_btn = Button(132, 154, 20, 13, ">", self.next_page)
        self.mutant_rects = []
        self.base_rect = None
        self.t = 0.0
        self.buttons = []
        self.sync()

    def update(self, dt):
        self.t = getattr(self, "t", 0.0) + dt

    def subsections(self):
        return CATEGORIES if self.section == "plants" else UPGRADE_SUBSECTIONS

    def filters(self):
        """Compatibility alias: index filters are now visible subsection tabs."""
        return self.subsections()

    def entries(self):
        if self.entry_type == "plants":
            return _category_ids(self.subsection)
        if self.entry_type == "relics":
            return list(data.RELIC_ORDER)
        return list(data.PERK_ORDER)

    @property
    def pages(self):
        return max(1, (len(self.entries()) + PER_PAGE - 1) // PER_PAGE)

    def _remember_selection(self):
        if self.selected is None:
            return
        self.selected_by_view[(self.section, self.subsection)] = self.selected
        self.selected_by_section[self.entry_type] = self.selected

    def _restore_selection(self):
        ids = self.entries()
        wanted = self.selected_by_view.get(
            (self.section, self.subsection), self.selected_by_section.get(self.entry_type),
        )
        self.selected = wanted if wanted in ids else (ids[0] if ids else None)
        if self.selected is not None:
            self.selected_by_view[(self.section, self.subsection)] = self.selected
            self.selected_by_section[self.entry_type] = self.selected

    def set_section(self, section):
        # Preserve the old programmatic calls while exposing only the two
        # requested top-level tabs in the actual interface.
        if section in ("relics", "heirlooms"):
            if self.section != "upgrades":
                self.set_section("upgrades")
            self.set_subsection(section)
            return
        if section not in _SECTION_LABELS:
            return
        if section == self.section:
            self.sync()
            return
        self._remember_selection()
        self.subsection_by_section[self.section] = self.subsection
        self.section = section
        self.subsection = self.subsection_by_section[section]
        self.category = self.subsection
        self.page = 0
        self._restore_selection()
        self.sync()

    def set_subsection(self, subsection):
        if subsection not in dict(self.subsections()):
            return
        if subsection == self.subsection:
            self.sync()
            return
        self._remember_selection()
        self.subsection = subsection
        self.category = subsection
        self.subsection_by_section[self.section] = subsection
        self.page = 0
        self._restore_selection()
        self.sync()

    def set_category(self, category):
        """Compatibility alias for selecting a plant subsection."""
        self.set_subsection(category)

    def cycle_subsection(self, direction):
        choices = self.subsections()
        if len(choices) <= 1:
            return
        ids = [sid for sid, _label in choices]
        current = ids.index(self.subsection) if self.subsection in ids else 0
        self.set_subsection(ids[(current + direction) % len(ids)])

    def cycle_filter(self, direction):
        self.cycle_subsection(direction)

    def select_plant(self, sid):
        """Focus a plant, switching section/subsection/page if it is hidden."""
        if sid not in data.PLANTS:
            return
        if self.section != "plants":
            self.set_section("plants")
        self.selected = sid
        ids = self.entries()
        if sid not in ids:
            self.subsection = "mutant" if data.PLANTS[sid].get("mutant") else "all"
            self.category = self.subsection
            self.subsection_by_section["plants"] = self.subsection
            ids = self.entries()
        if sid in ids:
            self.page = ids.index(sid) // PER_PAGE
        self.selected_by_section["plants"] = sid
        self.selected_by_view[("plants", self.subsection)] = sid
        self.sync()

    def prev_page(self):
        self.page = max(0, self.page - 1)
        self.sync()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.sync()

    def sync(self):
        valid_subsections = [sid for sid, _label in self.subsections()]
        if self.subsection not in valid_subsections:
            self.subsection = valid_subsections[0]
        self.category = self.subsection
        ids = self.entries()
        if ids and self.selected not in ids:
            self._restore_selection()
        self.page = max(0, min(self.page, self.pages - 1))
        self.prev_btn.enabled = self.page > 0
        self.next_btn.enabled = self.page < self.pages - 1

        for button in self.section_buttons:
            button.active = button.sid == self.section
            button.border_color = ACCENT
            button.color = (84, 68, 120) if button.active else PANEL_LIGHT

        self.subsection_buttons = (
            self.plant_subsection_buttons if self.section == "plants"
            else self.upgrade_subsection_buttons
        )
        for button in self.plant_subsection_buttons + self.upgrade_subsection_buttons:
            button.active = button in self.subsection_buttons and button.subsection == self.subsection
            button.border_color = ACCENT
            if button.active:
                button.color = (66, 96, 68) if self.section == "plants" else (84, 68, 120)
            else:
                button.color = PANEL_LIGHT

        self.buttons = (
            self.section_buttons + [self.back_btn] + self.subsection_buttons
            + [self.prev_btn, self.next_btn]
        )

    def visible_entries(self):
        ids = self.entries()
        start = self.page * PER_PAGE
        return ids[start:start + PER_PAGE]

    def card_rect(self, i):
        row, col = divmod(i, GRID_COLS)
        return (16 + col * 46, 50 + row * 34, 43, 32)

    def on_wheel(self, dy):
        if dy > 0:
            self.prev_page()
        elif dy < 0:
            self.next_page()

    def on_click(self, pos):
        if super().on_click(pos):
            return True
        for i, entry_id in enumerate(self.visible_entries()):
            if gfx.inside(pos, self.card_rect(i)):
                self.selected = entry_id
                self._remember_selection()
                return True
        if self.entry_type == "plants":
            for mutant_id, rect in self.mutant_rects:
                if gfx.inside(pos, rect):
                    self.select_plant(mutant_id)
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
        elif key == pygame.K_UP:
            self.cycle_subsection(-1)
        elif key == pygame.K_DOWN:
            self.cycle_subsection(1)
        elif key == pygame.K_TAB:
            ids = [sid for sid, _label in SECTIONS]
            self.set_section(ids[(ids.index(self.section) + 1) % len(ids)])

    def _level(self, key):
        if self.app.run:
            return self.app.run.perk(key)
        return int(self.app.profile.get("perks", {}).get(key, 0))

    def _card_meta(self, entry_id):
        if self.entry_type == "plants":
            meta = data.PLANTS[entry_id]
            return (
                meta["name"], meta.get("art", meta.get("base", entry_id)), meta.get("subs"),
                data.RARITY_COLORS[meta["rarity"]], "",
            )
        if self.entry_type == "relics":
            meta = data.RELICS[entry_id]
            return meta["name"], entry_id, None, data.RARITY_COLORS[meta["rarity"]], ""
        perk = data.PERKS[entry_id]
        level = self._level(entry_id)
        color = GOOD if level else (104, 94, 132)
        return perk["name"], perk["art"], None, color, "%d/%d" % (level, perk["max"])

    def _draw_book(self, surf):
        gfx.rect(surf, (46, 26, 20), 6, 17, 308, 158)
        gfx.rect(surf, (98, 60, 40), 7, 18, 306, 156)
        gfx.panel(surf, 11, 19, 146, 152, fill=(38, 33, 56), border=PANEL_DARK)
        gfx.panel(surf, 163, 19, 146, 152, fill=(38, 33, 56), border=PANEL_DARK)
        gfx.rect(surf, (58, 34, 24), 157, 18, 6, 154)
        gfx.rect(surf, (126, 82, 54), 159, 19, 2, 152)

    def _draw_cards(self, surf):
        for i, entry_id in enumerate(self.visible_entries()):
            x, y, w, h = self.card_rect(i)
            name, art, subs, color, badge = self._card_meta(entry_id)
            selected = entry_id == self.selected
            hovered = gfx.inside(self.mouse, (x, y, w, h))
            border = ACCENT if selected else (color if hovered else PANEL_DARK)
            fill = (58, 50, 86) if selected else ((48, 42, 72) if hovered else (32, 27, 48))
            gfx.rect(surf, border, x, y, w, h)
            gfx.rect(surf, fill, x + 1, y + 1, w - 2, h - 2)
            gfx.rect(surf, color, x + 1, y + 1, w - 2, 2)

            if self.entry_type == "plants":
                meta = data.PLANTS[entry_id]
                anim = gfx.plant_anim(
                    getattr(self, "t", 0.0), index=i,
                    style=gfx.plant_anim_style(entry_id, meta, art),
                    started=selected, hovered=hovered,
                )
                gfx.draw_sprite(surf, art, x + (w - 24) // 2, y + 2, 2, subs, anim=anim)
            else:
                bob = -1 if hovered else 0
                gfx.draw_sprite(surf, art, x + (w - 24) // 2, y + 2 + bob, 2, subs)

            if badge:
                gfx.draw_text(surf, badge, x + w - 2, y + 3, GOOD if badge != "0/0" else DIM, align="right")
            gfx.draw_text(
                surf, _shorten(name, w - 4), x + w // 2, y + 26,
                TEXT if selected else DIM, align="center",
            )

    def draw(self, surf):
        gfx.rect(surf, (28, 24, 42), 0, 0, CANVAS_W, CANVAS_H)
        gfx.draw_sprite(surf, "book", 5, 2, 1)
        gfx.draw_text(surf, "GARDEN INDEX", 22, 6, ACCENT)
        for button in self.section_buttons:
            button.draw(surf, self.mouse)
        self.back_btn.draw(surf, self.mouse)

        self._draw_book(surf)
        for button in self.subsection_buttons:
            button.draw(surf, self.mouse)
        if self.section == "upgrades":
            label = dict(UPGRADE_SUBSECTIONS).get(self.subsection, "UPGRADES")
            gfx.draw_text(surf, "%s (%d)" % (label, len(self.entries())), 84, 40, DIM, align="center")
        self._draw_cards(surf)

        self.prev_btn.draw(surf, self.mouse)
        self.next_btn.draw(surf, self.mouse)
        gfx.draw_text(
            surf, "%d / %d  (%d)" % (self.page + 1, self.pages, len(self.entries())),
            85, 158, DIM, align="center",
        )

        self.mutant_rects = []
        self.base_rect = None
        if self.entry_type == "plants":
            self._draw_plant_detail(surf)
        elif self.entry_type == "relics":
            self._draw_relic_detail(surf)
        else:
            self._draw_heirloom_detail(surf)

    def _draw_detail_icon(self, surf, art, color, subs=None):
        px, py = 168, 26
        gfx.rect(surf, color, px, py, 30, 30)
        gfx.rect(surf, (28, 24, 42), px + 1, py + 1, 28, 28)
        gfx.draw_sprite(surf, art, px + 3, py + 3, 2, subs)

    def _draw_plant_detail(self, surf):
        if self.selected not in data.PLANTS:
            return
        sp = data.PLANTS[self.selected]
        rcol = data.RARITY_COLORS[sp["rarity"]]
        art = sp.get("art", sp.get("base", self.selected))

        px, py = 168, 26
        gfx.rect(surf, rcol, px, py, 30, 30)
        gfx.rect(surf, (28, 24, 42), px + 1, py + 1, 28, 28)
        anim = gfx.plant_anim(
            getattr(self, "t", 0.0), index=0,
            style=gfx.plant_anim_style(self.selected, sp, art),
            started=True, glow=(sp.get("base", self.selected) == "mycelium"),
        )
        gfx.draw_sprite(surf, art, px + 3, py + 3, 2, sp.get("subs"), anim=anim)

        name_lines = gfx.wrap(sp["name"], 102)
        for row, line in enumerate(name_lines[:2]):
            gfx.draw_text(surf, line, 202, 26 + row * 7, TEXT)
        tag_y = 26 + min(2, len(name_lines)) * 7 + 1
        gfx.draw_text(surf, sp["rarity"].upper(), 202, tag_y, rcol)
        gfx.draw_text(surf, "/".join(tag.upper() for tag in sp["tags"][:3]), 202, tag_y + 8, DIM)
        gfx.rect(surf, PANEL_DARK, 168, 59, 136, 1)

        dps = sp["yield"] / sp["grow"] if sp["grow"] > 0 else 0
        pays = sp.get("pays", True) is not False
        gfx.draw_text(surf, "GROW TIME:", 168, 63, DIM)
        gfx.draw_text(surf, "%gs" % sp["grow"], 304, 63, TEXT, align="right")
        gfx.draw_text(surf, "HARVEST:", 168, 71, DIM)
        payout = "$%s ($%.1f/S)" % (fmt(sp["yield"]), dps) if pays else "$0 (NO PAYOUT)"
        gfx.draw_text(surf, payout, 304, 71, GOOD if pays else DIM, align="right")
        gfx.draw_text(surf, "END-ROUND SELL:", 168, 79, DIM)
        gfx.draw_text(surf, "$%s" % fmt(sp["sell"]), 304, 79, ACCENT, align="right")

        y = 89
        if "nocturnal" in sp["tags"]:
            gfx.draw_text(surf, "NEEDS CELLAR OR ECLIPSE", 168, y, WATER)
            y += 8
        if "fungus" in sp["tags"]:
            gfx.draw_text(surf, "GROWS TOP OR IN CELLAR", 168, y, WATER)
            y += 8
        if sp.get("upkeep"):
            gfx.draw_text(surf, "CURSED UPKEEP: -$%s/RND" % fmt(sp["upkeep"]), 168, y, BAD)
            y += 8
        if sp.get("aura") == "jealous":
            gfx.draw_text(surf, "JEALOUS: OTHERS -50% VAL", 168, y, BAD)
            y += 8
        if not pays:
            gfx.draw_text(surf, "PAYS NOTHING ITSELF", 168, y, ACCENT)
            y += 8
        if sp.get("note"):
            y += gfx.draw_wrapped(surf, sp["note"], 168, y, 136, GOOD) * 7 + 1

        gfx.rect(surf, PANEL_DARK, 168, y + 1, 136, 1)
        y += 5
        if sp.get("mutant"):
            base_id = sp["base"]
            y += gfx.draw_wrapped(surf, sp.get("desc", ""), 168, y, 136, rcol) * 7 + 3
            button_rect = (168, min(145, y), 136, 13)
            hovered = gfx.inside(self.mouse, button_rect)
            gfx.rect(surf, ACCENT if hovered else PANEL_LIGHT, *button_rect)
            gfx.rect(
                surf, (58, 50, 86) if hovered else (44, 38, 66),
                button_rect[0] + 1, button_rect[1] + 1, button_rect[2] - 2, button_rect[3] - 2,
            )
            gfx.draw_text(
                surf, "< BASE: " + data.PLANTS[base_id]["name"],
                button_rect[0] + button_rect[2] // 2, button_rect[1] + 4, TEXT, align="center",
            )
            self.base_rect = (base_id, button_rect)
        else:
            packs = [data.PACKS[key]["short"] for key in data.packs_for_plant(self.selected)]
            y += gfx.draw_wrapped(
                surf, "PACKS: " + (", ".join(packs) if packs else "NONE"), 168, y, 136, TEXT,
            ) * 7 + 2
            mutants = data.mutants_for(self.selected)
            if mutants and y < 148:
                gfx.draw_text(
                    surf, "MUTATIONS (%d+ HARV):" % data.mutation_threshold(self.selected),
                    168, y, data.RARITY_COLORS["mutant"],
                )
                y += 8
                for mutant_id in mutants[:2]:
                    if y + 12 > 168:
                        break
                    mutant = data.PLANTS[mutant_id]
                    rect = (168, y, 136, 12)
                    hovered = gfx.inside(self.mouse, rect)
                    gfx.rect(surf, ACCENT if hovered else data.RARITY_COLORS["mutant"], *rect)
                    gfx.rect(
                        surf, (52, 44, 78) if hovered else (32, 27, 48),
                        rect[0] + 1, rect[1] + 1, rect[2] - 2, rect[3] - 2,
                    )
                    gfx.draw_sprite(surf, mutant.get("art", mutant.get("base", self.selected)), rect[0] + 2, rect[1], 1, mutant.get("subs"))
                    gfx.draw_text(surf, mutant["name"], rect[0] + 16, rect[1] + 4, TEXT)
                    gfx.draw_text(surf, ">", rect[0] + rect[2] - 5, rect[1] + 4, ACCENT, align="right")
                    self.mutant_rects.append((mutant_id, rect))
                    y += 14

        harvested = int(self.app.profile.get("harvested", {}).get(self.selected, 0))
        if self.app.run:
            harvested += int(self.app.run.mastery.get(self.selected, 0))
        gfx.draw_text(surf, "HARVESTED: %s" % fmt(harvested), 236, 163, DIM, align="center")

    def _draw_relic_detail(self, surf):
        if self.selected not in data.RELICS:
            return
        relic = data.RELICS[self.selected]
        color = data.RARITY_COLORS[relic["rarity"]]
        self._draw_detail_icon(surf, self.selected, color)

        name_lines = gfx.wrap(relic["name"], 102)
        for row, line in enumerate(name_lines[:2]):
            gfx.draw_text(surf, line, 202, 26 + row * 7, TEXT)
        tag_y = 26 + min(2, len(name_lines)) * 7 + 1
        gfx.draw_text(surf, relic["rarity"].upper(), 202, tag_y, color)
        gfx.draw_text(surf, "BASE $%s" % fmt(relic["cost"]), 202, tag_y + 8, ACCENT)
        gfx.rect(surf, PANEL_DARK, 168, 59, 136, 1)

        y = 64
        if self.app.run:
            owned = self.selected in self.app.run.relics
            level = self.app.run.relic_level(self.selected) if owned else 0
            status = "OWNED" + (" +%d" % level if level else "") if owned else "NOT OWNED"
            gfx.draw_text(surf, status, 168, y, GOOD if owned else DIM)
            gfx.draw_text(surf, "NOW $%s" % fmt(self.app.run.relic_price(self.selected)), 304, y, ACCENT, align="right")
            y += 9
        y += gfx.draw_wrapped(surf, relic["desc"], 168, y, 136, TEXT) * 7 + 3

        levels = relic.get("levels", [])
        if levels:
            gfx.draw_text(surf, "EVOLUTIONS", 168, y, color)
            y += 8
            for level_no, step in enumerate(levels[:2], 1):
                if y > 148:
                    break
                gfx.draw_text(
                    surf, "+%d AT %d %sS" % (level_no, step["goal"], step["stat"].upper()),
                    168, y, ACCENT,
                )
                y += 7
                y += gfx.draw_wrapped(surf, step["desc"], 168, y, 136, GOOD) * 7 + 2
        else:
            gfx.draw_text(surf, "NO EVOLUTION - FULL POWER IMMEDIATELY", 168, min(y, 150), DIM)
        gfx.draw_text(surf, "RELIC %d / %d" % (data.RELIC_ORDER.index(self.selected) + 1, len(data.RELIC_ORDER)), 236, 163, DIM, align="center")

    def _draw_heirloom_detail(self, surf):
        if self.selected not in data.PERKS:
            return
        perk = data.PERKS[self.selected]
        level = self._level(self.selected)
        color = GOOD if level else ACCENT
        self._draw_detail_icon(surf, perk["art"], color)

        name_lines = gfx.wrap(perk["name"], 102)
        for row, line in enumerate(name_lines[:2]):
            gfx.draw_text(surf, line, 202, 26 + row * 7, TEXT)
        tag_y = 26 + min(2, len(name_lines)) * 7 + 1
        gfx.draw_text(surf, "PERMANENT HEIRLOOM", 202, tag_y, ACCENT)
        gfx.draw_text(surf, "LEVEL %d / %d" % (level, perk["max"]), 202, tag_y + 8, GOOD if level else DIM)
        gfx.rect(surf, PANEL_DARK, 168, 59, 136, 1)

        y = 64
        y += gfx.draw_wrapped(surf, perk.get("lore", perk["desc"]), 168, y, 136, TEXT) * 7 + 3
        gfx.draw_text(surf, "BONUS", 168, y, ACCENT)
        y += 8
        current = data.perk_text(self.selected, level) if level else "UNOWNED"
        y += gfx.draw_wrapped(surf, "NOW: " + current, 168, y, 136, GOOD if level else DIM) * 7 + 2
        if level < perk["max"]:
            next_bonus = data.perk_text(self.selected, level + 1)
            cost = data.perk_cost(self.selected, level)
            y += gfx.draw_wrapped(
                surf, "NEXT: %s (%d HEIRLOOMS)" % (next_bonus, cost), 168, y, 136, ACCENT,
            ) * 7 + 2
        else:
            gfx.draw_text(surf, "MAXED OUT", 168, y, GOOD)
            y += 9

        if y < 147:
            max_bonus = data.perk_text(self.selected, perk["max"])
            y += gfx.draw_wrapped(surf, "MAX: " + max_bonus, 168, y, 136, WATER) * 7 + 2
        if y < 154:
            gfx.draw_text(surf, perk["desc"], 168, y, DIM)
        gfx.draw_text(
            surf, "BANKED: %s" % fmt(self.app.profile.get("heirlooms", 0)),
            236, 163, ACCENT, align="center",
        )
