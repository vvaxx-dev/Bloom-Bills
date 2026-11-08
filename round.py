import math
from . import data, gfx
from .formatting import clock, fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import (ACCENT, BAD, DIM, CELLAR_PRICE, GOOD, PANEL_DARK, SOIL, SOIL_DARK,
                       TEXT, WATER)

CELL_W, CELL_H, GAP = 56, 34, 4
GRID_X, GRID_Y = 4, 36
TRAY_Y = 148
TRAY_SLOTS = 6

TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": DIM}

def plot_rect(i):
    return (GRID_X + (i % 4) * (CELL_W + GAP), GRID_Y + (i // 4) * (CELL_H + GAP), CELL_W, CELL_H)


def inside(pos, r):
    return r[0] <= pos[0] < r[0] + r[2] and r[1] <= pos[1] < r[1] + r[3]


class RoundScene(Scene):
    def on_enter(self):
        self.run.begin_round()
        self.floaters = []
        self.selected = None
        self.fast = 1
        self.t = 0.0
        self.ended = False
        self.view = "surface"
        self.tray_scroll = 0
        self.pick_default()
        self.cellar_btn = Button(244, 148, 72, 13, "", self.cellar_click)
        self.cellar_btn.label = "CELLAR (TAB)" if self.run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
        self.start_btn = Button(244, 163, 72, 14, "START (SPACE)", self.toggle_clock, color=(70, 130, 70))
        self.tray_left = Button(6, TRAY_Y + 3, 8, 22, "<", self.scroll_tray_left)
        self.tray_right = Button(228, TRAY_Y + 3, 8, 22, ">", self.scroll_tray_right)
        self.buttons = [self.cellar_btn, self.start_btn, self.tray_left, self.tray_right]

    def plant_list(self):
        return self.run.cellar_plots if self.view == "cellar" else self.run.plots

    def view_seeds(self):
        """Every seed plantable in the current view, in a fixed order so the
        tray can page through it. An eclipse unlocks nocturnal seeds up top,
        which is a screenful more than fits."""
        if self.in_cellar():
            return list(data.NOCTURNAL_PLANTS)
        seeds = list(data.SURFACE_PLANTS)
        if self.run.twist().get("eclipse"):
            seeds += [sid for sid in data.NOCTURNAL_PLANTS if sid not in seeds]
        return seeds

    def in_cellar(self):
        return self.view == "cellar"

     # -------------------------------------------------------- tray paging
    def max_scroll(self):
        return max(0, len(self.view_seeds()) - TRAY_SLOTS)

    def clamp_scroll(self):
        self.tray_scroll = max(0, min(self.tray_scroll, self.max_scroll()))

    def scroll_tray(self, delta):
        self.tray_scroll += delta
        self.clamp_scroll()

    def scroll_tray_left(self):
        self.scroll_tray(-1)

    def scroll_tray_right(self):
        self.scroll_tray(1)

    def on_wheel(self, dy):
        self.scroll_tray(-1 if dy > 0 else 1)

    def ensure_visible(self, sid):
        """Bring a seed into view (used when the game picks one for you)."""
        seeds = self.view_seeds()
        if sid not in seeds:
            return
        i = seeds.index(sid)
        if i < self.tray_scroll:
            self.tray_scroll = i
        elif i >= self.tray_scroll + TRAY_SLOTS:
            self.tray_scroll = i - TRAY_SLOTS + 1
        self.clamp_scroll()

    def visible_seeds(self):
        seeds = self.view_seeds()
        start = min(self.tray_scroll, max(0, len(seeds) - TRAY_SLOTS))
        return seeds[start:start + TRAY_SLOTS]

    def pick_default(self):
        run = self.run
        for sid in reversed(self.view_seeds()):
            if run.seeds.get(sid, 0) > 0 and run.can_plant(sid, self.in_cellar()):
                self.selected = sid
                self.ensure_visible(sid)
                return
        self.selected = None

    def cellar_click(self):
        run = self.run
        if not run.cellar_unlocked:
            if run.money >= CELLAR_PRICE:
                run.buy_cellar()
                self.app.toast("THE CELLAR IS OPEN! NO WATER, NO WEATHER.", 3.0)
                self.app.save_run()
            else:
                self.app.toast("DIGGING COSTS $%d" % CELLAR_PRICE)
            self.cellar_btn.label = "CELLAR (TAB)" if run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
            return
        self.view = "cellar" if self.view == "surface" else "surface"
        self.tray_scroll = 0
        self.pick_default()

    def toggle_clock(self):
        run = self.run
        if not run.started:
            run.start_timer()
            self.start_btn.label = "END EARLY"
            self.start_btn.color = (150, 70, 60)
        else:
            run.finish_early()

    def tray_rect(self, i):
        return (16 + i * 35, TRAY_Y + 3, 35, 22)

    def on_click(self, pos):
        if super().on_click(pos):
            return True
        run = self.run
        for i, sid in enumerate(self.visible_seeds()):
            if inside(pos, self.tray_rect(i)):
                if run.seeds.get(sid, 0) > 0:
                    if run.can_plant(sid, self.in_cellar()):
                        self.selected = sid
                    else:
                        self.app.toast(self.plant_block_reason(sid))
                else:
                    self.app.toast("NO %s SEEDS - OPEN A PACK" % data.PLANTS[sid]["name"].upper())
                return True
        plots = self.plant_list()
        for i in range(len(plots)):
            if inside(pos, plot_rect(i)):
                self.click_plot(i)
                return True
        return False

    def plant_block_reason(self, sid):
        sp = data.PLANTS[sid]
        if self.in_cellar() and "nocturnal" not in sp["tags"]:
            return "ONLY NOCTURNAL PLANTS GROW DOWN HERE"
        if "nocturnal" in sp["tags"]:
            return "NEEDS DARK: CELLAR OR ECLIPSE"
        return "%s: CAN'T PLANT THAT" % self.run.twist()["name"].upper()


    def click_plot(self, i):
        run = self.run
        plots = self.plant_list()
        if plots[i].species is None:
            if self.selected and run.plant(i, self.selected, self.in_cellar()):
                if run.seeds.get(self.selected, 0) <= 0:
                    self.pick_default()
            elif not self.selected:
                self.app.toast("NO SEEDS! OPEN PACKS FIRST")
            elif self.in_cellar():
                self.app.toast("THE CELLAR WATERS ITSELF")
        else:
            if not run.started:
                self.app.toast("PRESS START FIRST")
            elif self.in_cellar():
                self.app.toast("THE CELLAR WATERS ITSELF")
            else:
                run.water(i)

    def on_key(self, key):
        import pygame
        if key == pygame.K_SPACE and not self.run.started:
            self.toggle_clock()
        elif key == pygame.K_TAB:
            self.cellar_click()
        elif key == pygame.K_ESCAPE:
            self.app.goto("title")
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.scroll_tray(-1 if key == pygame.K_LEFT else 1)
        elif pygame.K_1 <= key <= pygame.K_6:
            seeds = self.view_seeds()
            idx = self.tray_scroll + (key - pygame.K_1)
            if idx < len(seeds):
                sid = seeds[idx]
                if self.run.seeds.get(sid, 0) > 0 and self.run.can_plant(sid, self.in_cellar()):
                    self.selected = sid

    def update(self, dt):
        self.t += dt
        self.tray_left.enabled = self.tray_scroll > 0
        self.tray_right.enabled = self.tray_scroll < self.max_scroll()
        run = self.run
        run.update(dt * self.fast)
        for ev in run.events:
            if ev["kind"] == "evolve":
                self.app.toast("%s EVOLVED! %s" % (ev["name"].upper(), ev["desc"].upper()), 3.0)
                continue
            if bool(ev.get("cellar")) != self.in_cellar():
                continue  
            x, y, w, _h = plot_rect(ev["plot"]) if ev["plot"] < 12 else (0, 0, 0, 0)
            if ev["kind"] == "harvest":
                self.floaters.append([x + w // 2, y + 8, "+$" + fmt(ev["amount"]), ACCENT, 0.0])
            elif ev["kind"] == "mutate":
                self.floaters.append([x + w // 2, y + 8, "MUTATED!", data.RARITY_COLORS["mutant"], 0.0])
                self.app.toast("%s MUTATED!" % ev["name"].upper(), 2.5)
            elif ev["kind"] == "wither":
                self.floaters.append([x + w // 2, y + 8, "WITHERED!", BAD, 0.0])
            elif ev["kind"] == "hail":
                self.floaters.append([x + w // 2, y + 8, "HAIL!", WATER, 0.0])
            elif ev["kind"] == "rot":
                self.floaters.append([x + w // 2, y + 8, "ROT!", BAD, 0.0])
                self.app.toast("%s ROTTED!" % ev.get("name", "A PLANT").upper(), 2.0)
            elif ev["kind"] == "eaten":
                self.floaters.append([x + w // 2, y + 8, "EATEN!", BAD, 0.0])
                self.app.toast("A CROW ATE YOUR %s!" % ev["name"].upper(), 2.0)
        run.events.clear()
        for f in self.floaters:
            f[4] += dt
        self.floaters = [f for f in self.floaters if f[4] < 1.0]
        if run.finished and not self.ended:
            self.ended = True
            self.app.after_round()

    def draw(self, surf):
        run = self.run
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run, timer=clock(run.time_left))

        twist = run.twist()
        if twist.get("boss"):
            msg, col = "BOSS: %s! %s" % (twist["name"].upper(),
                                          twist.get("short", twist["desc"]).upper()), BAD
        elif run.twist_id(run.round) != "none":
            msg, col = "%s: %s" % (twist["name"].upper(), twist["desc"].upper()), TONE_COLORS[twist.get("tone", "neutral")]
        elif self.in_cellar():
            msg, col = "THE CELLAR: SELF-WATERING, WEATHERPROOF.", WATER

        elif not run.started:
            msg, col = "PLANT SEEDS, THEN PRESS START.", DIM
        else:
            msg, col = "CLICK PLANTS TO WATER THEM.", DIM
        gfx.draw_text(surf, msg, 5, 18, col)
        frac = run.time_left / run.time_total if run.time_total else 0
        gfx.bar(surf, 4, 27, 312, 5, frac, GOOD if frac > 0.25 else BAD)

        # plots
        mouse = self.mouse
        hover = None
        plots = self.plant_list()
        for i in range(12):
            x, y, w, h = plot_rect(i)
            if i >= len(plots):
                gfx.rect(surf, PANEL_DARK, x, y, w, h)
                gfx.draw_text(surf, "LOCKED", x + w // 2, y + 14, (70, 62, 96), align="center")
                continue
            self.draw_plot(plots, surf, i, x, y, w, h)
            if inside(mouse, (x, y, w, h)):
                hover = i
        if hover is not None:
            x, y, w, h = plot_rect(hover)
            for r in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
                gfx.rect(surf, ACCENT, *r)

        for fx, fy, text, color, age in self.floaters:
            gfx.draw_text(surf, text, fx, fy - age * 14, color, align="center", shadow=(20, 16, 28))

        gfx.panel(surf, 244, 36, 72, 110, "RELICS")
        relic_hover = None
        for i, rid in enumerate(run.relics):
            ry = 48 + i * 9
            plus = " +" if run.relic_level(rid) > 0 else ""
            gfx.draw_text(surf, data.RELICS[rid]["name"] + plus, 248, ry, data.RARITY_COLORS[data.RELICS[rid]["rarity"]])
            if 244 <= mouse[0] < 316 and ry - 1 <= mouse[1] < ry + 7:
                relic_hover = rid
        if not run.relics:
            gfx.draw_wrapped(surf, "NO RELICS YET. BUY THEM IN THE SHOP.", 248, 48, 64, DIM)
        gfx.draw_text(surf, "SPEED x%.2f" % run.growth_speed(), 248, 110, TEXT)
        gfx.draw_text(surf, "WATER %ds" % run.water_time(), 248, 120, WATER)
        gfx.draw_text(surf, "SEEDS: %d" % sum(run.seeds.values()), 248, 130, TEXT)

        gfx.panel(surf, 4, TRAY_Y, 236, 28)
        seeds = self.view_seeds()
        visible = self.visible_seeds()
        for i, sid in enumerate(visible):
            r = self.tray_rect(i)
            count = run.seeds.get(sid, 0)
            usable = count > 0 and run.can_plant(sid, self.in_cellar())
            border = ACCENT if sid == self.selected else PANEL_DARK
            gfx.rect(surf, border, *r)
            gfx.rect(surf, (54, 47, 80) if usable else (36, 31, 56), r[0] + 1, r[1] + 1, r[2] - 2, r[3] - 2)
            gfx.draw_sprite(surf, sid, r[0] + 2, r[1] + 5, 1)
            gfx.draw_text(surf, "x%d" % count, r[0] + 16, r[1] + 3, TEXT if usable else DIM)
            gfx.draw_text(surf, str(i + 1), r[0] + 16, r[1] + 13, DIM)
        if len(seeds) > TRAY_SLOTS:
            self.tray_left.enabled = self.tray_scroll > 0
            self.tray_right.enabled = self.tray_scroll < self.max_scroll()
            self.tray_left.draw(surf, mouse)
            self.tray_right.draw(surf, mouse)
        self.cellar_btn.label = "CELLAR (TAB)" if run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
        self.cellar_btn.color = (96, 70, 140) if run.cellar_unlocked else (70, 130, 70)
        self.cellar_btn.draw(surf, mouse)
        self.start_btn.draw(surf, mouse)

        # tooltips
        if relic_hover:
            rel = data.RELICS[relic_hover]
            lv = run.relic_level(relic_hover)
            lines = [(rel["name"] + (" +%d" % lv if lv else ""), data.RARITY_COLORS[rel["rarity"]]),
                     (rel["desc"], TEXT)]
            for step in rel.get("levels", [])[:lv]:
                lines.append((step["desc"], GOOD))
            for step in rel.get("levels", [])[lv:]:
                lines.append(("%s AT %d %s" % ("EVOLVES", step["goal"], step["stat"].upper() + "S"), DIM))
            gfx.tooltip(surf, lines, mouse, 96)
        elif hover is not None and plots[hover].species:
            self.plot_tooltip(surf, hover)

    def draw_plot(self, plots, surf, i, x, y, w, h):
        run = self.run
        p = plots[i]
        cellar = self.in_cellar()
        top, bottom = (SOIL_DARK, (66, 48, 38)) if cellar else (SOIL_DARK, SOIL)
        gfx.rect(surf, top, x, y, w, h)
        gfx.rect(surf, bottom, x + 1, y + 1, w - 2, h - 2)
        for k in range(6):
            gfx.rect(surf, SOIL_DARK, x + 3 + (i * 7 + k * 11) % 50, y + 3 + (i * 5 + k * 13) % 28, 2, 1)
        if p.species is None:
            if self.selected and inside(self.mouse, (x, y, w, h)):
                gfx.draw_sprite(surf, "seed", x + 22, y + 10, 1)
                gfx.draw_text(surf, "PLANT", x + w // 2, y + 24, TEXT, align="center")
            return
        sp = data.PLANTS[p.species]
        frac = min(1.0, p.progress / sp["grow"])
        sway = 1 if (run.started and math.sin(self.t * 3 + i) > 0.6) else 0
        sprite_name = gfx.plant_sprite_name(sp.get("base", p.species), frac)
        gfx.draw_sprite(surf, sprite_name, x + 16 + sway, y + 1, 2, sp.get("subs"))
        gfx.bar(surf, x + 4, y + 28, w - 8, 3, frac, sp["color"])
        if p.water_left > 0:
            gfx.draw_sprite(surf, "drop", x + w - 9, y + 3)
        elif not cellar and run.can_water(i):
            gfx.draw_sprite(surf, "drop", x + w - 9, y + 3, 1, {"c": (96, 112, 140), "w": (130, 142, 170)})

    def plot_tooltip(self, surf, i):
        run = self.run
        plots = self.plant_list()
        p = plots[i]
        sp = data.PLANTS[p.species]
        count = run.mastery.get(p.species, 0)
        nxt = next((t for t in data.MILESTONES if count < t), None)
        speed = run.growth_speed() * (2.0 if p.water_left > 0 else 1.0)
        mutant_col = data.RARITY_COLORS["mutant"]
        if self.in_cellar():
            speed = (1.0 + run._sum("growth")) * 0.75
        mutant_col = data.RARITY_COLORS["mutant"]
        color = mutant_col if sp.get("mutant") else data.RARITY_COLORS[sp["rarity"]]
        lines = [(sp["name"], color)]
        if sp.get("mutant"):
            lines.append(("MUTANT: " + sp["desc"], mutant_col))
        if "nocturnal" in sp["tags"]:
            lines.append(("NOCTURNAL", WATER))
        if sp.get("upkeep"):
            lines.append(("CURSED: -$%d UPKEEP AT ROUND END" % sp["upkeep"], BAD))
        if "aura" in sp:
            lines.append(("CURSED: OTHER PLANTS -50%", BAD))
        if self.in_cellar():
            lines.append(("CELLAR: SELF-WATERING", WATER))
        lines += [
            ("HARVEST: $" + fmt(run.harvest_value(i, self.in_cellar())), ACCENT),
            ("RIPE IN: %.1fs" % max(0.0, (sp["grow"] - p.progress) / max(speed, 0.01)), TEXT),
            ("HARVESTED: %d" % count, DIM),
        ]
        if nxt:
            lines.append(("DOUBLES AT %d" % nxt, DIM))
        elif not sp.get("mutant") and data.mutants_for(p.species):
            lines.append(("MAY MUTATE AT %d+ HARVESTS" % data.mutation_threshold(p.species), mutant_col))
        gfx.tooltip(surf, lines, self.mouse, 84)
