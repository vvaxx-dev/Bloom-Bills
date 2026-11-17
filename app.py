"""Top-level Pygame application: window scaling, scene transitions, modal stack, and run lifecycle."""

import os
import sys
from pathlib import Path

import pygame

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from main import bootstrap_package
    __package__ = bootstrap_package()

from . import gfx
from .overlays import ConfirmModal, PauseModal, SettingsModal
from .save import SaveManager
from .scene import TOPBAR_PAUSE_RECT, draw_topbar_tooltip
from .scenes import SCENES
from .settings import (
    BLACK, BORDERLESS, CANVAS_H, CANVAS_W, FPS, PANEL_DARK, START_SCALE, TEXT, TITLE,
)
from .state import Run
from .tutorial import (PREMISE_KEY, DialogueOverlay, TUTORIAL_STAGES, beat_for,
                     mark_beat_seen, tutorial_steps)

RUN_SCENE_NAMES = ("packs", "round", "summary", "shop", "victory")


class App:
    """Owns the 320x180 pixel canvas, integer-scaled presentation window, save manager, and active scene."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.saves = SaveManager()
        self.profile = self.saves.load_profile()
        self.settings_cfg = self.profile.setdefault("settings", {})
        scale = int(self.settings_cfg.get("scale", START_SCALE))
        self.fullscreen = False
        self.borderless = BORDERLESS
        self.windowed_size = (CANVAS_W * scale, CANVAS_H * scale)
        pygame.display.set_mode(self._window_size(), self._window_flags())
        pygame.mouse.set_visible(False)
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.clock = pygame.time.Clock()

        self.run = None
        self.scene = None
        self.scene_name = ""
        self.pause_modal = None
        self.settings_modal = None
        self.confirm_modal = None
        self.dialogue_modal = None
        self.mouse = (0, 0)
        self.running = True
        self.toasts = []
        self.last_result = None
        self.debug = os.environ.get("BLOOM_DEBUG") == "1"
        self.goto("title")

    def open_index(self):
        """Open the Garden Index without losing the live in-run scene."""
        if self.scene_name == "index":
            return
        if self.run and self.scene_name in RUN_SCENE_NAMES:
            self._index_return_scene = self.scene
            self._index_return_name = self.scene_name
            self._index_return_pause = True
        self.goto("index")

    def return_from_index(self):
        """Leave the Garden Index, restoring any scene parked by open_index."""
        scene, name = self._index_return_scene, self._index_return_name
        want_pause = self._index_return_pause
        self._index_return_scene = None
        self._index_return_name = ""
        self._index_return_pause = False
        if scene is None:
            self.goto("title")
            return
        self.pause_modal = None
        self.settings_modal = None
        self.confirm_modal = None
        self.dialogue_modal = None
        self.scene = scene
        self.scene_name = name
        if want_pause and self.run and name in RUN_SCENE_NAMES:
            self.open_pause()

    def discover_crossbreed(self, cid):
        """Persist a crossbreed discovery into profile.json immediately."""
        from . import data as _data

        if cid not in _data.CROSSBREEDS:
            return
        found = list(self.profile.get("discovered_crossbreeds", []))
        if cid not in found:
            found.append(cid)
            self.profile["discovered_crossbreeds"] = sorted(found)
            self.saves.save_profile(self.profile)
        if self.run is not None:
            self.run.discovered_crossbreeds.add(cid)

    def goto(self, name, **kwargs):
        if name != "index":
            self._index_return_scene = None
            self._index_return_name = ""
            self._index_return_pause = False
        self.scene_name = name
        self.pause_modal = None
        self.settings_modal = None
        self.confirm_modal = None
        self.dialogue_modal = None
        self.scene = SCENES[name](self, **kwargs)
        self.scene.on_enter()

    def toast(self, text, seconds=2.0):
        self.toasts = [[text, seconds]]

    def quit(self):
        self.running = False

    def save_settings(self):
        self.profile["settings"] = dict(self.settings_cfg)
        self.saves.save_profile(self.profile)

    def set_window_scale(self, scale):
        scale = max(2, min(8, int(scale)))
        self.settings_cfg["scale"] = scale
        self.windowed_size = (CANVAS_W * scale, CANVAS_H * scale)
        if not self.fullscreen and not self.borderless:
            self.rebuild_window()
        self.save_settings()

    def ask_confirm(self, title, message, on_confirm, confirm_label="CONFIRM", danger=True):
        if not self.settings_cfg.get("confirmations", True):
            if on_confirm:
                on_confirm()
            return
        self.confirm_modal = ConfirmModal(
            self, title, message, on_confirm, confirm_label=confirm_label, danger=danger,
        )

    def open_settings(self):
        self.settings_modal = SettingsModal(self)

    def open_pause(self):
        if self.run and self.scene_name in RUN_SCENE_NAMES:
            self.pause_modal = PauseModal(self)

    def active_modal(self):
        """Return the highest-priority open modal (confirm > settings > dialogue > pause)."""
        return self.confirm_modal or self.settings_modal or self.dialogue_modal or self.pause_modal

    def _tutorial_done(self):
        return self.profile.setdefault("tutorial_done", [])

    def _complete_tutorial(self, stage, skipped=False):
        done = self._tutorial_done()
        stages = TUTORIAL_STAGES if skipped else (stage,)
        for name in stages:
            if name not in done:
                done.append(name)
        if stage == "packs":
            # The premise rides on the front of the packs walkthrough, so this is
            # the moment it counts as read: later runs get the two-line version.
            # `start_story` is deliberately not called here - the packs screen that
            # follows is already full of words, and its own enter hook will pick the
            # next beat up.
            mark_beat_seen(self.profile, PREMISE_KEY)
        self.saves.save_profile(self.profile)

    def start_story(self):
        """Play the story beat due for this round on the packs screen, once.

        Beats are gated three ways: the run remembers the arc (so a reload does
        not repeat it and a new run does hear it), the profile remembers hazard
        warnings (so Moss explains a rot once ever), and nothing plays while a
        tutorial or modal owns the screen. Skipping a beat marks it seen too, on
        the theory that a player who hits Esc once means it.
        """
        if not self.run or self.scene_name != "packs" or self.active_modal():
            return
        beat = beat_for(self.run, self.profile)
        if not beat:
            return
        beat_id, steps, persistent = beat
        if not steps:
            return

        def end():
            if self.run:
                self.run.mark_story_beat(beat_id)
                self.save_run()
            if persistent:
                mark_beat_seen(self.profile, beat_id)
                self.saves.save_profile(self.profile)

        self.dialogue_modal = DialogueOverlay(self, steps, on_finish=end, on_skip=end)

    def start_tutorial(self, stage):
        """Open a first-run tutorial stage once, unless it was finished or skipped."""
        if not self.run or stage in self._tutorial_done() or self.active_modal():
            return
        steps = tutorial_steps(stage, self.scene)
        if not steps:
            return
        self.dialogue_modal = DialogueOverlay(
            self, steps,
            on_finish=lambda: self._complete_tutorial(stage),
            on_skip=lambda: self._complete_tutorial(stage, skipped=True),
        )

    def open_guide(self):
        """Replayable overview dialogue, usable from the title screen without a run."""
        from .tutorial import guide_steps
        self.dialogue_modal = DialogueOverlay(self, guide_steps())

    def _window_flags(self):
        return pygame.NOFRAME if self.borderless else pygame.RESIZABLE

    def _desktop_size(self):
        try:
            info = pygame.display.Info()
            width, height = int(info.current_w), int(info.current_h)
        except (pygame.error, ValueError):
            width = height = 0
        if width < CANVAS_W or height < CANVAS_H:
            return None
        return (width, height)

    def _window_size(self):
        if not self.borderless or self.fullscreen:
            return self.windowed_size
        return self._desktop_size() or self.windowed_size

    def rebuild_window(self):
        pygame.display.set_mode(self._window_size(), self._window_flags())
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(False)

    def toggle_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.rebuild_window()
        else:
            fs_size = self._desktop_size() or (1920, 1080)
            pygame.display.set_mode(fs_size, pygame.FULLSCREEN)
            pygame.display.set_caption(TITLE)
            pygame.mouse.set_visible(False)
            self.fullscreen = True
        mode = "FULLSCREEN" if self.fullscreen else ("BORDERLESS" if self.borderless else "WINDOWED")
        self.toast(mode)

    def toggle_borderless(self):
        self.borderless = not self.borderless
        if not self.fullscreen:
            self.rebuild_window()
        self.toast("BORDERLESS" if self.borderless else "WINDOWED")

    def new_run(self):
        self.run = Run(perks=self.profile["perks"])
        self.run.grant_round_packs()
        self.save_run()
        self.goto("packs")
        self.start_tutorial("packs")

    def continue_run(self):
        saved = self.saves.load_run()
        if not saved:
            return self.new_run()
        self.run = Run.from_dict(saved)
        # Apply any permanent perks bought on the Heirloom Shelf while the run was parked.
        changed = False
        for key, target_lv in self.profile.get("perks", {}).items():
            while self.run.perk(key) < int(target_lv):
                self.run.perks[key] = self.run.perk(key) + 1
                self.run._apply_perk(key)
                changed = True
        if changed:
            self.save_run()
        if self.run.phase == "shop":
            self.goto("shop")
        elif self.run.phase == "summary" and self.run.won and not self.run.endless and not self.run.retired:
            # The win is pending its retire/endless choice; don't let a reload skip it.
            self.goto("victory")
        elif self.run.phase == "summary":
            self.goto("summary")
        else:
            self.goto("packs")
        if self.scene_name in TUTORIAL_STAGES:
            self.start_tutorial(self.scene_name)

    def save_run(self):
        if self.run and not self.run.dead:
            self.saves.save_run(self.run.to_dict())

    def after_round(self):
        self.run.end_round()
        self.save_run()
        if self.run.dead:
            self.finish_run()
            self.goto("gameover")
        else:
            self.goto("summary")

    def finish_run(self):
        """Credit earned heirlooms, merge lifetime stats into profile.json, and clear run.json."""
        run = self.run
        profile = self.profile
        gain = run.heirloom_reward()
        new_best = run.round > profile["best_round"]
        profile["heirlooms"] += gain
        merged_perks = dict(profile.get("perks", {}))
        for key, lv in run.perks.items():
            merged_perks[key] = max(int(merged_perks.get(key, 0)), int(lv))
        profile["perks"] = merged_perks
        profile["best_round"] = max(profile["best_round"], run.round)
        profile["runs"] += 1
        if run.won:
            profile["wins"] += 1
        harvested = dict(profile.get("harvested", {}))
        for sid, count in run.mastery.items():
            harvested[sid] = harvested.get(sid, 0) + int(count)
        profile["harvested"] = harvested
        from . import data as _data

        discovered = set(profile.get("discovered_crossbreeds", []))
        discovered.update(getattr(run, "discovered_crossbreeds", set()))
        # Anything already harvested (e.g. from an older save) is no mystery.
        discovered.update(sid for sid, n in harvested.items() if n and sid in _data.CROSSBREEDS)
        profile["discovered_crossbreeds"] = sorted(discovered)
        self.saves.save_profile(profile)
        self.saves.clear_run()
        s = run.last_summary or {}
        self.last_result = {
            "round": run.round, "quotas_paid": run.quotas_paid, "total_earned": run.total_earned,
            "heirlooms": gain, "spent": run.heirlooms_spent, "won": run.won,
            "bill": s.get("bill", 0), "money": s.get("money", run.money), "new_best": new_best,
            "cause": "snail" if getattr(run, "snail_bitten", False) else "",
        }
        self.run = None

    def _layout(self):
        """Compute integer letterboxed scale factor and top-left window offset."""
        w, h = pygame.display.get_surface().get_size()
        scale = max(1, min(w // CANVAS_W, h // CANVAS_H))
        return scale, (w - CANVAS_W * scale) // 2, (h - CANVAS_H * scale) // 2

    def to_canvas(self, pos):
        scale, ox, oy = self._layout()
        return ((pos[0] - ox) // scale, (pos[1] - oy) // scale)

    def present(self):
        window = pygame.display.get_surface()
        scale, ox, oy = self._layout()
        window.fill(BLACK)
        window.blit(pygame.transform.scale(self.canvas, (CANVAS_W * scale, CANVAS_H * scale)), (ox, oy))
        pygame.display.flip()

    def draw_toasts(self):
        if not self.toasts:
            return
        text = str(self.toasts[0][0])
        max_w = CANVAS_W - 16
        lines = gfx.wrap(text, max_w) or [""]
        if len(lines) > 2:
            lines = [lines[0], gfx.fit_text(" ".join(lines[1:]), max_w)]
        w = max(gfx.text_width(line) for line in lines) + 10
        h = 4 + 7 * len(lines)
        x = (CANVAS_W - w) // 2
        y = 15
        gfx.rect(self.canvas, PANEL_DARK, x - 1, y, w + 2, h + 1)
        gfx.rect(self.canvas, (80, 40, 40), x, y + 1, w, h - 1)
        for i, line in enumerate(lines):
            gfx.draw_text(self.canvas, line, CANVAS_W // 2, y + 2 + i * 7, TEXT, align="center")

    def handle_key(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_F12:
            self.toggle_borderless()
            return
        modal = self.active_modal()
        if modal:
            modal.on_key(key)
            return
        if key == pygame.K_ESCAPE and self.run and self.scene_name in RUN_SCENE_NAMES:
            if not (getattr(self.scene, "shovel_mode", False) or getattr(self.scene, "choose_mode", False)):
                self.open_pause()
                return
        if self.debug and self.run:
            if key == pygame.K_F2 and hasattr(self.scene, "fast"):
                self.scene.fast = 1 if self.scene.fast > 1 else 10
                self.toast("DEBUG: SPEED x%d" % self.scene.fast)
            elif key == pygame.K_F3:
                self.run.money += 10000
                self.toast("DEBUG: +$10000")
        self.scene.on_key(key)

    def handle_click(self, pos):
        modal = self.active_modal()
        if modal:
            modal.on_click(pos)
            return
        if self.run and self.scene_name in RUN_SCENE_NAMES and gfx.inside(pos, TOPBAR_PAUSE_RECT):
            self.open_pause()
            return
        self.scene.on_click(pos)

    def cursor_kind(self):
        if not self.active_modal() and bool(getattr(self.scene, "shovel_mode", False)):
            return "shovel"
        return "cursor"

    def tick(self, dt):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.quit()
            elif ev.type == pygame.MOUSEMOTION:
                self.mouse = self.to_canvas(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.mouse = self.to_canvas(ev.pos)
                self.handle_click(self.mouse)
            elif ev.type == pygame.MOUSEWHEEL:
                modal = self.active_modal()
                if not modal:
                    self.scene.on_wheel(ev.y)
                elif hasattr(modal, "on_wheel"):
                    modal.on_wheel(ev.y)
            elif ev.type == pygame.KEYDOWN:
                self.handle_key(ev.key)
        self.mouse = self.to_canvas(pygame.mouse.get_pos())

        modal = self.active_modal()
        if not modal:
            self.scene.update(dt)
        if self.dialogue_modal:
            self.dialogue_modal.update(dt)
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]

        # Hide hover highlights on underlying scene widgets while a modal is active.
        real_mouse = self.mouse
        if modal:
            self.mouse = (-999, -999)
        self.scene.draw(self.canvas)
        self.mouse = real_mouse

        if modal:
            if self.pause_modal and modal is not self.pause_modal:
                self.pause_modal.draw(self.canvas, (-999, -999))
            modal.draw(self.canvas, self.mouse)
        elif self.run and self.scene_name in RUN_SCENE_NAMES:
            draw_topbar_tooltip(self.canvas, self.mouse)

        self.draw_toasts()
        gfx.draw_cursor(self.canvas, self.mouse, self.cursor_kind())
        self.present()

    def main_loop(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
            self.tick(dt)
        pygame.quit()


if __name__ == "__main__":
    App().main_loop()
