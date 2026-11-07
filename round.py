
import math

from . import data, gfx
from .formatting import clock, fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import (ACCENT, BAD, DIM, GOOD, PANEL_DARK, SOIL, SOIL_DARK,
                       TEXT, WATER)

CELL_W, CELL_H, GAP = 56, 34, 4
GRID_X, GRID_Y = 4, 36
TRAY_Y = 148


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
        self.pick_default()
        self.start_btn = Button(244, TRAY_Y, 72, 28, "START (SPACE)", self.toggle_clock, color=(70, 130, 70))
        self.buttons = [self.start_btn]

    def pick_default(self):
        run = self.run
        for sid in reversed(data.PLANT_ORDER):
            if run.seeds.get(sid, 0) > 0 and run.can_plant(sid):
                self.selected = sid
                return
        self.selected = None

    def toggle_clock(self):
        run = self.run
        if not run.started:
            run.start_timer()
            self.start_btn.label = "END EARLY"
            self.start_btn.color = (150, 70, 60)
        else:
            run.finish_early()

    def tray_rect(self, i):
        return (8 + i * 38, TRAY_Y + 3, 36, 22)

    def on_click(self, pos):
        if super().on_click(pos):
            return True
        run = self.run
        for i, sid in enumerate(data.PLANT_ORDER):
            if inside(pos, self.tray_rect(i)):
                if run.seeds.get(sid, 0) > 0:
                    if run.can_plant(sid):
                        self.selected = sid
                    else:
                        self.app.toast("%s: CAN'T PLANT THAT" % run.twist()["name"].upper())
                return True
        for i in range(len(run.plots)):
            if inside(pos, plot_rect(i)):
                self.click_plot(i)
                return True
        return False

    def click_plot(self, i):
        run = self.run
        if run.plots[i].species is None:
            if self.selected and run.plant(i, self.selected):
                if run.seeds.get(self.selected, 0) <= 0:
                    self.pick_default()
            elif not self.selected:
                self.app.toast("NO SEEDS! OPEN PACKS FIRST")
        else:
            if not run.started:
                self.app.toast("PRESS START FIRST")
            else:
                run.water(i)

    def on_key(self, key):
        import pygame
        if key == pygame.K_SPACE and not self.run.started:
            self.toggle_clock()
        elif key == pygame.K_ESCAPE:
            self.app.goto("title")
        elif pygame.K_1 <= key <= pygame.K_6:
            idx = key - pygame.K_1
            sid = data.PLANT_ORDER[idx]
            if self.run.seeds.get(sid, 0) > 0 and self.run.can_plant(sid):
                self.selected = sid

    def update(self, dt):
        self.t += dt
        run = self.run
        run.update(dt * self.fast)
        for ev in run.events:
            x, y, w, h = plot_rect(ev["plot"]) if ev["plot"] < 12 else (0, 0, 0, 0)
            if ev["kind"] == "harvest":
                self.floaters.append([x + w // 2, y + 8, "+$" + fmt(ev["amount"]), ACCENT, 0.0])
            elif ev["kind"] == "mutate":
                self.floaters.append([x + w // 2, y + 8, "MUTATED!", data.RARITY_COLORS["mutant"], 0.0])
                self.app.toast("%s MUTATED!" % ev["name"].upper(), 2.5)
            elif ev["kind"] == "wither":
                self.floaters.append([x + w // 2, y + 8, "WITHERED!", BAD, 0.0])
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
        draw_topbar(surf, run)

        twist = run.twist()
        if run.is_quota_round(run.round):
            msg, col = "%s: %s" % (twist["name"].upper(), twist["desc"].upper()), BAD
        elif not run.started:
            msg, col = "PLANT SEEDS, THEN PRESS START.", DIM
        else:
            msg, col = "CLICK PLANTS TO WATER THEM.", DIM
        gfx.draw_text(surf, msg, 5, 18, col)
        gfx.draw_text(surf, clock(run.time_left), 315, 18, TEXT, align="right")
        frac = run.time_left / run.time_total if run.time_total else 0
        gfx.bar(surf, 4, 27, 312, 5, frac, GOOD if frac > 0.25 else BAD)

        # plots
        mouse = self.mouse
        hover = None
        for i in range(12):
            x, y, w, h = plot_rect(i)
            if i >= len(run.plots):
                gfx.rect(surf, PANEL_DARK, x, y, w, h)
                gfx.draw_text(surf, "LOCKED", x + w // 2, y + 14, (70, 62, 96), align="center")
                continue
            self.draw_plot(surf, i, x, y, w, h)
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
            gfx.draw_text(surf, data.RELICS[rid]["name"], 248, ry, data.RARITY_COLORS[data.RELICS[rid]["rarity"]])
            if 244 <= mouse[0] < 316 and ry - 1 <= mouse[1] < ry + 7:
                relic_hover = rid
        if not run.relics:
            gfx.draw_wrapped(surf, "NO RELICS YET. BUY THEM IN THE SHOP.", 248, 48, 64, DIM)
        gfx.draw_text(surf, "SPEED x%.2f" % run.growth_speed(), 248, 110, TEXT)
        gfx.draw_text(surf, "WATER %ds" % run.water_time(), 248, 120, WATER)
        gfx.draw_text(surf, "SEEDS: %d" % sum(run.seeds.values()), 248, 130, TEXT)

        gfx.panel(surf, 4, TRAY_Y, 236, 28)
        for i, sid in enumerate(data.PLANT_ORDER):
            r = self.tray_rect(i)
            count = run.seeds.get(sid, 0)
            usable = count > 0 and run.can_plant(sid)
            border = ACCENT if sid == self.selected else PANEL_DARK
            gfx.rect(surf, border, *r)
            gfx.rect(surf, (54, 47, 80) if usable else (36, 31, 56), r[0] + 1, r[1] + 1, r[2] - 2, r[3] - 2)
            gfx.draw_sprite(surf, sid, r[0] + 2, r[1] + 5, 1)
            gfx.draw_text(surf, "x%d" % count, r[0] + 16, r[1] + 3, TEXT if usable else DIM)
            gfx.draw_text(surf, str(i + 1), r[0] + 16, r[1] + 13, DIM)
        self.start_btn.draw(surf, mouse)

        # tooltips
        if relic_hover:
            rel = data.RELICS[relic_hover]
            gfx.tooltip(surf, [(rel["name"], data.RARITY_COLORS[rel["rarity"]]), (rel["desc"], TEXT)],
                        (mouse[0] - 100, mouse[1]), 96)
        elif hover is not None and run.plots[hover].species:
            self.plot_tooltip(surf, hover)

    def draw_plot(self, surf, i, x, y, w, h):
        run = self.run
        p = run.plots[i]
        gfx.rect(surf, SOIL_DARK, x, y, w, h)
        gfx.rect(surf, SOIL, x + 1, y + 1, w - 2, h - 2)
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
        elif run.can_water(i):
            gfx.draw_sprite(surf, "drop", x + w - 9, y + 3, 1, {"c": (96, 112, 140), "w": (130, 142, 170)})

    def plot_tooltip(self, surf, i):
        run = self.run
        p = run.plots[i]
        sp = data.PLANTS[p.species]
        count = run.mastery.get(p.species, 0)
        nxt = next((t for t in data.MILESTONES if count < t), None)
        speed = run.growth_speed() * (2.0 if p.water_left > 0 else 1.0)
        mutant_col = data.RARITY_COLORS["mutant"]
        lines = [
            (sp["name"], mutant_col if sp.get("mutant") else data.RARITY_COLORS[sp["rarity"]]),
        ]
        if sp.get("mutant"):
            lines.append(("MUTANT: " + sp["desc"], mutant_col))
        lines += [
            ("HARVEST: $" + fmt(run.harvest_value(i)), ACCENT),
            ("RIPE IN: %.1fs" % max(0.0, (sp["grow"] - p.progress) / speed), TEXT),
            ("HARVESTED: %d" % count, DIM),
        ]
        if nxt:
            lines.append(("DOUBLES AT %d" % nxt, DIM))
        elif not sp.get("mutant") and data.mutants_for(p.species):
            lines.append(("MAY MUTATE AT %d+ HARVESTS" % data.mutation_threshold(p.species), mutant_col))
        gfx.tooltip(surf, lines, self.mouse, 84)
