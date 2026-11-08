import os
import pygame
from .save import SaveManager
from .scenes import SCENES
from .settings import (BLACK, BORDERLESS, CANVAS_H, CANVAS_W, FPS, START_SCALE, TITLE, TEXT, PANEL_DARK)
from .state import Run
from . import gfx


class App:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.fullscreen = False
        self.borderless = BORDERLESS
        self.windowed_size = (CANVAS_W * START_SCALE, CANVAS_H * START_SCALE)
        pygame.display.set_mode(self._window_size(), self._window_flags())
        pygame.mouse.set_visible(False) 
        self.canvas = pygame.Surface((CANVAS_W, CANVAS_H))
        self.clock = pygame.time.Clock()

        self.saves = SaveManager()
        self.profile = self.saves.load_profile()
        self.run = None
        self.scene = None
        self.mouse = (0, 0)
        self.running = True
        self.toasts = []                 # [text, seconds_left]
        self.last_result = None
        self.debug = os.environ.get("BLOOM_DEBUG") == "1"
        self.goto("title")

    def goto(self, name, **kwargs):
        self.scene = SCENES[name](self, **kwargs)
        self.scene.on_enter()

    def toast(self, text, seconds=2.0):
        self.toasts = [[text, seconds]]

    def quit(self):
        self.running = False

    def _window_flags(self):
        """No window chrome while borderless; plain resizable otherwise."""
        return pygame.NOFRAME if self.borderless else pygame.RESIZABLE

    def _window_size(self):
        """Borderless fills the screen without going exclusive-fullscreen."""
        if not self.borderless or self.fullscreen:
            return self.windowed_size
        try:
            info = pygame.display.Info()
            width, height = int(info.current_w), int(info.current_h)
        except (pygame.error, ValueError):
            width = height = 0
        if width < CANVAS_W or height < CANVAS_H:
            return self.windowed_size
        return (width, height)

    def rebuild_window(self):
        pygame.display.set_mode(self._window_size(), self._window_flags())
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(False)

    def toggle_fullscreen(self):
        if self.fullscreen:
            self.fullscreen = False
            self.rebuild_window()
        else:
            pygame.display.set_mode((1920, 1080), pygame.FULLSCREEN)
            self.fullscreen = True
        pygame.display.set_caption(TITLE)
        pygame.mouse.set_visible(False)
        self.toast("FULLSCREEN" if self.fullscreen else "WINDOWED")

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

    def continue_run(self):
        data = self.saves.load_run()
        if not data:
            return self.new_run()
        self.run = Run.from_dict(data)
        if self.run.phase == "shop":
            self.goto("shop")
        elif self.run.phase == "summary" and self.run.pending_bill:
            self.goto("summary")
        else:
            self.goto("packs")

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
        run = self.run
        profile = self.profile
        gain = run.heirloom_reward()
        new_best = run.round > profile["best_round"]
        profile["heirlooms"] += gain
        profile["perks"] = dict(run.perks) 
        profile["best_round"] = max(profile["best_round"], run.round)
        profile["runs"] += 1
        if run.won:
            profile["wins"] += 1
        self.saves.save_profile(profile)
        self.saves.clear_run()
        s = run.last_summary or {}
        self.last_result = {
            "round": run.round, "quotas_paid": run.quotas_paid, "total_earned": run.total_earned,
            "heirlooms": gain, "spent": run.heirlooms_spent, "won": run.won,
            "bill": s.get("bill", 0), "money": s.get("money", run.money), "new_best": new_best,
        }
        self.run = None


    def _layout(self):
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
        text = self.toasts[0][0]
        w = gfx.text_width(text) + 10
        x = (CANVAS_W - w) // 2
        gfx.rect(self.canvas, PANEL_DARK, x - 1, 15, w + 2, 13)
        gfx.rect(self.canvas, (80, 40, 40), x, 16, w, 11)
        gfx.draw_text(self.canvas, text, CANVAS_W // 2, 19, TEXT, align="center")

    def handle_key(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        if key == pygame.K_F12:
            self.toggle_borderless()
            return
        if self.debug and self.run:
            if key == pygame.K_F2 and hasattr(self.scene, "fast"):
                self.scene.fast = 1 if self.scene.fast > 1 else 10
                self.toast("DEBUG: SPEED x%d" % self.scene.fast)
            elif key == pygame.K_F3:
                self.run.money += 10000
                self.toast("DEBUG: +$10000")
        self.scene.on_key(key)

    def tick(self, dt):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.quit()
            elif ev.type == pygame.MOUSEMOTION:
                self.mouse = self.to_canvas(ev.pos)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                self.mouse = self.to_canvas(ev.pos)
                self.scene.on_click(self.mouse)
            elif ev.type == pygame.MOUSEWHEEL:
                self.scene.on_wheel(ev.y)
            elif ev.type == pygame.KEYDOWN:
                self.handle_key(ev.key)
        self.mouse = self.to_canvas(pygame.mouse.get_pos())
        self.scene.update(dt)
        for t in self.toasts:
            t[1] -= dt
        self.toasts = [t for t in self.toasts if t[1] > 0]
        self.scene.draw(self.canvas)
        self.draw_toasts()
        gfx.draw_cursor(self.canvas, self.mouse)
        self.present()

    def main_loop(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.1)
            self.tick(dt)
        pygame.quit()
