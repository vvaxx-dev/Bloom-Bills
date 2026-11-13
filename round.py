"""Live growing round screen: planting, watering, shoveling, cellar toggle, and relic sidebar."""

import math
import pygame

from . import ambient, data, gfx
from .formatting import clock, fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import (
    ACCENT, BAD, BG, CANVAS_H, CANVAS_W, CELLAR_PRICE, COLS, DIM, GOOD,
    MAX_PLOTS, MYCELIUM_CREEP_TIME, PANEL_DARK, PANEL_LIGHT, SOIL, SOIL_DARK,
    TEXT, WATER,)

CELL_W, CELL_H, GAP = 56, 34, 4
GRID_X, GRID_Y = 4, 36
TRAY_Y = 148
TRAY_SLOTS = 6

TONE_COLORS = {"good": GOOD, "bad": BAD, "neutral": DIM}


def plot_rect(i):
    return (GRID_X + (i % COLS) * (CELL_W + GAP), GRID_Y + (i // COLS) * (CELL_H + GAP), CELL_W, CELL_H)


class RoundScene(Scene):
    def on_enter(self):
        self.run.begin_round()
        self.floaters = []
        self.selected = None
        self.shovel_mode = False
        self.choose_mode = False
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
        self.tray_right = Button(202, TRAY_Y + 3, 8, 22, ">", self.scroll_tray_right)
        self.shovel_btn = Button(
            214, TRAY_Y, 26, 28, "DIG", self.toggle_shovel,
            color=(86, 72, 102), icon="shovel", icon_scale=1, hover_subs=gfx.SHOVEL_HOVER_SUBS,
        )
        self.ambient = ambient.GardenAmbient(self.run)
        self.buttons = [self.cellar_btn, self.start_btn, self.tray_left, self.tray_right,
                        self.shovel_btn]
        self._sync_tray_buttons()

    def _ambient(self):
        amb = getattr(self, "ambient", None)
        if amb is None:
            amb = ambient.GardenAmbient(self.run)
            self.ambient = amb
        return amb

    def _sync_tray_buttons(self):
        self.tray_left.enabled = self.tray_scroll > 0
        self.tray_right.enabled = self.tray_scroll < self.max_scroll()

    def in_cellar(self):
        return self.view == "cellar"

    def plant_list(self):
        return self.run.cellar_plots if self.in_cellar() else self.run.plots

    def view_seeds(self):
        """Return plantable species for the active board; Eclipse adds nocturnal seeds to the surface tray."""
        if self.in_cellar():
            return list(data.CELLAR_PLANTS)
        seeds = list(data.SURFACE_PLANTS)
        if self.run.twist().get("eclipse"):
            seeds += [sid for sid in data.NOCTURNAL_PLANTS if sid not in seeds]
        return seeds

    def toggle_shovel(self):
        self.shovel_mode = not self.shovel_mode
        if self.shovel_mode:
            self.choose_mode = False
            self.selected = None
        else:
            self.pick_default()

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
        """Auto-select the highest-tier owned seed that can grow on the active board."""
        run = self.run
        cellar = self.in_cellar()
        for sid in reversed(self.view_seeds()):
            if run.seeds.get(sid, 0) > 0 and run.can_plant(sid, cellar):
                self.selected = sid
                self.ensure_visible(sid)
                return
        self.selected = None

    def cellar_click(self):
        run = self.run
        if not run.cellar_unlocked:
            if run.buy_cellar():
                self.app.toast("THE CELLAR IS OPEN! NO WATER, NO WEATHER.", 3.0)
                self.app.save_run()
            else:
                self.app.toast("DIGGING COSTS $%d" % CELLAR_PRICE)
            self.cellar_btn.label = "CELLAR (TAB)" if run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
            return
        self.view = "surface" if self.in_cellar() else "cellar"
        self.shovel_mode = False
        self.tray_scroll = 0
        self.pick_default()
        self._sync_tray_buttons()

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
        if "chosen_bloom" in run.relics:
            idx = run.relics.index("chosen_bloom")
            if gfx.inside(pos, (244, 47 + idx * 9, 72, 9)):
                if run.chosen_plant is None:
                    self.choose_mode = not self.choose_mode
                    self.shovel_mode = False
                    self.app.toast("CLICK A PLANTED PLOT TO CHOOSE IT")
                else:
                    self.app.toast("ALREADY CHOSEN THIS ROUND")
                return True
        for i, sid in enumerate(self.visible_seeds()):
            if gfx.inside(pos, self.tray_rect(i)):
                if run.seeds.get(sid, 0) > 0:
                    # Highlight any owned seed, even one this board cannot grow
                    # right now, so its numbers are always readable.
                    self.shovel_mode = False
                    self.choose_mode = False
                    self.selected = sid
                    if not run.can_plant(sid, self.in_cellar()):
                        self.app.toast(self.plant_block_reason(sid))
                else:
                    self.app.toast("NO %s SEEDS - OPEN A PACK" % data.PLANTS[sid]["name"].upper())
                return True
        plots = self.plant_list()
        for i in range(len(plots)):
            if gfx.inside(pos, plot_rect(i)):
                self.click_plot(i)
                return True
        return False

    def plant_block_reason(self, sid):
        sp = data.PLANTS[sid]
        if self.in_cellar() and "nocturnal" not in sp["tags"] and "fungus" not in sp["tags"]:
            return "ONLY NOCTURNAL PLANTS AND FUNGI GROW DOWN HERE"
        if "nocturnal" in sp["tags"]:
            return "NEEDS DARK: CELLAR OR ECLIPSE"
        return "%s: CAN'T PLANT THAT" % self.run.twist()["name"].upper()

    def click_plot(self, i):
        run = self.run
        plots = self.plant_list()
        in_cellar = self.in_cellar()
        if self.choose_mode:
            if run.choose_plant(i, in_cellar):
                self.choose_mode = False
                self.app.toast("CHOSEN: 50% FASTER, X2 HARVEST!")
            else:
                self.app.toast("CHOOSE A PLANTED PLOT")
            return
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
            if self.selected:
                if run.plant(i, self.selected, in_cellar):
                    if run.seeds.get(self.selected, 0) <= 0:
                        self.pick_default()
                else:
                    self.app.toast(self.plant_block_reason(self.selected))
            else:
                self.app.toast("NO SEEDS! OPEN PACKS FIRST")
        elif not run.started:
            self.app.toast("PRESS START FIRST (OR USE SHOVEL)")
        elif run.harvest(i, in_cellar):
            pass
        elif in_cellar:
            self.app.toast("THE CELLAR WATERS ITSELF")
        else:
            run.water(i)

    def on_key(self, key):
        if key == pygame.K_SPACE and not self.run.started:
            self.toggle_clock()
        elif key == pygame.K_TAB:
            self.cellar_click()
        elif key in (pygame.K_x, pygame.K_DELETE, pygame.K_BACKSPACE):
            self.toggle_shovel()
        elif key == pygame.K_ESCAPE:
            if self.choose_mode:
                self.choose_mode = False
            elif self.shovel_mode:
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
                if self.run.seeds.get(sid, 0) > 0:
                    self.shovel_mode = False
                    self.selected = sid

    def _floaters_enabled(self):
        cfg = getattr(self.app, "settings_cfg", None)
        return True if cfg is None else bool(cfg.get("floaters", True))

    def update(self, dt):
        self.t += dt
        self._sync_tray_buttons()
        run = self.run
        run.auto_harvest = bool(getattr(self.app, "settings_cfg", {}).get("auto_harvest", False))
        run.update(dt * self.fast)
        self._ambient().update(dt * self.fast, run, self.in_cellar())
        show_floaters = self._floaters_enabled()

        for ev in run.events:
            kind = ev["kind"]
            if kind == "evolve":
                self.app.toast("%s EVOLVED! %s" % (ev["name"].upper(), ev["desc"].upper()), 3.0)
                continue
            if kind == "weather_clear":
                self.app.toast("CLEAR SKIES! WEATHER AND BOSS EFFECTS CLEARED.", 3.0)
                continue
            if kind == "compost":
                self.app.toast("COMPOST HEAP! X2 VALUE FOR FINAL %dS!" % ev["window"], 2.5)
                continue
            if bool(ev.get("cellar")) != self.in_cellar():
                continue
            x, y, w, _h = plot_rect(ev["plot"]) if ev["plot"] < MAX_PLOTS else (0, 0, 0, 0)
            fx, fy = x + w // 2, y + 8
            if kind == "harvest":
                if show_floaters and ev["amount"] > 0:
                    self.floaters.append([fx, fy, "+$" + fmt(ev["amount"]), ACCENT, 0.0])
            elif kind == "mutate":
                if show_floaters:
                    self.floaters.append([fx, fy, "MUTATED!", data.RARITY_COLORS["mutant"], 0.0])
                self.app.toast("%s MUTATED!" % ev["name"].upper(), 2.5)
            elif kind == "wither":
                if show_floaters:
                    self.floaters.append([fx, fy, "WITHERED!", BAD, 0.0])
            elif kind == "hail":
                if show_floaters:
                    self.floaters.append([fx, fy, "HAIL!", WATER, 0.0])
            elif kind == "rot":
                if show_floaters:
                    self.floaters.append([fx, fy, "ROT!", BAD, 0.0])
                self.app.toast("%s ROTTED!" % ev.get("name", "A PLANT").upper(), 2.0)
            elif kind == "ghost_swap":
                other = ev.get("other_plot", -1)
                if show_floaters:
                    self.floaters.append([fx, fy, "SWAPPED!", (186, 134, 244), 0.0])
                    if 0 <= other < MAX_PLOTS:
                        ox, oy, ow, _oh = plot_rect(other)
                        self.floaters.append([ox + ow // 2, oy + 8, "SWAPPED!", (186, 134, 244), 0.0])
                self.app.toast(
                    "THE GHOST SWAPPED %s AND %s!"
                    % (ev.get("first_name", "TWO PLANTS").upper(), ev.get("second_name", "").upper()),
                    2.0,
                )
            elif kind == "eaten":
                if show_floaters:
                    self.floaters.append([fx, fy, "EATEN!", BAD, 0.0])
                self.app.toast("A CROW ATE YOUR %s!" % ev["name"].upper(), 2.0)
            elif kind == "spread":
                if show_floaters:
                    self.floaters.append([fx, fy, "SPREAD!", GOOD, 0.0])
                parent = ev.get("source")
                if parent is not None and parent < len(self.plant_list()):
                        px, py, pw, _ph = plot_rect(parent)
                        self.floaters.append([px + pw // 2, py + 8, "SPAWNED", GOOD, 0.0])
                self.app.toast(
                    "MYCELIUM SPREAD! PATCH OF %d (+%d%%)"
                    % (ev.get("size", 2), round(100 * (self.run.network_share(ev.get("size", 2)) - 1))),
                    2.0,
                )
            elif kind == "devour":
                if show_floaters:
                    self.floaters.append([fx, fy, "EATEN!", BAD, 0.0])
                self.app.toast(
                    "A MAN-EATER ATE YOUR %s! +$%d BASE" % (ev["name"].upper(), ev.get("gained", 0)), 2.0)
            elif kind == "bloom":
                if show_floaters:
                    self.floaters.append([fx, fy, "LUCKY!", GOOD, 0.0])
                self.app.toast(
                    "LUCKY CLOVER! %s IS X%g FOR THE ROUND." % (ev["name"].upper(), ev.get("mult", 1.5)), 2.0)
        run.events.clear()

        if show_floaters:
            for f in self.floaters:
                f[4] += dt
            self.floaters = [f for f in self.floaters if f[4] < 1.0]
        else:
            self.floaters.clear()

        if run.finished and not self.ended:
            self.ended = True
            self.app.after_round()

    def draw(self, surf):
        run = self.run
        mouse = self.mouse
        gfx.rect(surf, BG, 0, 0, CANVAS_W, CANVAS_H)
        draw_topbar(surf, run, timer=clock(run.time_left), mouse=mouse)

        twist = run.twist()
        if self.choose_mode:
            msg, col = "CHOOSE ONE PLANTED PLOT (ESC TO CANCEL).", ACCENT
        elif self.shovel_mode:
            msg, col = "SHOVEL ACTIVE: CLICK A PLANTED PLOT TO REMOVE IT (X TO CANCEL).", BAD
        elif twist.get("boss"):
            msg = "BOSS: %s! %s" % (twist["name"].upper(), twist.get("short", twist["desc"]).upper())
            col = BAD
        elif not run.weather_cleared and run.twist_id(run.round) != "none":
            msg = "%s: %s" % (twist["name"].upper(), twist["desc"].upper())
            col = TONE_COLORS[twist.get("tone", "neutral")]
        elif self.in_cellar():
            msg, col = "THE CELLAR: SELF-WATERING, WEATHERPROOF.", WATER
        elif not run.started:
            msg, col = "WEATHER: FAIR WEATHER - PLANT SEEDS, THEN PRESS START.", DIM
        else:
            msg, col = "CLICK TO WATER; CLICK MATURE PLANTS TO HARVEST.", DIM
        gfx.draw_text(surf, msg, 5, 18, col)

        frac = run.time_left / run.time_total if run.time_total else 0
        compost_now = run.compost_active()
        bar_col = ACCENT if compost_now else (GOOD if frac > 0.25 else BAD)
        gfx.bar(surf, 4, 27, 312, 5, frac, bar_col)

        hover = None
        plots = self.plant_list()
        amb = self._ambient()
        amb.draw_foliage(surf, run, cellar=self.in_cellar(), plot_rects=())

        for i in range(MAX_PLOTS):
            r = plot_rect(i)
            x, y, w, h = r
            if i >= len(plots):
                gfx.rect(surf, PANEL_DARK, x, y, w, h)
                gfx.draw_text(surf, "LOCKED", x + w // 2, y + 14, (70, 62, 96), align="center")
                continue
            self.draw_plot(plots, surf, i, x, y, w, h)
            if gfx.inside(mouse, r):
                hover = i

        # Keep the soil lanes clean; seasonal art lives in the topbar while
        # sparse autumn leaves and winter snow pass over the garden itself.
        amb.draw_foreground(surf, run, cellar=self.in_cellar())

        if hover is not None:
            x, y, w, h = plot_rect(hover)
            hcol = BAD if (self.shovel_mode and plots[hover].species) else ACCENT
            for edge in ((x, y, w, 1), (x, y + h - 1, w, 1), (x, y, 1, h), (x + w - 1, y, 1, h)):
                gfx.rect(surf, hcol, *edge)

        for fx, fy, text, color, age in self.floaters:
            gfx.draw_text(surf, text, fx, fy - age * 14, color, align="center", shadow=(20, 16, 28))

        gfx.panel(surf, 244, 36, 72, 110, "RELICS")
        relic_hover = None
        for i, rid in enumerate(run.relics):
            ry = 48 + i * 9
            plus = " +" if run.relic_level(rid) > 0 else ""
            active_tag = " *" if (rid == "compost" and compost_now) or (rid == "chosen_bloom" and run.chosen_plant is None) else ""
            rcol = GOOD if (rid == "compost" and compost_now) else data.RARITY_COLORS[data.RELICS[rid]["rarity"]]
            gfx.draw_text(surf, data.RELICS[rid]["name"] + plus + active_tag, 248, ry, rcol)
            if gfx.inside(mouse, (244, ry - 1, 72, 8)):
                relic_hover = rid
        if not run.relics:
            gfx.draw_wrapped(surf, "NO RELICS YET. BUY THEM IN THE SHOP.", 248, 48, 64, DIM)
        if "chosen_bloom" in run.relics and run.chosen_plant is None:
            gfx.draw_text(surf, "* CLICK RELIC", 248, 102, ACCENT)
        gfx.draw_text(surf, "SPEED x%.2f" % run.growth_speed(), 248, 110, TEXT)
        gfx.draw_text(surf, "WATER %ds" % run.water_time(), 248, 120, WATER)
        gfx.draw_text(surf, "SEEDS: %d" % sum(run.seeds.values()), 248, 130, TEXT)
        # Resale lives on the packs screen now; a nudge here keeps players from
        # hunting for a sell button in the middle of a round.
        gfx.draw_text(surf, "SELL IN PACKS", 248, 138, DIM)

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
            if gfx.inside(mouse, r):
                seed_hover = sid
        if len(seeds) > TRAY_SLOTS:
            self._sync_tray_buttons()
            self.tray_left.draw(surf, mouse)
            self.tray_right.draw(surf, mouse)

        self.shovel_btn.active = self.shovel_mode
        self.shovel_btn.border_color = BAD
        self.shovel_btn.color = (148, 62, 58) if self.shovel_mode else (86, 72, 102)
        self.shovel_btn.draw(surf, mouse)

        self.cellar_btn.label = "CELLAR (TAB)" if run.cellar_unlocked else "DIG $%d" % CELLAR_PRICE
        self.cellar_btn.color = (96, 70, 140) if run.cellar_unlocked else (70, 130, 70)
        self.cellar_btn.draw(surf, mouse)
        self.start_btn.label = "END EARLY" if run.started else "START (SPACE)"
        self.start_btn.color = (150, 70, 60) if run.started else (70, 130, 70)
        self.start_btn.draw(surf, mouse)

        if relic_hover:
            rel = data.RELICS[relic_hover]
            lv = run.relic_level(relic_hover)
            lines = [
                (rel["name"] + (" +%d" % lv if lv else ""), data.RARITY_COLORS[rel["rarity"]]),
                (rel["desc"], TEXT),
            ]
            if relic_hover == "chosen_bloom":
                lines.append(("CLICK TO CHOOSE A PLANT" if run.chosen_plant is None else "CHOICE USED THIS ROUND", ACCENT))
            if relic_hover == "compost":
                if compost_now:
                    lines.append(("ACTIVE NOW: X2 VALUE! (%.1FS)" % run.time_left, GOOD))
                else:
                    lines.append(("ACTIVATES IN FINAL %dS" % int(run.compost_window()), ACCENT))
            for step in rel.get("levels", [])[:lv]:
                lines.append((step["desc"], GOOD))
            for step in rel.get("levels", [])[lv:]:
                lines.append(("EVOLVES AT %d %sS" % (step["goal"], step["stat"].upper()), DIM))
            gfx.tooltip(surf, lines, mouse, 102)
        elif self.shovel_btn.hover(mouse):
            gfx.tooltip(surf, [
                ("SHOVEL ACTIVE (X)" if self.shovel_mode else "SHOVEL (X)", BAD if self.shovel_mode else ACCENT),
                ("CLICK A PLANTED CROP TO DIG IT UP.", TEXT),
            ], mouse, 108)
        elif hover is not None and plots[hover].species:
            self.plot_tooltip(surf, hover)
        elif seed_hover is not None:
            sp = data.PLANTS[seed_hover]
            pays = sp.get("pays", True) is not False
            lines = [
                (sp["name"], data.RARITY_COLORS[sp["rarity"]]),
                ("GROW: %gS   HARVEST: %s" % (
                    sp["grow"], "$" + fmt(sp["yield"]) if pays else "$0"), TEXT),
                ("SELL AT END: $%s" % fmt(sp["sell"]), ACCENT),
                ("SELLS IN PACKS FOR $%s" % fmt(run.seed_price(seed_hover)), DIM),
            ]
            if not pays:
                lines.append(("PAYS NOTHING ITSELF", ACCENT))
            if sp.get("note"):
                lines.append((sp["note"], GOOD))
            gfx.tooltip(surf, lines, mouse, 104)
        elif gfx.inside(mouse, (4, 16, 312, 11)):
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
            if not self.shovel_mode and self.selected and gfx.inside(self.mouse, (x, y, w, h)):
                gfx.draw_sprite(surf, "seed", x + 22, y + 10, 1)
                gfx.draw_text(surf, "PLANT", x + w // 2, y + 24, TEXT, align="center")
            return
        sp = data.PLANTS[p.species]
        if run.is_chosen(i, cellar):
            gfx.rect(surf, ACCENT, x, y, w, 2)
        frac = min(1.0, p.progress / sp["grow"])
        # Some mutants (Five-Leaf Clover) have entirely different mature art.
        if frac >= 0.75 and sp.get("art"):
            sprite_name, subs = sp["art"], sp.get("subs")
        else:
            sprite_name, subs = gfx.plant_sprite_name(sp.get("base", p.species), frac), sp.get("subs")

        twist_id = "none" if (cellar or getattr(run, "weather_cleared", False)) else run.twist_id()
        wind = 1.4 if twist_id == "gale" else (0.25 if not cellar else 0.0)
        hovered = gfx.inside(self.mouse, (x, y, w, h))
        ripe = p.progress >= sp["grow"]
        disabled = run.plant_disabled(i, cellar)
        style = gfx.plant_anim_style(p.species, sp, sprite_name)
        glow = sp.get("base", p.species) == "mycelium" and not disabled
        anim = gfx.plant_anim(
            self.t, index=i, style=style, started=run.started and not disabled, ripe=ripe,
            speed=run.plot_growth_speed(i, cellar), hovered=hovered, wind=wind, glow=glow,
        )
        gfx.draw_sprite(surf, sprite_name, x + 16, y + 1, 2, subs, anim=anim)
        gfx.bar(surf, x + 4, y + 28, w - 8, 3, frac, sp["color"])
        if sp.get("spread") and run.creep_grown.get(cellar, 0) < run.creep_cap(plots, i):
            if run._can_creep(plots, i, cellar) or p.creep_cd > 0:
                # Creep meter: the amber bar under a mycelium filling toward its
                # next guaranteed spread, so growth is something you can watch.
                creep_frac = min(1.0, p.creep_cd / MYCELIUM_CREEP_TIME)
                creep_col = (255, 230, 120) if creep_frac >= 1.0 else (176, 138, 62)
                gfx.bar(surf, x + 4, y + 25, w - 8, 2, creep_frac, creep_col, back=(40, 34, 28))
        if disabled:
            gfx.rect(surf, (64, 52, 78), x + 1, y + h - 5, w - 2, 4)
            gfx.draw_text(surf, "DORMANT", x + 2, y + 2, (186, 134, 244))
        elif p.progress >= sp["grow"]:
            gfx.draw_text(surf, "READY", x + 2, y + 2, GOOD)
        if self.shovel_mode and gfx.inside(self.mouse, (x, y, w, h)):
            gfx.rect(surf, (120, 36, 36), x + 8, y + 11, w - 16, 11)
            gfx.draw_text(surf, "REMOVE", x + w // 2, y + 14, TEXT, align="center")
        elif p.water_left > 0:
            gfx.draw_sprite(surf, "drop", x + w - 9, y + 3)
        elif not cellar and run.can_water(i):
            gfx.draw_sprite(surf, "drop", x + w - 9, y + 3, 1, {"c": (96, 112, 140), "w": (130, 142, 170)})

    def plot_tooltip(self, surf, i):
        run = self.run
        cellar = self.in_cellar()
        p = self.plant_list()[i]
        sp = data.PLANTS[p.species]
        count = run.mastery.get(p.species, 0)
        nxt = next((t for t in data.MILESTONES if count < t), None)
        speed = run.plot_growth_speed(i, cellar)
        mutant_col = data.RARITY_COLORS["mutant"]
        color = mutant_col if sp.get("mutant") else data.RARITY_COLORS[sp["rarity"]]

        lines = [(sp["name"], color)]
        if run.plant_disabled(i, cellar):
            lines.append(("QUEEN BEE: DORMANT (NO HONEY)", (186, 134, 244)))
        elif p.progress >= sp["grow"]:
            lines.append(("READY: CLICK TO HARVEST", GOOD))
        if sp.get("mature_bonus"):
            lines.append(("MATURE %dS: +$%d BASE" % (int(p.mature_time), int(p.mature_time) * sp["mature_bonus"]), WATER))
        if run.is_chosen(i, cellar):
            lines.append(("CHOSEN: 1.5X GROWTH, 2X HARVEST", ACCENT))
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
        if cellar:
            lines.append(("CELLAR: SELF-WATERING", WATER))
        if run.compost_active():
            lines.append(("COMPOST HEAP: X2 ACTIVE!", GOOD))
        if sp.get("network"):
            size = len(run.mycelium_network(i, cellar))
            lines.append((
                "PATCH: %d MYCELIUM (+%d%%)" % (size, round(100 * (run.network_share(size) - 1))), GOOD,
            ))
        if sp.get("spread"):
            board = run.cellar_plots if cellar else run.plots
            grown = run.creep_grown.get(cellar, 0)
            cap = run.creep_cap(board, i)
            room = [n for n in run.neighbours(i, cellar) if board[n].species is None]
            lines.append(("HARVESTS CAN SPREAD IT", GOOD))
            if grown >= cap:
                lines.append(("PATCH HAS SPREAD ITS LIMIT (%d)" % cap, DIM))
            elif not room:
                lines.append(("NO EMPTY PLOT BESIDE IT (NEEDS 1 OR 2)", DIM))
            else:
                lines.append((
                    "CREEP: %d%% TO THE NEXT PLOT (%d/%d GROWN)" % (
                        round(100 * min(1.0, p.creep_cd / MYCELIUM_CREEP_TIME)), grown, cap),
                    GOOD,
                ))
        if sp.get("feed"):
            lines.append(("FED: +$%s NEXT HARVEST" % fmt(p.fed), TEXT))
        if sp.get("consume"):
            lines.append(("EATS A NEIGHBOUR EACH HARVEST", BAD))
            if p.gorged:
                lines.append(("EATEN BASE: +$%s" % fmt(int(round(p.gorged))), GOOD))
        if sp.get("bloom_chance"):
            lines.append(("LUCKY: %d%% X%g NEIGHBOUR" % (round(100 * sp["bloom_chance"]), sp.get("bloom_mult", 1.5)), GOOD))
        if p.bloom > 1.0:
            lines.append(("CLOVER BOOST: x%g BASE" % p.bloom, GOOD))
        if sp.get("pays", True) is False:
            lines.append(("HARVEST: $0 (PAYS NOTHING)", DIM))
        else:
            lines.append(("HARVEST: $" + fmt(run.harvest_value(i, cellar)), ACCENT))
        lines += [
            ("RIPE IN: %.1fs" % max(0.0, (sp["grow"] - p.progress) / max(speed, 0.01)), TEXT),
            ("HARVESTED: %d" % count, DIM),
        ]
        if nxt:
            lines.append(("DOUBLES AT %d" % nxt, DIM))
        elif not sp.get("mutant") and data.mutants_for(p.species):
            lines.append(("MAY MUTATE AT %d+ HARVESTS" % data.mutation_threshold(p.species), mutant_col))
        gfx.tooltip(surf, lines, self.mouse, 88)