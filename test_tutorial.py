"""Coverage for the reusable Moss dialogue layer and first-run tutorial flow."""

import os
import tempfile
import unittest
from unittest.mock import patch

import pygame

from . import gfx
from .settings import ACCENT, CANVAS_H, CANVAS_W
from .sprites_data import GRIDS, PALETTE
from .tutorial import BOX_H, BOX_W, BOX_X, BOX_Y, DialogueOverlay, DialogueStep, guide_steps, tutorial_steps


class TutorialAppTests(unittest.TestCase):
    def setUp(self):
        pygame.init()
        pygame.display.set_mode((1, 1))
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"BLOOM_SAVE_DIR": self.tmp.name})
        self.env.start()
        from .app import App
        self.app = App()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def finish_dialogue(self):
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        while self.app.dialogue_modal is modal:
            modal.on_key(pygame.K_SPACE)

    def test_new_run_opens_packs_tutorial_and_blocks_scene_input(self):
        self.app.new_run()
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        self.assertIs(self.app.active_modal(), modal)
        packs_before = len(self.app.run.packs)
        seeds_before = dict(self.app.run.seeds)
        btn = self.app.scene.open_btn
        self.app.handle_click((btn.x + 2, btn.y + 2))
        self.assertEqual(len(self.app.run.packs), packs_before)
        self.assertEqual(self.app.run.seeds, seeds_before)
        self.assertIs(self.app.dialogue_modal, modal)
        self.assertEqual(modal.index, 1)  # the click advanced dialogue, not the scene
        self.app.handle_key(pygame.K_SPACE)
        self.assertEqual(len(self.app.run.packs), packs_before)
        self.assertIs(self.app.dialogue_modal, modal)
        self.assertEqual(modal.index, 2)

    def test_finishing_stages_persists_and_later_stages_open_once(self):
        from .save import SaveManager
        self.app.new_run()
        self.finish_dialogue()
        self.assertIn("packs", self.app.profile["tutorial_done"])
        self.assertIsNone(self.app.dialogue_modal)

        self.app.scene.go()
        self.assertEqual(self.app.scene_name, "round")
        self.assertIsNotNone(self.app.dialogue_modal)
        self.app.run.start_timer()
        before = self.app.run.time_left
        self.app.tick(0.5)
        self.assertEqual(self.app.run.time_left, before)
        self.finish_dialogue()
        self.assertIn("round", self.app.profile["tutorial_done"])

        self.app.goto("summary")
        self.app.scene.go_shop()
        self.assertEqual(self.app.scene_name, "shop")
        self.assertIsNotNone(self.app.dialogue_modal)
        self.finish_dialogue()
        self.assertIn("shop", self.app.profile["tutorial_done"])
        self.assertEqual(SaveManager().load_profile()["tutorial_done"], ["packs", "round", "shop"])

        self.app.scene.go()
        self.assertEqual(self.app.scene_name, "packs")
        self.assertIsNone(self.app.dialogue_modal)

    def test_skip_marks_every_stage_done_and_persists(self):
        from .save import SaveManager
        self.app.new_run()
        modal = self.app.dialogue_modal
        modal.on_key(pygame.K_ESCAPE)
        self.assertIsNone(self.app.dialogue_modal)
        self.assertEqual(set(self.app.profile["tutorial_done"]), {"packs", "round", "shop"})
        self.assertEqual(set(SaveManager().load_profile()["tutorial_done"]), {"packs", "round", "shop"})
        self.app.scene.go()
        self.assertIsNone(self.app.dialogue_modal)

    def test_title_guide_replays_without_a_run_or_tutorial_progress(self):
        self.app.goto("title")
        btn = self.app.scene.guide_btn
        self.app.handle_click((btn.x + 2, btn.y + 2))
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        self.assertIsNone(self.app.run)
        self.finish_dialogue()
        self.assertIsNone(self.app.dialogue_modal)
        self.assertEqual(self.app.profile["tutorial_done"], [])

    def test_dialogue_box_geometry_and_targets_stay_visible(self):
        area = BOX_W * BOX_H
        self.assertGreaterEqual(area, (CANVAS_W * CANVAS_H) // 6)
        self.assertLessEqual(area, (CANVAS_W * CANVAS_H) // 4)
        self.assertGreater(CANVAS_H - (BOX_Y + BOX_H), 0)
        self.app.new_run()
        for stage in ("packs", "round", "shop"):
            self.app.goto(stage)
            modal = DialogueOverlay(self.app, tutorial_steps(stage, self.app.scene))
            self.app.dialogue_modal = modal
            for index in range(len(modal.pages)):
                modal.index = index
                box = modal.box_rect()
                target = modal.target_rect()
                self.assertGreaterEqual(box[0], 0)
                self.assertGreaterEqual(box[1], 14)
                self.assertLessEqual(box[0] + box[2], CANVAS_W)
                self.assertLessEqual(box[1] + box[3], CANVAS_H)
                portrait = modal.portrait_rect()
                self.assertGreaterEqual(portrait[0], 0)
                self.assertGreaterEqual(portrait[1], 0)
                self.assertLessEqual(portrait[0] + portrait[2], CANVAS_W)
                self.assertLessEqual(portrait[1] + portrait[3], CANVAS_H)
                # The box sits beside Moss, never on top of him.
                self.assertFalse(
                    box[0] < portrait[0] + portrait[2] and portrait[0] < box[0] + box[2]
                    and box[1] < portrait[1] + portrait[3] and portrait[1] < box[1] + box[3],
                    (stage, index, box, portrait),
                )
                if target:
                    for rect in (box, portrait):
                        overlap = (
                            rect[0] < target[0] + target[2] and target[0] < rect[0] + rect[2]
                            and rect[1] < target[1] + target[3] and target[1] < rect[1] + rect[3]
                        )
                        self.assertFalse(overlap, (stage, index, rect, target))

    def test_dialogue_draws_white_box_portrait_and_arrow(self):
        self.app.new_run()
        modal = self.app.dialogue_modal
        while modal.target_rect() is None:
            modal.advance()
        surf = pygame.Surface((CANVAS_W, CANVAS_H))
        self.app.scene.draw(surf)
        modal.draw(surf, (160, 90))
        x, y, w, h = modal.box_rect()
        self.assertEqual(tuple(surf.get_at((x + w // 2, y + h // 2)))[:3], (245, 240, 230))
        px0, py0, pw, ph = modal.portrait_rect()
        # Moss is drawn natively at portrait size, not a blown-up tiny sprite.
        self.assertGreaterEqual(pw, 90)
        self.assertGreaterEqual(ph, 150)
        self.assertEqual(gfx.sprite("moss").get_size(), (pw, ph))
        portrait_pixels = {
            tuple(surf.get_at((px, py)))[:3]
            for px in range(px0, px0 + pw) for py in range(py0, py0 + ph)
            if surf.get_at((px, py)).a
        }
        self.assertGreater(len(portrait_pixels), 12)
        arrow_pixels = sum(
            1 for px in range(CANVAS_W) for py in range(14, y)
            if tuple(surf.get_at((px, py)))[:3] == ACCENT
        )
        self.assertGreater(arrow_pixels, 0)

    def test_long_text_paginates_and_back_navigation_works(self):
        modal = DialogueOverlay(self.app, [DialogueStep("WORD " * 80)])
        self.app.dialogue_modal = modal
        self.assertGreater(len(modal.pages), 1)
        modal.on_key(pygame.K_RIGHT)
        self.assertEqual(modal.index, 1)
        modal.on_key(pygame.K_LEFT)
        self.assertEqual(modal.index, 0)
        modal.on_click((1, 1))
        self.assertEqual(modal.index, 1)

    def test_moss_sprite_is_rectangular_and_uses_known_palette(self):
        rows = GRIDS["moss"]
        self.assertEqual(len({len(row) for row in rows}), 1)
        self.assertTrue(set("".join(rows)) <= set(PALETTE) | {"."})
        self.assertEqual(gfx.sprite("moss").get_size(), (len(rows[0]), len(rows)))
        self.assertNotEqual(
            pygame.image.tobytes(gfx.sprite("moss"), "RGBA"),
            pygame.image.tobytes(gfx.sprite("unknown"), "RGBA"),
        )

    def test_guide_steps_use_the_same_dialogue_layer(self):
        modal = DialogueOverlay(self.app, guide_steps())
        self.assertTrue(modal.pages)
        self.assertIsNone(modal.target_rect())

    def test_tutorial_text_uses_only_supported_font_glyphs(self):
        from .sprites_data import FONT
        from .tutorial import TUTORIAL_BUILDERS
        texts = [step.text for step in guide_steps()]
        for builder in TUTORIAL_BUILDERS.values():
            texts.extend(step.text for step in builder())
        missing = {ch for text in texts for ch in text.upper() if ch not in FONT}
        self.assertEqual(missing, set())