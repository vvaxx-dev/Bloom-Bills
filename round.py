"""Live growing round screen: planting, watering, shoveling, cellar toggle, and relic sidebar."""

import math
import pygame

from . import ambient, data, gfx
from .formatting import clock, fmt
from .gfx import Button
from .scene import Scene, draw_topbar
from .settings import (
    ACCENT, APHID, BAD, BG, CANVAS_H, CANVAS_W, CELLAR_PRICE, COLS, DIM, GOOD,
    MAX_PLOTS, MYCELIUM_CREEP_TIME, PANEL_DARK, PANEL_LIGHT, SICK, SICK_SOIL, SOIL,
    SOIL_DARK, STARDUST, STARDUST_SOIL, TEXT, WATER, WEED, WEED_FEE,
)

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
        self.tray_scroll = min(self.tray_scroll, self.max_scroll())
        self.tray_left.enabled = self.tray_scroll > 0
        self.tray_right.enabled = self.tray_scroll < self.max_scroll()

    def in_cellar(self):
        return self.view == "cellar"

    def plant_list(self):
        return self.run.cellar_plots if self.in_cellar() else self.run.plots

    def relic_display(self):
        """Owned relics in rarity order, as shown in the round sidebar."""
        return data.sort_by_rarity(list(self.run.relics), data.RELICS)

    def view_seeds(self):
        """Return plantable species for the active board, but only ones the player
        actually owns; Eclipse adds owned nocturnal seeds to the surface tray.
        The tray is always in rarity order."""
        run = self.run
        if self.in_cellar():
            return data.sort_by_rarity([sid for sid in data.CELLAR_PLANTS if run.seeds.get(sid, 0) > 0])
        seeds = [sid for sid in data.SURFACE_PLANTS if run.seeds.get(sid, 0) > 0]
        if run.twist().get("eclipse"):
            seeds += [sid for sid in data.NOCTURNAL_PLANTS
                      if sid not in seeds and run.seeds.get(sid, 0) > 0]
        return data.sort_by_rarity(seeds)

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
            idx = self.relic_display().index("chosen_bloom")
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
                if not in_cellar and plots[i].weed:
                    # Digging out a weed is never a loss, so it goes through
                    # without the destructive-action confirmation the crop
                    # shovel asks for.
                    run.clear_weeds(i)
                    self.app.toast("PULLED THE WEEDS - CLEAN SOIL")
                else:
                    self.app.toast("NOTHING PLANTED HERE")
                return
            plant_name = data.PLANTS[plots[i].species]["name"].upper()
            sick = plots[i].sick

            def do_remove():
                ok, _ = run.remove_plant(i, in_cellar)
                if ok:
                    self.app.toast(
                        "%s DUG OUT. THE PLOT IS CLEAN AGAIN." % plant_name
                        if sick else "REMOVED %s" % plant_name,
                        2.4,
                    )
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
            if not in_cellar and plots[i].weed:
                self.app.toast("WEEDS HAVE THAT PLOT - SHOVEL IT (X)")
                return
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
        board_rects = [plot_rect(i) for i in range(len(self.plant_list()))]
        self._ambient().update(dt * self.fast, run, self.in_cellar(),
                               plot_rects=board_rects, mouse=self.mouse)
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
            if kind == "capsule":
                self.app.toast("TIME CAPSULE! +$%d FROM LAST 10S." % ev["amount"], 2.0)
                continue
            if kind == "crossbreed":
                if hasattr(self.app, "discover_crossbreed"):
                    self.app.discover_crossbreed(ev["species"])
                self.app.toast(
                    "%s %s SEED +1!" % (
                        "CROSSBREED DISCOVERED!" if ev.get("first") else "CROSSBREED!",
                        ev["name"].upper(),
                    ), 3.0,
                )
                if show_floaters and bool(ev.get("cellar")) == self.in_cellar() \
                        and ev["plot"] < MAX_PLOTS:
                    x, y, w, _h = plot_rect(ev["plot"])
                    self.floaters.append(
                        [x + w // 2, y + 8, "NEW SEED!", data.RARITY_COLORS["exquisite"], 0.0])
                continue
            if kind == "owl_seed":
                self.app.toast("THE OWL DROPPED %d %s SEED%s!"
                               % (ev["count"], ev["name"].upper(), "" if ev["count"] == 1 else "S"), 2.0)
                continue
            if kind == "owl_scare":
                if self.in_cellar():
                    continue
                self.app.toast("THE OWL SCARED THE CROWS AWAY!", 2.0)
                continue
            if kind == "snail_bite":
                self.app.toast("THE ETERNAL SNAIL CAUGHT YOUR CURSOR!", 3.0)
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
            elif kind == "sick":
                # Diseased: named, and the source plot is flagged so the spread
                # reads as a chain rather than as random bad luck.
                if show_floaters:
                    self.floaters.append([fx, fy, "DISEASED!", SICK, 0.0])
                    source = ev.get("source")
                    if source is not None and 0 <= source < MAX_PLOTS:
                        sx, sy, sw, _sh = plot_rect(source)
                        self.floaters.append([sx + sw // 2, sy + 8, "SPREAD!", SICK, 0.0])
                self.app.toast(
                    "%s CAUGHT DISEASE! DIG IT OUT OR IT SPREADS." % ev["name"].upper(), 2.4)
            elif kind == "cured":
                if show_floaters:
                    self.floaters.append([fx, fy, "SOIL CLEAN", GOOD, 0.0])
            elif kind == "meteor":
                if ev.get("destroyed"):
                    if show_floaters:
                        self.floaters.append([fx, fy, "METEOR!", BAD, 0.0])
                    self.app.toast("A METEOR TOOK YOUR %s!" % ev.get("name", "CROP").upper(), 2.2)
                elif ev.get("stardust"):
                    if show_floaters:
                        self.floaters.append([fx, fy, "STARDUST!", ACCENT, 0.0])
                    self.app.toast("STARDUST IN THAT PLOT - PLANT SOMETHING GOOD.", 2.4)
                elif ev.get("weedy"):
                    if show_floaters:
                        self.floaters.append([fx, fy, "BURNT WEEDS", GOOD, 0.0])
                else:
                    if show_floaters:
                        self.floaters.append([fx, fy, "STARLIT x1.5!", ACCENT, 0.0])
                    self.app.toast(
                        "A METEOR MADE %s STARLIT! X1.5 VALUE." % ev.get("name", "A CROP").upper(), 2.6)
            elif kind == "weed":
                if show_floaters:
                    self.floaters.append([fx, fy, "WEEDS!", WEED, 0.0])
                    source = ev.get("source")
                    if source is not None and 0 <= source < MAX_PLOTS:
                        sx, sy, sw, _sh = plot_rect(source)
                        self.floaters.append([sx + sw // 2, sy + 8, "SEEDED", WEED, 0.0])
                self.app.toast("WEEDS TOOK AN EMPTY PLOT. DIG THEM OUT.", 2.0)
            elif kind == "weed_clear":
                if show_floaters:
                    self.floaters.append([fx, fy, "CLEARED", GOOD, 0.0])
            elif kind == "aphid":
                if show_floaters:
                    self.floaters.append([fx, fy, "APHIDS!", BAD, 0.0])
                self.app.toast("APHIDS ON YOUR %s - WATER IT OFF!" % ev["name"].upper(), 2.4)
            elif kind == "aphid_wash":
                if show_floaters:
                    self.floaters.append([fx, fy, "WASHED OFF", WATER, 0.0])
            elif kind == "stardust":
                if show_floaters:
                    self.floaters.append([fx, fy, "STARLIT CROP!", ACCENT, 0.0])
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
            elif kind == "critter_eaten":
                if show_floaters:
                    self.floaters.append([fx, fy, "CHOMP!", GOOD, 0.0])
                self.app.toast(
                    "FLYTRAP ATE A %s! +$%d BASE" % (ev.get("name", "CRITTER").upper(), ev.get("amount", 0)),
                    2.0,
                )
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
            # The full Eclipse sentence is much wider than the 320px HUD row;
            # the short line keeps the meaning without painting off screen.
            msg = "%s: %s" % (twist["name"].upper(), twist.get("short", twist["desc"]).upper())
            col = TONE_COLORS[twist.get("tone", "neutral")]
        elif self.in_cellar():
            msg, col = "THE CELLAR: SELF-WATERING, WEATHERPROOF.", WATER
        elif not run.started:
            msg, col = "WEATHER: FAIR WEATHER - PLANT SEEDS, THEN PRESS START.", DIM
        elif self.hazard_note():
            # A hazard has left marks on the garden, which beats reminding the
            # player how to click: the row of sick plots is the problem now.
            msg, col = self.hazard_note(), SICK
        else:
            msg, col = "CLICK TO WATER; CLICK MATURE PLANTS TO HARVEST.", DIM
        gfx.draw_text(surf, gfx.fit_text(msg, CANVAS_W - 10), 5, 18, col)

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
        amb.draw_foreground(surf, run, cellar=self.in_cellar(), mouse=self.mouse)

        if hover is not None:
            x, y, w, h = plot_rect(hover)
            diggable = plots[hover].species or (not self.in_cellar() and plots[hover].weed)
            hcol = BAD if (self.shovel_mode and diggable) else ACCENT
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
            gfx.draw_text(surf, gfx.fit_text(data.RELICS[rid]["name"] + plus + active_tag, 68),
                          248, ry, rcol)
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
        if not visible:
            gfx.draw_text(surf, "NO SEEDS - OPEN PACKS", 10, TRAY_Y + 11, DIM)
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
            syn = data.synergy_text(relic_hover)
            if syn:
                lines.append(("PAIRING: " + syn, GOOD))
            if rel.get("lore"):
                lines.append((rel["lore"], DIM))
            if relic_hover in run.active_synergy_ids():
                lines.append(("PAIRING ACTIVE!", GOOD))
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
            lines = [
                ("SHOVEL ACTIVE (X)" if self.shovel_mode else "SHOVEL (X)", BAD if self.shovel_mode else ACCENT),
                ("CLICK A PLANTED CROP TO DIG IT UP.", TEXT),
            ]
            # The shovel is the answer to both soil hazards, and players keep
            # forgetting it: say so only when there is something to answer.
            if run.weedy_count():
                lines.append(("OR A WEED - THE PLOT COMES BACK PLANTABLE", WEED))
            if run.diseased_count():
                lines.append(("DIGGING OUT A SICK CROP LEAVES IT CLEAN", GOOD))
            if self.shovel_mode:
                lines.append(("NO SEED COMES BACK.", DIM))
            gfx.tooltip(surf, lines, mouse, 108)
        elif hover is not None and plots[hover].species:
            self.plot_tooltip(surf, hover)
        elif hover is not None and not self.in_cellar() and (plots[hover].weed or plots[hover].starlit):
            self.empty_plot_tooltip(surf, plots[hover])
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
            lore = data.plant_lore(seed_hover)
            if lore:
                lines.append((lore, DIM))
            gfx.tooltip(surf, lines, mouse, 104)
        elif gfx.inside(mouse, (4, 16, 312, 11)):
            tcol = BAD if twist.get("boss") else TONE_COLORS.get(twist.get("tone", "neutral"), TEXT)
            lines = [
                ("WEATHER: " + twist["name"].upper(), tcol),
                (twist["desc"], TEXT),
            ]
            lore = data.twist_lore(run.twist_id())
            if lore and not run.weather_cleared:
                lines.append((lore, DIM))
            if self.hazard_note():
                lines.append((self.hazard_note(), ACCENT))
            gfx.tooltip(surf, lines, mouse, 112)

    def draw_plot(self, plots, surf, i, x, y, w, h):
        run = self.run
        p = plots[i]
        cellar = self.in_cellar()
        top, bottom = (SOIL_DARK, (66, 48, 38)) if cellar else (SOIL_DARK, SOIL)
        # Hazard states recolour the soil itself, so the garden can be read at
        # a glance before any tooltip is opened: mouldy for Disease, warm and
        # golden where a meteor left stardust.
        if not cellar and (p.sick or p.starlit):
            bottom = SICK_SOIL if p.sick else STARDUST_SOIL
        gfx.rect(surf, top, x, y, w, h)
        gfx.rect(surf, bottom, x + 1, y + 1, w - 2, h - 2)
        for k in range(6):
            gfx.rect(surf, SOIL_DARK, x + 3 + (i * 7 + k * 11) % 50, y + 3 + (i * 5 + k * 13) % 28, 2, 1)
        if p.species is None:
            if not cellar and p.weed:
                # Weeds are drawn with the same animation as a real crop,
                # because the trap is exactly that: it looks like progress.
                gfx.draw_sprite(
                    surf, "weed", x + 16, y + 1, 2,
                    anim=gfx.plant_anim(self.t, index=i, style="reed", started=True,
                                        hovered=gfx.inside(self.mouse, (x, y, w, h)), wind=0.5),
                )
                gfx.draw_text(surf, "WEEDS", x + 2, y + 2, WEED)
                if self.shovel_mode:
                    gfx.rect(surf, (52, 92, 46), x + 8, y + 11, w - 16, 11)
                    gfx.draw_text(surf, "CLEAR", x + w // 2, y + 14, TEXT, align="center")
                elif self.selected:
                    gfx.draw_text(surf, "NEEDS THE SHOVEL", x + w // 2, y + 26, DIM, align="center")
                return
            if not cellar and p.starlit:
                # The dust itself twinkles in STARDUST rather than the harvest
                # gold, so a gifted plot and a ripe one cannot be confused.
                for k, (ox, oy) in enumerate(((38, 6), (12, 20), (30, 24))):
                    if int(self.t * 3 + i + k) % 3:
                        gfx.rect(surf, STARDUST, x + ox, y + oy, 1, 1)
                gfx.draw_sprite(surf, "star", x + w - 20, y + 8, 1)
                gfx.draw_text(surf, "STARDUST", x + 2, y + 2, STARDUST)
                if self.selected and gfx.inside(self.mouse, (x, y, w, h)):
                    gfx.draw_text(surf, "PLANT (x1.5)", x + w // 2, y + 26, ACCENT, align="center")
                return
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
        if p.sick:
            # Mouldy dabs on the foliage itself: three spots that drift a pixel
            # so a sick plot never looks quite still under the cursor.
            for k, (ox, oy) in enumerate(((24, 9), (34, 15), (20, 19))):
                gfx.rect(surf, SICK, x + ox + (int(self.t * 2) + k) % 2, y + oy, 3, 2)
        if p.aphids:
            for k in range(4):
                gfx.rect(surf, APHID, x + 14 + k * 5 + (int(self.t * 4) + k) % 2,
                         y + 16 + (k % 2) * 3, 2, 2)
        if p.starlit and int(self.t * 2 + i) % 3:
            gfx.draw_sprite(surf, "star", x + w - 20, y + 3, 1)
            gfx.rect(surf, STARDUST, x + 6, y + 30, w - 12, 1)
        gfx.bar(surf, x + 4, y + 28, w - 8, 3, frac, SICK if p.sick else sp["color"])
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
        elif p.sick:
            gfx.draw_text(surf, "SICK", x + 2, y + 2, SICK)
        elif p.aphids:
            gfx.draw_text(surf, "APHIDS", x + 2, y + 2, BAD)
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
        # Hazard lines come next: they are the reason a plot is worth less than
        # the number the seed promised, so they read before the maths does.
        if p.sick:
            grow_m, yield_m, sale_m = run.disease_factors()
            lines.append(("DISEASED: %d%% GROWTH, %d%% VALUE"
                          % (round(100 * grow_m), round(100 * yield_m)), SICK))
            lines.append(("SELLS AT %d%% AT THE BUZZER" % round(100 * sale_m), SICK))
            lines.append(("SPREADS TO A NEIGHBOUR EVERY %ds"
                          % int(run.twist().get("contagion", 0) or 0), BAD))
            lines.append(("SHOVEL IT - THE PLOT COMES BACK CLEAN", GOOD))
        if p.aphids:
            lines.append(("APHIDS: HARVEST HALVED", BAD))
            lines.append(("WATER THE PLOT TO WASH THEM OFF", WATER))
        if p.starlit:
            lines.append(("STARLIT: X1.5 HARVEST AND SALE", ACCENT))
            lines.append(("A METEOR REWROTE THIS CROP", DIM))
        if sp.get("mature_bonus"):
            lines.append(("MATURE %dS: +$%d BASE" % (int(p.mature_time), int(p.mature_time) * sp["mature_bonus"]), WATER))
        if sp.get("crossbreed"):
            lines.append(("CROSSBREED - NO PACK SELLS IT", ACCENT))
        if sp.get("twist_growth", {}).get("sunny"):
            lines.append(("GROWS 25% FASTER IN SUNSHINE", GOOD))
        if sp.get("hardy_twists"):
            lines.append(("THRIVES IN DROUGHT AND HEATWAVES", GOOD))
        if sp.get("season_growth"):
            lines.append(("GROWS 25% FASTER IN AUTUMN", GOOD))
        if sp.get("frost_hardy"):
            lines.append(("WINTER-HARDY IN FROST", WATER))
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
        if self.shovel_mode:
            lines.append(("DIG IT UP (NO SEED BACK)", BAD))
        gfx.tooltip(surf, lines, self.mouse, 88)

    def empty_plot_tooltip(self, surf, plot):
        """Tooltip for bare soil that something has already claimed."""
        lines = []
        if plot.weed:
            lines += [
                ("WEEDS", WEED),
                ("NOBODY CAN PLANT HERE", BAD),
                ("DIG IT OUT WITH THE SHOVEL (X)", TEXT),
                ("COSTS $%d IF LEFT TO THE BUZZER" % WEED_FEE, DIM),
                ("A METEOR WOULD BURN IT, TOO", DIM),
            ]
        if plot.starlit:
            lines += [
                ("STARDUST SOIL", ACCENT),
                ("YOUR NEXT CROP HERE IS STARLIT: X1.5", GOOD),
                ("THE DUST SURVIVES PLANTING, NOT SHOVELLING", DIM),
            ]
        gfx.tooltip(surf, lines, self.mouse, 100)

    def hazard_note(self):
        """What the active hazard has actually done this round, for the forecast."""
        run = self.run
        bits = []
        sick = run.diseased_count()
        if sick:
            bits.append("%d PLOT%s SICK - SHOVEL THEM" % (sick, "" if sick == 1 else "S"))
        weeds = run.weedy_count()
        if weeds:
            bits.append("%d WEED%s TO DIG" % (weeds, "" if weeds == 1 else "S"))
        aphids = sum(1 for p in run.plots if p.species and p.aphids)
        if aphids:
            bits.append("%d WITH APHIDS - WATER THEM" % aphids)
        starlit = sum(1 for p in run.plots if p.starlit)
        if starlit:
            bits.append("%d STARLIT PLOT%s" % (starlit, "" if starlit == 1 else "S"))
        return ". ".join(bits)