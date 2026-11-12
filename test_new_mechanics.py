"""Coverage for manual harvesting, exquisite relics, and the Relic Cabinet."""
import os
import tempfile
import unittest
from unittest.mock import patch

from . import data
from .state import Plot, Run


class HarvestTests(unittest.TestCase):
    def make_run(self, species="daisy", cellar=False):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.begin_round()
        run.cellar_unlocked = True
        (run.cellar_plots if cellar else run.plots)[0] = Plot(species)
        run.start_timer()
        return run

    def test_manual_maturity_harvest_and_reset_on_both_boards(self):
        for cellar, species in ((False, "daisy"), (True, "brown_mushroom")):
            with self.subTest(cellar=cellar):
                run = self.make_run(species, cellar)
                p = (run.cellar_plots if cellar else run.plots)[0]
                run.update(12)
                self.assertEqual(p.progress, data.PLANTS[species]["grow"])
                self.assertEqual(run.counters["harvest"], 0)
                self.assertTrue(run.harvest(0, cellar))
                self.assertEqual(p.progress, 0)
                self.assertEqual(p.mature_time, 0)
                self.assertFalse(run.harvest(0, cellar))
                self.assertEqual(run.counters["harvest"], 1)

    def test_auto_repeats_and_switching_harvests_ripe_plant(self):
        run = self.make_run()
        run.update(7)
        run.auto_harvest = True
        run.update(3)
        self.assertEqual(run.counters["harvest"], 1)
        self.assertAlmostEqual(run.plots[0].progress, 3)

    def test_crystal_time_is_elapsed_not_growth_and_resets(self):
        run = self.make_run("crystal_bloom")
        run.plots[0].progress = 24
        run.plots[0].water_left = 2
        run.update(3.7)  # 0.5s to maturity at double speed, 3.2s mature
        p = run.plots[0]
        self.assertAlmostEqual(p.mature_time, 3.2)
        self.assertEqual(run.harvest_value(0), 260)
        self.assertTrue(run.harvest(0))
        self.assertEqual(p.mature_time, 0)
        self.assertEqual(run.harvest_value(0), 200)
        self.assertEqual(Plot.from_dict(Plot("crystal_bloom", mature_time=3.5).to_dict()).mature_time, 3.5)

    def test_auto_crystal_has_no_wait_bonus(self):
        run = self.make_run("crystal_bloom")
        run.auto_harvest = True
        run.update(26)
        self.assertEqual(run.round_income, 200)
        self.assertEqual(run.plots[0].mature_time, 0)


class RelicTests(unittest.TestCase):
    def weather(self, kind):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: kind
        run.relics = ["clear_skies"]
        run.begin_round()
        run.time_total = run.time_left = 20
        run.plots = [Plot("orchid") for _ in range(5)]
        run.start_timer()
        return run

    def test_clear_good_bad_boss_and_halfway_blight(self):
        for kind in ("sunny", "locusts", "blight", "crow_swarm", "hailstorm", "heatwave"):
            with self.subTest(kind=kind):
                run = self.weather(kind)
                with patch.object(run.rng, "random", return_value=0.24):
                    run.update(15)
                self.assertTrue(run.weather_cleared)
                self.assertEqual(run.twist()["name"], "Fair Weather")
                self.assertEqual(run.time_total, 20)
                self.assertEqual(sum(e["kind"] == "weather_clear" for e in run.events), 1)
                if kind == "blight":
                    self.assertFalse(any(e["kind"] == "wither" for e in run.events))
                if kind == "sunny":
                    self.assertAlmostEqual(run.plots[0].progress, 17.5)

    def test_failed_roll_only_once_and_no_relic_no_roll(self):
        run = self.weather("sunny")
        with patch.object(run.rng, "random", return_value=0.25) as roll:
            run.update(10)
            run.update(1)
            self.assertEqual(roll.call_count, 1)
        self.assertFalse(run.weather_cleared)
        self.assertEqual(run.twist()["growth"], 1.25)
        run = self.weather("sunny")
        run.relics = []
        with patch.object(run.rng, "random") as roll:
            run.update(11)
            roll.assert_not_called()

    def test_choose_one_plant_in_cellar_and_growth_yield(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["chosen_bloom"]
        run.begin_round()
        run.cellar_unlocked = True
        run.cellar_plots[0] = Plot("brown_mushroom")
        run.plots[0] = Plot("daisy")
        self.assertTrue(run.choose_plant(0, True))
        self.assertFalse(run.choose_plant(0))
        self.assertEqual(run.harvest_value(0, True), 6)
        self.assertEqual(run.harvest_value(0), 2)
        self.assertAlmostEqual(run.plot_growth_speed(0, True), 0.75 * 1.5)
        run.start_timer()
        run.update(2)
        self.assertAlmostEqual(run.cellar_plots[0].progress, 2 * 0.75 * 1.5)
        run.remove_plant(0, True)
        self.assertFalse(run.choose_plant(0))
        run.begin_round()
        run.plots[0] = Plot("daisy")
        self.assertTrue(run.choose_plant(0))

    def test_cabinet_slots_discount_and_save(self):
        run = Run(seed=1)
        price = run.relic_price("green_thumb")
        run.perks["relics"] = 1
        self.assertEqual(run.relic_price("green_thumb"), int(price * 0.85))
        run.perks["relics"] = 2
        self.assertEqual(run.relic_slots(), 6)
        run.relics = data.RELIC_ORDER[:5]
        run.shop_offers = [data.RELIC_ORDER[5]]
        run.money = 1000000
        self.assertTrue(run.buy_relic(0)[0])
        self.assertEqual(len(Run.from_dict(run.to_dict()).relics), 6)
        run.perks["relics"] = 3
        run.roll_offers()
        self.assertEqual(len(run.shop_offers), 4)
        self.assertEqual(len(set(run.shop_offers)), 4)
        self.assertEqual(len(Run.from_dict(run.to_dict()).shop_offers), 4)

    def test_upgrading_parked_shop_adds_offer_without_reroll(self):
        run = Run(seed=3, perks={"relics": 2})
        run.enter_shop()
        before = list(run.shop_offers)
        run.buy_heirloom("relics", 10000)
        self.assertEqual(run.shop_offers[:3], before)
        self.assertEqual(len(run.shop_offers), 4)
        self.assertEqual(len(set(run.shop_offers)), 4)

    def test_weather_reset_before_next_forecast(self):
        run = self.weather("sunny")
        with patch.object(run.rng, "random", return_value=0):
            run.update(10)
        self.assertEqual(run.twist()["growth"], 1)
        run.start_next_round()
        self.assertEqual(run.twist()["growth"], 1.25)


class InterfaceTests(unittest.TestCase):
    def test_settings_and_selection_shop_interactions(self):
        from .app import App
        from .round import plot_rect
        from .save import SaveManager
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            self.assertFalse(app.settings_cfg["auto_harvest"])
            app.open_settings()
            button = app.settings_modal.harvest_btn
            app.handle_click((button.x + 2, button.y + 2))
            self.assertTrue(SaveManager().load_profile()["settings"]["auto_harvest"])
            app.settings_modal.close()
            app.new_run()
            app.run.relics = ["chosen_bloom"]
            app.goto("round")
            app.run.plots[0] = Plot("daisy")
            app.handle_click((248, 49))
            self.assertTrue(app.scene.choose_mode)
            x, y, w, h = plot_rect(0)
            app.handle_click((x + w // 2, y + h // 2))
            self.assertTrue(app.run.is_chosen(0))
            app.run.start_timer()
            app.run.plots[0].progress = data.PLANTS["daisy"]["grow"]
            app.handle_click((x + w // 2, y + h // 2))
            self.assertEqual(app.run.counters["harvest"], 1)
            self.assertEqual(app.run.plots[0].progress, 0)
            app.scene.draw(app.canvas)
            app.run.perks["relics"] = 3
            app.run.enter_shop()
            app.goto("shop")
            self.assertEqual(len(app.scene.buy_buttons), 4)
            self.assertEqual(len(app.scene.sell_buttons), 6)
            app.run.money = 1000000
            app.scene.refresh()
            fourth = app.scene.buy_buttons[3]
            rid = app.run.shop_offers[3]
            app.handle_click((fourth.x + 2, fourth.y + 2))
            self.assertIn(rid, app.run.relics)
            app.scene.draw(app.canvas)
            app.goto("shelf")
            app.scene.draw(app.canvas)


class CellarPlotBuyabilityTests(unittest.TestCase):
    def test_cellar_plots_unlock_for_purchase_after_12_garden_plots_and_persist(self):
        from .settings import CELLAR_PLOTS, MAX_PLOTS
        run = Run(seed=7)
        run.money = 10**12

        while len(run.plots) < MAX_PLOTS:
            self.assertFalse(run.next_plot_is_cellar())
            self.assertTrue(run.buy_plot())
        self.assertEqual(len(run.plots), MAX_PLOTS)
        self.assertEqual(len(run.cellar_plots), CELLAR_PLOTS)
        self.assertTrue(run.can_buy_plot())
        self.assertTrue(run.next_plot_is_cellar())

        while len(run.cellar_plots) < MAX_PLOTS:
            self.assertTrue(run.buy_plot())
        self.assertTrue(run.cellar_unlocked)
        self.assertEqual(len(run.cellar_plots), MAX_PLOTS)
        self.assertFalse(run.can_buy_plot())
        self.assertFalse(run.buy_plot())

        restored = Run.from_dict(run.to_dict())
        self.assertEqual(len(restored.plots), MAX_PLOTS)
        self.assertEqual(len(restored.cellar_plots), MAX_PLOTS)
        self.assertTrue(restored.cellar_unlocked)

    def test_shop_scene_offers_cellar_plots_after_garden_is_full(self):
        from .app import App
        from .settings import MAX_PLOTS
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            app.new_run()
            run = app.run
            run.money = 10**12
            run.plots = [Plot() for _ in range(MAX_PLOTS - 1)]
            run.enter_shop()
            app.goto("shop")
            self.assertIn("PLOT (11/12)", app.scene.plot_btn.label)

            btn = app.scene.plot_btn
            app.handle_click((btn.x + 4, btn.y + 4))
            self.assertEqual(len(run.plots), MAX_PLOTS)
            self.assertIn("CELLAR (4/12)", app.scene.plot_btn.label)
            self.assertTrue(app.scene.plot_btn.enabled)

            app.handle_click((btn.x + 4, btn.y + 4))
            self.assertEqual(len(run.cellar_plots), 5)
            self.assertEqual(app.scene.msg, "NEW CELLAR PLOT!")
            self.assertIn("CELLAR (5/12)", app.scene.plot_btn.label)


class HeirloomArtworkTests(unittest.TestCase):
    def test_every_heirloom_has_distinct_12x12_artwork_and_renders_on_shelf_and_pause(self):
        from . import gfx
        from .app import App
        from .sprites_data import GRIDS, PALETTE

        seen_art = set()
        for key in data.PERK_ORDER:
            perk = data.PERKS[key]
            art_id = perk["art"]
            self.assertIn(art_id, GRIDS)
            self.assertNotIn(art_id, seen_art)
            seen_art.add(art_id)
            rows = GRIDS[art_id]
            self.assertEqual(len(rows), 12)
            self.assertTrue(all(len(row) == 12 for row in rows))
            self.assertTrue(set("".join(rows)) <= set(PALETTE) | {"."})
            self.assertTrue(perk.get("lore"))
            self.assertEqual(gfx.sprite(art_id, 1).get_size(), (12, 12))

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            app.profile["heirlooms"] = 50
            app.profile["perks"] = {"cash": 2, "plots": 1, "relics": 1}
            app.goto("shelf")
            app.scene.update(0.5)
            app.mouse = (40, app.scene.ROW_Y + 6)
            app.scene.draw(app.canvas)

            app.new_run()
            app.goto("round")
            app.open_pause()
            app.pause_modal.draw(app.canvas, (180, 75))


class ShovelSpriteAndCursorTests(unittest.TestCase):
    def test_shovel_sprite_and_cursor_switch_in_shovel_mode(self):
        import pygame
        from . import gfx
        from .app import App
        from .sprites_data import GRIDS

        shovel_rows = GRIDS["shovel"]
        self.assertEqual((len(shovel_rows[0]), len(shovel_rows)), (12, 12))
        chars = set("".join(shovel_rows))
        self.assertTrue({"w", "d", "D", "b", "B"} <= chars)
        self.assertNotEqual(shovel_rows[11][0], ".")

        s_normal = pygame.Surface((40, 40), pygame.SRCALPHA)
        s_shovel = pygame.Surface((40, 40), pygame.SRCALPHA)
        gfx.draw_cursor(s_normal, (16, 20), "cursor")
        gfx.draw_cursor(s_shovel, (16, 20), "shovel")
        self.assertNotEqual(pygame.image.tobytes(s_normal, "RGBA"), pygame.image.tobytes(s_shovel, "RGBA"))
        self.assertGreater(s_shovel.get_at((16, 20)).a, 0)

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            app.new_run()
            app.goto("round")
            self.assertEqual(app.cursor_kind(), "cursor")
            app.scene.toggle_shovel()
            self.assertTrue(app.scene.shovel_mode)
            self.assertEqual(app.cursor_kind(), "shovel")
            app.open_pause()
            self.assertEqual(app.cursor_kind(), "cursor")


class PlantSpriteAnimationTests(unittest.TestCase):
    def test_family_styles_and_animated_frames_move_cleanly(self):
        import pygame
        from . import gfx

        self.assertEqual(gfx.plant_anim_style("daisy", data.PLANTS["daisy"], "daisy"), "flower")
        self.assertEqual(gfx.plant_anim_style("venus_flytrap", data.PLANTS["venus_flytrap"], "venus_flytrap"), "carnivore")
        self.assertEqual(gfx.plant_anim_style("mycelium", data.PLANTS["mycelium"], "mycelium"), "mushroom")
        self.assertEqual(gfx.plant_anim_style("wheat", data.PLANTS["wheat"], "wheat"), "reed")
        self.assertEqual(gfx.plant_anim_style("cactus", data.PLANTS["cactus"], "cactus"), "cactus")
        self.assertEqual(gfx.plant_anim_style("pumpkin", data.PLANTS["pumpkin"], "pumpkin"), "crop")
        self.assertEqual(gfx.plant_anim_style("daisy", data.PLANTS["daisy"], "seed"), "seed")

        for sid in ("daisy", "venus_flytrap", "mycelium", "wheat", "pumpkin"):
            sp = data.PLANTS[sid]
            style = gfx.plant_anim_style(sid, sp, sid)
            frames = set()
            for step in range(8):
                surf = pygame.Surface((36, 36), pygame.SRCALPHA)
                anim = gfx.plant_anim(0.15 + step * 0.22, index=0, style=style, started=True, ripe=True, speed=1.3)
                gfx.draw_sprite(surf, sid, 6, 6, 2, sp.get("subs"), anim=anim)
                frames.add(pygame.image.tobytes(surf, "RGBA"))
            self.assertGreater(len(frames), 1, sid)


class CrittersAndFoliageTests(unittest.TestCase):
    def test_critter_progression_from_insects_to_woodland_to_aliens(self):
        from . import ambient

        r1 = ambient.choose_critter_roster(1, seed=3, cellar=False)
        self.assertTrue(r1)
        self.assertTrue(all(ambient.CRITTER_SPECIES[c]["tier"] == "insect" for c in r1))

        r24 = ambient.choose_critter_roster(24, seed=3, cellar=False)
        self.assertIn("mouse", r24)
        self.assertIn("rabbit", r24)

        r100 = ambient.choose_critter_roster(100, seed=3, cellar=False)
        self.assertIn("alien", r100)
        self.assertIn("ufo", r100)
        self.assertIn("void", r100)

    def test_seasonal_foliage_and_weather_stay_below_topbar(self):
        import pygame
        from . import ambient
        from .round import plot_rect

        rects = [plot_rect(i) for i in range(4)]
        for rnd, twist_name, cellar in (
            (1, "rain", False),
            (10, "drought", False),
            (18, "gale", False),
            (26, "frost", False),
            (100, "eclipse", False),
            (24, "none", True),
        ):
            run = Run(seed=9)
            run.round = rnd
            run.twist_id = lambda _r=None, tw=twist_name: tw
            amb = ambient.GardenAmbient(run)
            for _ in range(10):
                amb.update(0.12, run, cellar=cellar)
            surf = pygame.Surface((320, 180))
            surf.fill((0, 0, 0))
            amb.draw_foliage(surf, run, cellar=cellar, plot_rects=rects)
            amb.draw_foreground(surf, run, cellar=cellar)

            # Topbar region y=0..13 must remain completely untouched.
            top_lit = sum(
                1 for y in range(14) for x in range(320)
                if surf.get_at((x, y))[:3] != (0, 0, 0)
            )
            self.assertEqual(top_lit, 0)
            board_lit = sum(
                1 for y in range(32, 148) for x in range(244)
                if surf.get_at((x, y))[:3] != (0, 0, 0)
            )
            self.assertGreater(board_lit, 20)


class RoadmapBossTests(unittest.TestCase):
    def pinned(self, twist, round_number=9):
        run = Run(seed=17)
        run.round = round_number
        run.twist_id = lambda _rnd=None, value=twist: value
        run.begin_round()
        run.start_timer()
        run.time_total = run.time_left = 60.0
        return run

    def test_queen_bee_only_allows_honey_plants_to_work(self):
        run = self.pinned("queen_bee", round_number=36)
        run.plots = [Plot("daisy"), Plot("tomato")]
        run.update(2.0)
        self.assertGreater(run.plots[0].progress, 0.0)
        self.assertEqual(run.plots[1].progress, 0.0)
        self.assertFalse(run.plant_disabled(0))
        self.assertTrue(run.plant_disabled(1))
        self.assertFalse(run.can_water(1))

    def test_autumn_ghost_swaps_and_restarts_two_plants(self):
        run = self.pinned("ghost", round_number=27)
        run.plots = [Plot("daisy", progress=2.0), Plot("tomato", progress=3.0)]
        run.update(5.0)
        self.assertEqual([p.species for p in run.plots], ["tomato", "daisy"])
        self.assertEqual([p.progress for p in run.plots], [0.0, 0.0])
        swaps = [event for event in run.events if event["kind"] == "ghost_swap"]
        self.assertEqual(len(swaps), 1)
        self.assertEqual({swaps[0]["plot"], swaps[0]["other_plot"]}, {0, 1})

    def test_ghosts_in_the_rotating_roster_are_autumn_only(self):
        run = Run(seed=1)
        ghost_rounds = [rnd for rnd in range(9, 9 * 41, 9) if run.twist_id(rnd) == "ghost"]
        self.assertTrue(ghost_rounds)
        self.assertTrue(all(data.season(rnd)["name"] == "Autumn" for rnd in ghost_rounds))
        self.assertIn("queen_bee", data.BOSS_TWISTS)

        # The restriction is metadata-driven rather than an accidental result
        # of the current roster order.
        with patch.object(data, "BOSS_TWISTS", ["ghost", "crow_swarm"]):
            self.assertEqual(run.twist_id(9), "crow_swarm")
            self.assertEqual(run.twist_id(27), "ghost")

    def test_first_round_is_always_fair_weather(self):
        self.assertTrue(all(Run(seed=seed).twist_id(1) == "none" for seed in range(50)))


class RoadmapAmbientTests(unittest.TestCase):
    def test_critter_cap_and_offscreen_visits(self):
        import random
        from . import ambient

        for rnd in (1, 18, 24, 45, 100, 999):
            self.assertLessEqual(ambient.target_critter_count(rnd), ambient.MAX_ONSCREEN_CRITTERS)
            self.assertLessEqual(len(ambient.choose_critter_roster(rnd, seed=4)), 3)

        critter = ambient.Critter("ant", random.Random(2))
        critter.axis = "x"
        critter.x = float(ambient.BOARD_LEFT)
        critter.y = float(ambient.LANE_YS[1])
        critter.dir = -1.0
        critter.leaving = True
        critter.pause = 0.0
        critter.update(2.0, random.Random(3))
        self.assertLess(critter.x, ambient.BOARD_LEFT)
        self.assertTrue(critter.offscreen)
        self.assertGreater(critter.away, 0.0)

    def test_surface_lanes_have_no_scattered_foliage(self):
        import pygame
        from . import ambient

        run = Run(seed=3)
        manager = ambient.GardenAmbient(run)
        surf = pygame.Surface((320, 180))
        surf.fill((0, 0, 0))
        manager.draw_foliage(surf, run, cellar=False, plot_rects=[(4, 36, 56, 34)])
        self.assertEqual(
            sum(surf.get_at((x, y))[:3] != (0, 0, 0) for y in range(180) for x in range(320)),
            0,
        )

    def test_each_season_has_dedicated_topbar_art(self):
        from .sprites_data import GRIDS

        arts = [season["art"] for season in data.SEASONS]
        self.assertEqual(len(set(arts)), 4)
        self.assertTrue(all(art in GRIDS for art in arts))


class GardenIndexTests(unittest.TestCase):
    def make_scene(self):
        from .index import IndexScene

        class AppStub:
            profile = {"perks": {}, "harvested": {}, "heirlooms": 0}
            run = None
            mouse = (-1, -1)

            def goto(self, _name):
                pass

        scene = IndexScene(AppStub())
        scene.on_enter()
        return scene

    def test_garden_index_has_two_top_sections_and_nested_subsections(self):
        from .index import CATEGORIES, SECTIONS, UPGRADE_SUBSECTIONS

        scene = self.make_scene()
        self.assertEqual(SECTIONS, [("plants", "PLANTS"), ("upgrades", "UPGRADES")])
        self.assertEqual(scene.section, "plants")
        self.assertEqual(scene.subsections(), CATEGORIES)
        self.assertEqual(len(scene.section_buttons), 2)
        self.assertEqual(len(scene.subsection_buttons), len(CATEGORIES))

        scene.set_section("upgrades")
        self.assertEqual(scene.section, "upgrades")
        self.assertEqual(scene.subsections(), UPGRADE_SUBSECTIONS)
        self.assertEqual(
            [sid for sid, _label in scene.subsections()],
            ["relics", "heirlooms"],
        )
        self.assertEqual(len(scene.subsection_buttons), 2)

    def test_upgrade_subsections_contain_every_relic_and_heirloom(self):
        scene = self.make_scene()
        scene.set_section("upgrades")
        scene.set_subsection("relics")
        self.assertEqual(scene.entry_type, "relics")
        self.assertEqual(scene.entries(), data.RELIC_ORDER)
        scene.set_subsection("heirlooms")
        self.assertEqual(scene.entry_type, "heirlooms")
        self.assertEqual(scene.entries(), data.PERK_ORDER)
