"""Modal overlays layered above active scenes: confirmations, settings, and mid-run pause."""

import pygame

from . import data, gfx
from .gfx import Button
from .settings import ACCENT, BAD, DIM, GOOD, PANEL_DARK, PANEL_LIGHT, TEXT


class ConfirmModal:
    """Two-button confirmation prompt that cancels when clicked outside its frame."""

    def __init__(self, app, title, message, on_confirm, confirm_label="CONFIRM", danger=True):
        self.app = app
        self.title = title
        self.message = message
        self.on_confirm = on_confirm
        self.danger = danger
        self.box = (52, 42, 216, 96)
        bx, by, bw, bh = self.box
        btn_col = (150, 70, 60) if danger else (70, 130, 70)
        self.confirm_btn = Button(bx + 14, by + bh - 25, 90, 18, confirm_label, self._do_confirm, color=btn_col)
        self.cancel_btn = Button(bx + bw - 104, by + bh - 25, 90, 18, "CANCEL", self._do_cancel, color=PANEL_LIGHT)
        self.buttons = [self.confirm_btn, self.cancel_btn]

    def _do_confirm(self):
        cb = self.on_confirm
        self.app.confirm_modal = None
        if cb:
            cb()

    def _do_cancel(self):
        self.app.confirm_modal = None

    def on_click(self, pos):
        for b in self.buttons:
            if b.click(pos):
                return True
        if not gfx.inside(pos, self.box):
            self._do_cancel()
        return True

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            self._do_cancel()
        elif key == pygame.K_RETURN:
            self._do_confirm()

    def draw(self, surf, mouse):
        gfx.dim_overlay(surf, 170)
        bx, by, bw, bh = self.box
        stripe = BAD if self.danger else ACCENT
        gfx.panel(surf, bx, by, bw, bh, fill=(38, 32, 58), border=PANEL_DARK)
        gfx.rect(surf, stripe, bx + 1, by + 1, bw - 2, 2)
        gfx.draw_text(surf, self.title, bx + bw // 2, by + 10, stripe, align="center")
        gfx.rect(surf, PANEL_DARK, bx + 12, by + 20, bw - 24, 1)
        lines = gfx.wrap(self.message, bw - 24)
        start_y = by + 28 + max(0, (30 - len(lines) * 8) // 2)
        for i, line in enumerate(lines[:4]):
            gfx.draw_text(surf, line, bx + bw // 2, start_y + i * 8, TEXT, align="center")
        for b in self.buttons:
            b.draw(surf, mouse)


class SettingsModal:
    """Display and UX preference controls persisted into profile.json."""

    def __init__(self, app):
        self.app = app
        self.box = (36, 16, 248, 148)
        bx, by, bw, bh = self.box
        rx = bx + bw - 82
        self.fs_btn = Button(rx, by + 28, 70, 15, "", self._toggle_fs)
        self.bl_btn = Button(rx, by + 48, 70, 15, "", self._toggle_bl)
        self.scale_down = Button(rx, by + 68, 18, 15, "-", lambda: self._step_scale(-1))
        self.scale_up = Button(rx + 52, by + 68, 18, 15, "+", lambda: self._step_scale(1))
        self.conf_btn = Button(rx, by + 88, 70, 15, "", self._toggle_confirm)
        self.float_btn = Button(rx, by + 108, 70, 15, "", self._toggle_floaters)
        self.done_btn = Button(bx + (bw - 80) // 2, by + bh - 21, 80, 16, "DONE", self.close, color=(70, 130, 70))
        self.buttons = [
            self.fs_btn, self.bl_btn, self.scale_down, self.scale_up,
            self.conf_btn, self.float_btn, self.done_btn,
        ]
        self.refresh()

    def refresh(self):
        cfg = self.app.settings_cfg
        self.fs_btn.label = "ON" if self.app.fullscreen else "OFF"
        self.fs_btn.color = (70, 130, 70) if self.app.fullscreen else PANEL_LIGHT
        self.bl_btn.label = "ON" if self.app.borderless else "OFF"
        self.bl_btn.color = (70, 130, 70) if self.app.borderless else PANEL_LIGHT
        scale = int(cfg.get("scale", 6))
        windowed = not self.app.fullscreen and not self.app.borderless
        self.scale_down.enabled = windowed and scale > 2
        self.scale_up.enabled = windowed and scale < 8
        conf = bool(cfg.get("confirmations", True))
        self.conf_btn.label = "ON" if conf else "OFF"
        self.conf_btn.color = (70, 130, 70) if conf else PANEL_LIGHT
        flt = bool(cfg.get("floaters", True))
        self.float_btn.label = "ON" if flt else "OFF"
        self.float_btn.color = (70, 130, 70) if flt else PANEL_LIGHT

    def _toggle_fs(self):
        self.app.toggle_fullscreen()
        self.refresh()

    def _toggle_bl(self):
        self.app.toggle_borderless()
        self.refresh()

    def _step_scale(self, delta):
        self.app.set_window_scale(int(self.app.settings_cfg.get("scale", 6)) + delta)
        self.refresh()

    def _toggle_confirm(self):
        self.app.settings_cfg["confirmations"] = not bool(self.app.settings_cfg.get("confirmations", True))
        self.app.save_settings()
        self.refresh()

    def _toggle_floaters(self):
        self.app.settings_cfg["floaters"] = not bool(self.app.settings_cfg.get("floaters", True))
        self.app.save_settings()
        self.refresh()

    def close(self):
        self.app.settings_modal = None

    def on_click(self, pos):
        for b in self.buttons:
            if b.click(pos):
                return True
        if not gfx.inside(pos, self.box):
            self.close()
        return True

    def on_key(self, key):
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
            self.close()

    def draw(self, surf, mouse):
        self.refresh()
        gfx.dim_overlay(surf, 175)
        bx, by, bw, bh = self.box
        gfx.panel(surf, bx, by, bw, bh, fill=(38, 33, 58), border=PANEL_DARK)
        gfx.rect(surf, ACCENT, bx + 1, by + 1, bw - 2, 2)
        gfx.draw_sprite(surf, "cog", bx + 9, by + 5)
        gfx.draw_text(surf, "SETTINGS", bx + 28, by + 8, ACCENT, scale=2)
        gfx.rect(surf, PANEL_DARK, bx + 10, by + 22, bw - 20, 1)

        rows = (
            ("FULLSCREEN (F11)", by + 33),
            ("BORDERLESS (F12)", by + 53),
            ("WINDOW SCALE", by + 73),
            ("CONFIRM PROMPTS", by + 93),
            ("FLOATING TEXT", by + 113),
        )
        for label, ry in rows:
            gfx.draw_text(surf, label, bx + 12, ry, TEXT)
        scale_txt = "%dX" % int(self.app.settings_cfg.get("scale", 6))
        col = DIM if (self.app.fullscreen or self.app.borderless) else ACCENT
        gfx.draw_text(surf, scale_txt, bx + bw - 47, by + 73, col, align="center")

        for b in self.buttons:
            b.draw(surf, mouse)


class PauseModal:
    """In-run pause overlay freezing round simulation and displaying active heirloom bonuses."""

    def __init__(self, app):
        self.app = app
        self.box = (18, 16, 284, 148)
        bx, by, bw, _bh = self.box
        self.cog_btn = Button(
            bx + bw - 25, by + 4, 19, 19, "", app.open_settings,
            icon="cog", chromeless=True, hover_subs=gfx.COG_HOVER_SUBS,
        )
        self.resume_btn = Button(bx + 10, by + 30, 88, 22, "RESUME", self.resume, color=(70, 130, 70))
        self.new_btn = Button(bx + 10, by + 57, 88, 22, "NEW RUN", self.new_run_clicked, color=PANEL_LIGHT)
        self.menu_btn = Button(bx + 10, by + 84, 88, 22, "MAIN MENU", self.main_menu_clicked, color=(96, 70, 140))
        self.quit_btn = Button(bx + 10, by + 111, 88, 22, "QUIT", self.quit_clicked, color=(150, 70, 60))
        self.buttons = [self.cog_btn, self.resume_btn, self.new_btn, self.menu_btn, self.quit_btn]

    def resume(self):
        self.app.pause_modal = None

    def new_run_clicked(self):
        def start_fresh():
            self.app.pause_modal = None
            self.app.new_run()

        self.app.ask_confirm(
            "START A NEW RUN?",
            "YOUR CURRENT RUN PROGRESS WILL BE LOST.",
            start_fresh,
            confirm_label="NEW RUN",
            danger=True,
        )

    def _mid_round_unsaved(self):
        run = self.app.run
        if not run or run.phase != "round":
            return False
        if run.started:
            return True
        return any(p.species is not None for group in (run.plots, run.cellar_plots) for p in group)

    def main_menu_clicked(self):
        def go_title():
            if self.app.run and self.app.run.phase in ("packs", "shop", "summary"):
                self.app.save_run()
            self.app.run = None
            self.app.pause_modal = None
            self.app.goto("title")

        if self._mid_round_unsaved():
            self.app.ask_confirm(
                "RETURN TO MAIN MENU?",
                "THIS ROUND'S PROGRESS WILL RESET TO PACKS.",
                go_title,
                confirm_label="MAIN MENU",
                danger=True,
            )
        else:
            go_title()

    def quit_clicked(self):
        def do_quit():
            if self.app.run and self.app.run.phase in ("packs", "shop", "summary"):
                self.app.save_run()
            self.app.pause_modal = None
            self.app.quit()

        msg = (
            "THIS ROUND'S PROGRESS WILL RESET TO PACKS."
            if self._mid_round_unsaved() else "YOUR PROGRESS BETWEEN ROUNDS IS SAVED."
        )
        self.app.ask_confirm("QUIT GAME?", msg, do_quit, confirm_label="QUIT", danger=True)

    def on_click(self, pos):
        for b in self.buttons:
            if b.click(pos):
                return True
        return True

    def on_key(self, key):
        if key == pygame.K_ESCAPE:
            self.resume()

    def draw(self, surf, mouse):
        gfx.dim_overlay(surf, 165)
        bx, by, bw, bh = self.box
        gfx.panel(surf, bx, by, bw, bh, fill=(38, 33, 58), border=PANEL_DARK)
        gfx.rect(surf, ACCENT, bx + 1, by + 1, bw - 2, 2)
        gfx.draw_text(surf, "PAUSED", bx + 10, by + 8, ACCENT, scale=2)

        run = self.app.run
        if run:
            season = run.season()
            gfx.draw_text(surf, "ROUND %d - %s" % (run.round, season["name"].upper()), bx + 88, by + 11, season["color"])

        hx, hy, hw, hh = bx + 106, by + 30, 168, 108
        gfx.panel(surf, hx, hy, hw, hh, "OWNED HEIRLOOMS", fill=(32, 27, 50))
        banked = int(self.app.profile.get("heirlooms", 0))
        gfx.draw_text(surf, "BANK: %d" % banked, hx + hw - 5, hy + 4, ACCENT, align="right")

        for i, key in enumerate(data.PERK_ORDER):
            perk = data.PERKS[key]
            level = run.perk(key) if run else int(self.app.profile["perks"].get(key, 0))
            ry = hy + 15 + i * 20
            owned = level > 0
            gfx.rect(surf, (44, 38, 66), hx + 4, ry, hw - 8, 18)
            gfx.rect(surf, GOOD if owned else (66, 58, 92), hx + 4, ry, 2, 18)
            gfx.draw_text(surf, perk["name"], hx + 9, ry + 2, TEXT if owned else DIM)
            gfx.draw_text(surf, "%d/%d" % (level, perk["max"]), hx + hw - 7, ry + 2, GOOD if owned else DIM, align="right")
            bonus = data.perk_text(key, level) if owned else "NONE OWNED"
            gfx.draw_text(surf, bonus, hx + 9, ry + 10, ACCENT if owned else DIM)

        if run:
            gfx.draw_text(surf, "EARNED SO FAR: +%d" % run.heirloom_reward(), hx + hw // 2, hy + hh - 10, ACCENT, align="center")

        for b in self.buttons:
            b.draw(surf, mouse)
        if self.cog_btn.hover(mouse):
            gfx.tooltip(surf, [("SETTINGS", ACCENT)], (self.cog_btn.x - 46, self.cog_btn.y + 13), 44)
