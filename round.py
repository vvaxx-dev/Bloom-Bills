import math
from . import data, gfx
from .formatting import clock, fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import (ACCENT, BAD, DIM, CELLAR_PRICE, GOOD, PANEL_DARK, PANEL_LIGHT,
                       SOIL, SOIL_DARK, TEXT, WATER)

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
        self.shovel_mode = False
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
        self.tray_right = Button(202, TRAY_Y + 3, 8, 22, ">", self.scroll_tray_right)
        self.shovel_btn = Button(214, TRAY_Y, 26, 28, "DIG", self.toggle_shovel,
                                 color=PANEL_LIGHT, icon="shovel", icon_scale=1)
        self.buttons = [self.cellar_btn, self.start_btn, self.tray_left, self.tray_right, self.shovel_btn]

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

    def toggle_shovel(self):
        self.shovel_mode = not self.shovel_mode
        if self.shovel_mode:
            self.selected = None
        else:
            self.pick_default()

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
        self.shovel_mode = False
        self.tray_scroll = 0
        self.pick_default()

    def toggle_clock(self):
        run = self.run
        if not run.started:
            run.start_timer()
            self.start_btn.label = "END EARLY"
            self.start_btn.color = (150, 70, 60)
        elif run.time_left > 1.0 and hasattr(self.app, "ask_confirm"):
            self.app.ask_confirm(
                "END ROUND EARLY?",
                "%s LEFT ON THE CLOCK. UNRIPE PLANTS SELL PARTIALLY." % clock(run.time_left),
                run.finish_early,
                confirm_label="END ROUND",
                danger=True,
            )
        else:
            run.finish_early()

    def tray_rect(self, i):
        return (15 + i * 31, TRAY_Y + 3, 31, 22)

    def on_click(self, pos):
        if super().on_click(pos):
            return True
        run = self.run
        for i, sid in enumerate(self.visible_seeds()):
            if inside(pos, self.tray_rect(i)):
                if run.seeds.get(sid, 0) > 0:
                    if run.can_plant(sid, self.in_cellar()):
                        self.shovel_mode = False

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
        in_cellar = self.in_cellar()
        if self.shovel_mode:
            if plots[i].species is None:
                self.app.toast("NOTHING PLANTED HERE")
                return
            plant_name = data.PLANTS[plots[i].species]["name"].upper()

            def do_remove():
                ok, _ = run.remove_plant(i, in_cellar)
                if ok:
                    self.app.toast("REMOVED %s" % plant_name)
                self.shovel_mode = False
                self.pick_default()

            if hasattr(self.app, "ask_confirm"):
                self.app.ask_confirm(
                    "REMOVE %s?" % plant_name,
                    "DIG UP THIS PLANT? THE SEED WILL NOT BE RETURNED.",
                    do_remove,
                    confirm_label="REMOVE",
                    danger=True,
                )
            else:
                do_remove()
            return

        if plots[i].species is None:
            if self.selected and run.plant(i, self.selected, in_cellar):
                if run.seeds.get(self.selected, 0) <= 0:
                    self.pick_default()
            elif not self.selected:
                self.app.toast("NO SEEDS! OPEN PACKS FIRST")
            elif in_cellar:
                self.app.toast("THE CELLAR WATERS ITSELF")
        else:
            if not run.started:
                self.app.toast("PRESS START FIRST (OR USE SHOVEL)")
            elif in_cellar:
                self.app.toast("THE CELLAR WATERS ITSELF")
            else:
                run.water(i)

    def on_key(self, key):
        import pygame
        if key == pygame.K_SPACE and not self.run.started:
            self.toggle_clock()
        elif key == pygame.K_TAB:
            self.cellar_click()
        elif key in (pygame.K_x, pygame.K_DELETE, pygame.K_BACKSPACE):
            self.toggle_shovel()
        elif key == pygame.K_ESCAPE:
            if self.shovel_mode:
                self.shovel_mode = False
                self.pick_default()
            elif hasattr(self.app, "open_pause"):
                self.app.open_pause()
            else:
                self.app.goto("title")
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.scroll_tray(-1 if key == pygame.K_LEFT else 1)
        elif pygame.K_1 <= key <= pygame.K_6:
            seeds = self.view_seeds()
            idx = self.tray_scroll + (key - pygame.K_1)
            if idx < len(seeds):
                sid = seeds[idx]
                if self.run.seeds.get(sid, 0) > 0 and self.run.can_plant(sid, self.in_cellar()):
                    self.shovel_mode = False
                    self.selected = sid

    def _floaters_enabled(self):
        cfg = getattr(self.app, "settings_cfg", None)
        return True if cfg is None else bool(cfg.get("floaters", True))


    def update(self, dt):
        run = self.run
        if run.phase != "round" or not run.started or run.finished or dt <= 0:
            return
        dt = min(dt, run.time_left)
        w = run.compost_window()
        if w > 0 and run.time_left > w > run.time_left - dt:
            first_dt = run.time_left - w
            run._step_round(first_dt)
            if not run.finished and dt - first_dt > 0:
                run._step_round(dt - first_dt)
        else:
            run._step_round(dt)

        if run.finished and not self.ended:
            self.ended = True
            self.app.after_round()

    def draw(self, surf):
        run = self.run
        mouse = self.mouse
        gfx.rect(surf, (30, 26, 46), 0, 0, 320, 180)
        draw_topbar(surf, run, timer=clock(run.time_left), mouse=mouse)


        twist = run.twist()
        if self.shovel_mode:
            msg, col = "SHOVEL ACTIVE: CLICK A PLANTED PLOT TO REMOVE IT (X TO CANCEL).", BAD
        elif twist.get("boss"):
            msg, col = "BOSS: %s! %s" % (twist["name"].upper(),
                                          twist.get("short", twist["desc"]).upper()), BAD
        elif run.twist_id(run.round) != "none":
            msg, col = "%s: %s" % (twist["name"].upper(), twist["desc"].upper()), TONE_COLORS[twist.get("tone", "neutral")]
        elif self.in_cellar():
            msg, col = "THE CELLAR: SELF-WATERING, WEATHERPROOF.", WATER
        elif not run.started:
            msg, col = "WEATHER: FAIR WEATHER - PLANT SEEDS, THEN PRESS START.", DIM
        else:
            msg, col = "FAIR WEATHER - CLICK PLANTS TO WATER THEM.", DIM
        gfx.draw_text(surf, msg, 5, 18, col)

        frac = run.time_left / run.time_total if run.time_total else 0
        compost_now = run.compost_active()
        bar_col = ACCENT if compost_now else (GOOD if frac > 0.25 else BAD)
        gfx.bar(surf, 4, 27, 312, 5, frac, bar_col)

        # plots
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
            hcol = BAD if (self.shovel_mode and plots[hover].species) else ACCENT
            for r in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
                gfx.rect(surf, hcol, *r)

        for fx, fy, text, color, age in self.floaters:
            gfx.draw_text(surf, text, fx, fy - age * 14, color, align="center", shadow=(20, 16, 28))

        gfx.panel(surf, 244, 36, 72, 110, "RELICS")
        relic_hover = None
        for i, rid in enumerate(run.relics):
            ry = 48 + i * 9
            plus = " +" if run.relic_level(rid) > 0 else ""
            active_tag = " *" if (rid == "compost" and compost_now) else ""
            rcol = GOOD if (rid == "compost" and compost_now) else data.RARITY_COLORS[data.RELICS[rid]["rarity"]]
            gfx.draw_text(surf, data.RELICS[rid]["name"] + plus + active_tag, 248, ry, rcol)
            if 244 <= mouse[0] < 316 and ry - 1 <= mouse[1] < ry + 7:
                relic_hover = rid
        if not run.relics:
            gfx.draw_wrapped(surf, "NO RELICS YET. BUY THEM IN THE SHOP.", 248, 48, 64, DIM)
        gfx.draw_text(surf, "SPEED x%.2f" % run.growth_speed(), 248, 110, TEXT)
        gfx.draw_text(surf, "WATER %ds" % run.water_time(), 248, 120, WATER)
        gfx.draw_text(surf, "SEEDS: %d" % sum(run.seeds.values()), 248, 130, TEXT)

        # Seed tray + Shovel button
        gfx.panel(surf, 4, TRAY_Y, 208, 28)
        seeds = self.view_seeds()
        visible = self.visible_seeds()
        seed_hover = None
        for i, sid in enumerate(visible):
            r = self.tray_rect(i)
            count = run.seeds.get(sid, 0)
            usable = count > 0 and run.can_plant(sid, self.in_cellar())
            border = ACCENT if (sid == self.selected and not self.shovel_mode) else PANEL_DARK
            gfx.rect(surf, border, *r)
            gfx.rect(surf, (54, 47, 80) if usable else (36, 31, 56), r[0] + 1, r[1] + 1, r[2] - 2, r[3] - 2)
            gfx.draw_sprite(surf, sid, r[0] + 1, r[1] + 5, 1)
            gfx.draw_text(surf, "x%d" % count, r[0] + 14, r[1] + 3, TEXT if usable else DIM)
            gfx.draw_text(surf, str(i + 1), r[0] + 14, r[1] + 13, DIM)
            if inside(mouse, r):
                seed_hover = sid
        if len(seeds) > TRAY_SLOTS:
            self.tray_left.enabled = self.tray_scroll > 0
            self.tray_right.enabled = self.tray_scroll < self.max_scroll()
            self.tray_left.draw(surf, mouse)
            self.tray_right.draw(surf, mouse)

            self.shovel_btn.active = self.shovel_mode
        self.shovel_btn.border_color = BAD
        self.shovel_btn.color = (140, 62, 58) if self.shovel_mode else PANEL_LIGHT
        self.shovel_btn.draw(surf, mouse)

        self.cellar_btn.label = "CELLAR (TAB)" if run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
        self.cellar_btn.color = (96, 70, 140) if run.cellar_unlocked else (70, 130, 70)
        self.cellar_btn.draw(surf, mouse)
        self.start_btn.label = "END EARLY" if run.started else "START (SPACE)"
        self.start_btn.color = (150, 70, 60) if run.started else (70, 130, 70)
        self.start_btn.draw(surf, mouse)

        # tooltips
        if relic_hover:
            rel = data.RELICS[relic_hover]
            lv = run.relic_level(relic_hover)
            lines = [(rel["name"] + (" +%d" % lv if lv else ""), data.RARITY_COLORS[rel["rarity"]]),
                     (rel["desc"], TEXT)]
            if relic_hover == "compost":
                if compost_now:
                    lines.append(("ACTIVE NOW: X2 VALUE! (%.1FS)" % run.time_left, GOOD))
                else:
                    lines.append(("ACTIVATES IN FINAL 15S", ACCENT))
            for step in rel.get("levels", [])[:lv]:
                lines.append((step["desc"], GOOD))
            for step in rel.get("levels", [])[lv:]:
                lines.append(("%s AT %d %s" % ("EVOLVES", step["goal"], step["stat"].upper() + "S"), DIM))
            gfx.tooltip(surf, lines, mouse, 102)
        elif self.shovel_btn.hover(mouse):
            gfx.tooltip(surf, [
                ("SHOVEL (X)", ACCENT),
                ("REMOVE A PLANTED CROP FROM A PLOT.", TEXT),
            ], mouse, 104)
        elif hover is not None and plots[hover].species:
            self.plot_tooltip(surf, hover)
        elif seed_hover is not None:
            sp = data.PLANTS[seed_hover]
            lines = [
                (sp["name"], data.RARITY_COLORS[sp["rarity"]]),
                ("GROW: %gS   HARVEST: $%s" % (sp["grow"], fmt(sp["yield"])), TEXT),
                ("SELL AT END: $%s" % fmt(sp["sell"]), ACCENT),
            ]
            gfx.tooltip(surf, lines, mouse, 104)
        elif 4 <= mouse[0] < 316 and 16 <= mouse[1] < 27:
            tcol = BAD if twist.get("boss") else TONE_COLORS.get(twist.get("tone", "neutral"), TEXT)
            gfx.tooltip(surf, [
                ("WEATHER: " + twist["name"].upper(), tcol),
                (twist["desc"], TEXT),
            ], mouse, 112)

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
            if not self.shovel_mode and self.selected and inside(self.mouse, (x, y, w, h)):
                gfx.draw_sprite(surf, "seed", x + 22, y + 10, 1)
                gfx.draw_text(surf, "PLANT", x + w // 2, y + 24, TEXT, align="center")
            return
        sp = data.PLANTS[p.species]
        frac = min(1.0, p.progress / sp["grow"])
        sway = 1 if (run.started and math.sin(self.t * 3 + i) > 0.6) else 0
        sprite_name = gfx.plant_sprite_name(sp.get("base", p.species), frac)
        gfx.draw_sprite(surf, sprite_name, x + 16 + sway, y + 1, 2, sp.get("subs"))
        gfx.bar(surf, x + 4, y + 28, w - 8, 3, frac, sp["color"])
        if self.shovel_mode and inside(self.mouse, (x, y, w, h)):
            gfx.rect(surf, (120, 36, 36), x + 8, y + 11, w - 16, 11)
            gfx.draw_text(surf, "REMOVE", x + w // 2, y + 14, TEXT, align="center")
        elif p.water_left > 0:
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
        if self.in_cellar():
            speed = (1.0 + run._sum("growth")) * 0.75
        mutant_col = data.RARITY_COLORS["mutant"]
        color = mutant_col if sp.get("mutant") else data.RARITY_COLORS[sp["rarity"]]
        lines = [(sp["name"], color)]
        if self.shovel_mode:
            lines.append(("CLICK TO REMOVE CROP", BAD))
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
        if run.compost_active():
            lines.append(("COMPOST HEAP: X2 ACTIVE!", GOOD))
        lines += [
            ("HARVEST: $" + fmt(run.harvest_value(i, self.in_cellar())), ACCENT),
            ("RIPE IN: %.1fs" % max(0.0, (sp["grow"] - p.progress) / max(speed, 0.01)), TEXT),
            ("HARVESTED: %d" % count, DIM),
        ]
        if nxt:
            lines.append(("DOUBLES AT %d" % nxt, DIM))
        elif not sp.get("mutant") and data.mutants_for(p.species):
            lines.append(("MAY MUTATE AT %d+ HARVESTS" % data.mutation_threshold(p.species), mutant_col))
        gfx.tooltip(surf, lines, self.mouse, 88)
