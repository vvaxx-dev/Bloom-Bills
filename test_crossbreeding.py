"""Crossbreeding: adjacent parents, weather/season gates, discovery, and rarity order."""

import unittest
from unittest import mock

from . import data
from .state import Plot, Run

# (child, parent A, parent B, condition twist or "autumn"/"any", grow, yield)
EXPECTED = {
    "eclipse_bloom": ("sunflower", "moonflower", "eclipse", 15, 150),
    "rainbow_daisy": ("daisy", "four_leaf_clover", "rain", 9, 45),
    "solar_saffron": ("saffron", "sunflower", "sunny", 24, 320),
    "spiny_pumpkin": ("cactus", "pumpkin", "drought", 22, 220),
    "frost_tomato": ("tomato", "cranberries", "frost", 16, 110),
    "ghost_bloom": ("pumpkin", "moonflower", "autumn", 18, 200),
    "maneater_tomato": ("venus_flytrap", "tomato", "any", 14, 90),
    "lucky_orchid": ("four_leaf_clover", "orchid", "any", 28, 380),
    "prism_bloom": ("crystal_bloom", "orchid", "any", 30, 450),
    "snap_aloe": ("aloe_vera", "venus_flytrap", "any", 15, 70),
    "desert_bloom": ("prickly_pear", "agave", "any", 26, 350),
    "eclipse_sovereign": ("sunflower_gold", "moonflower_blood", "eclipse", 18, 600),
}


def make_run(twist="none", round_no=1, seed=7):
    run = Run(seed=seed)
    run.round = round_no
    if twist is not None:
        run.twist_id = lambda _rnd=None, t=twist: t  # noqa: E731 - test double
    run.begin_round()
    run.started = True
    return run


def plant_pair(run, a, b, a_at=0, b_at=1, cellar_a=False, cellar_b=False):
    board_a = run.cellar_plots if cellar_a else run.plots
    board_b = run.cellar_plots if cellar_b else run.plots
    while len(board_a) <= a_at:
        board_a.append(Plot())
    while len(board_b) <= b_at:
        board_b.append(Plot())
    board_a[a_at] = Plot(a, progress=data.PLANTS[a]["grow"])
    board_b[b_at] = Plot(b, progress=data.PLANTS[b]["grow"])
    return board_a


class CrossbreedDataTests(unittest.TestCase):
    def test_all_twelve_crossbreeds_exist_with_requested_numbers(self):
        self.assertEqual(set(data.CROSSBREEDS), set(EXPECTED))
        self.assertEqual(len(data.CROSSBREED_ORDER), 12)
        for cid, (a, b, _cond, grow, yld) in EXPECTED.items():
            with self.subTest(crossbreed=cid):
                sp = data.PLANTS[cid]
                self.assertTrue(sp["crossbreed"])
                self.assertTrue(sp["no_mutations"])
                self.assertEqual(set(sp["parents"]), {a, b})
                self.assertEqual(sp["grow"], grow)
                self.assertEqual(sp["yield"], yld)
                self.assertGreaterEqual(sp["sell"], sp["yield"])
                self.assertIn(sp["rarity"], data.RARITY_COLORS)
                self.assertTrue(sp["hint"])
                self.assertTrue(sp["note"])
                self.assertEqual(data.mutants_for(cid), [])

    def test_no_pack_sells_a_crossbreed(self):
        for kind, pack in data.PACKS.items():
            for cid in data.CROSSBREEDS:
                self.assertNotIn(cid, pack["pool"], kind)
        for cid in data.CROSSBREEDS:
            self.assertEqual(data.packs_for_plant(cid), [])

    def test_inherited_mechanics(self):
        self.assertEqual(data.PLANTS["rainbow_daisy"]["bloom_chance"], 0.25)
        self.assertEqual(data.PLANTS["rainbow_daisy"]["bloom_mult"], 1.5)
        self.assertNotEqual(data.PLANTS["rainbow_daisy"].get("pays"), False)
        self.assertEqual(data.PLANTS["lucky_orchid"]["bloom_chance"], 0.25)
        self.assertEqual(data.PLANTS["prism_bloom"]["mature_bonus"], 30)
        self.assertTrue(data.PLANTS["maneater_tomato"]["consume"])
        self.assertEqual(data.PLANTS["maneater_tomato"]["feed"], 2)
        self.assertEqual(data.PLANTS["snap_aloe"]["feed"], 2)
        self.assertTrue(set(data.PLANTS["desert_bloom"]["tags"]) >= {"desert", "fruit", "flower"})
        self.assertTrue(data.PLANTS["eclipse_sovereign"]["exact_parents"])
        # Crossbreed seeds can actually be planted somewhere legal.
        run = make_run("eclipse")
        self.assertTrue(run.can_plant("eclipse_bloom", cellar=False))
        self.assertTrue(run.can_plant("eclipse_bloom", cellar=True))
        self.assertTrue(run.can_plant("ghost_bloom", cellar=True))


class CrossbreedHarvestTests(unittest.TestCase):
    def harvest_with(self, run, cid, at=0, cellar=False):
        with mock.patch.dict(data.PLANTS[cid], {"chance": 1.0}):
            board = run.cellar_plots if cellar else run.plots
            board[at].progress = data.PLANTS[board[at].species]["grow"]
            return run.harvest(at, cellar=cellar)

    def test_flagship_needs_eclipse_and_adjacency(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower")
        self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        self.assertEqual(run.seeds.get("eclipse_bloom"), 1)
        self.assertIn("eclipse_bloom", run.discovered_crossbreeds)
        kinds = [ev["kind"] for ev in run.events]
        self.assertIn("crossbreed", kinds)

    def test_no_eclipse_no_flagship(self):
        run = make_run("none")
        plant_pair(run, "sunflower", "moonflower")
        with mock.patch.dict(data.PLANTS["eclipse_bloom"], {"chance": 1.0}):
            self.assertTrue(run.harvest(0))
        self.assertNotIn("eclipse_bloom", run.seeds)

    def test_diagonal_and_distant_parents_do_not_cross(self):
        for b_at in (5, 3):  # diagonal to plot 0, and two plots away
            run = make_run("eclipse")
            plant_pair(run, "sunflower", "moonflower", b_at=b_at)
            with mock.patch.dict(data.PLANTS["eclipse_bloom"], {"chance": 1.0}):
                self.assertTrue(run.harvest(0))
            self.assertNotIn("eclipse_bloom", run.seeds, b_at)

    def test_below_and_above_count_as_adjacent(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower", b_at=4)  # directly below
        self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        self.assertEqual(run.seeds.get("eclipse_bloom"), 1)

    def test_cellar_plot_directly_below_counts(self):
        # The Ghost Bloom route: Pumpkin on the surface, Moonflower in the
        # cellar plot directly below it, in Autumn with no eclipse at all.
        run = make_run("none", round_no=19)
        self.assertEqual(run.season_name(), "Autumn")
        plant_pair(run, "pumpkin", "moonflower", a_at=1, b_at=1, cellar_b=True)
        self.assertTrue(self.harvest_with(run, "ghost_bloom", at=1))
        self.assertEqual(run.seeds.get("ghost_bloom"), 1)

    def test_ghost_bloom_needs_autumn(self):
        run = make_run("none", round_no=1)  # Spring
        plant_pair(run, "pumpkin", "moonflower", a_at=1, b_at=1, cellar_b=True)
        with mock.patch.dict(data.PLANTS["ghost_bloom"], {"chance": 1.0}):
            self.assertTrue(run.harvest(1))
        self.assertNotIn("ghost_bloom", run.seeds)

    def test_weather_recipes(self):
        cases = [
            ("rainbow_daisy", "daisy", "four_leaf_clover", "rain", 1),
            ("solar_saffron", "saffron", "sunflower", "sunny", 1),
            ("spiny_pumpkin", "cactus", "pumpkin", "drought", 1),
            ("spiny_pumpkin", "cactus", "pumpkin", "heatwave", 1),
            ("frost_tomato", "tomato", "cranberries", "frost", 1),
            ("maneater_tomato", "venus_flytrap", "tomato", "none", 1),
            ("lucky_orchid", "four_leaf_clover", "orchid", "none", 1),
            ("prism_bloom", "crystal_bloom", "orchid", "none", 1),
            ("snap_aloe", "aloe_vera", "venus_flytrap", "none", 1),
            ("desert_bloom", "prickly_pear", "agave", "none", 1),
        ]
        for cid, a, b, twist, rnd in cases:
            with self.subTest(crossbreed=cid, twist=twist):
                run = make_run(twist, round_no=rnd)
                plant_pair(run, a, b)
                self.assertTrue(self.harvest_with(run, cid))
                self.assertEqual(run.seeds.get(cid), 1)

    def test_sovereign_needs_the_exact_mutants(self):
        # Ordinary parents under an eclipse make the lesser Eclipse Bloom.
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower")
        self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        self.assertNotIn("eclipse_sovereign", run.seeds)
        # The crowned pair makes the Sovereign, never the lesser child.
        run = make_run("eclipse")
        plant_pair(run, "sunflower_gold", "moonflower_blood")
        with mock.patch.dict(data.PLANTS["eclipse_sovereign"], {"chance": 1.0}), \
                mock.patch.dict(data.PLANTS["eclipse_bloom"], {"chance": 1.0}):
            self.assertTrue(run.harvest(0))
        self.assertEqual(run.seeds.get("eclipse_sovereign"), 1)
        self.assertNotIn("eclipse_bloom", run.seeds)

    def test_mutant_forms_still_count_as_their_parent(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower_twin", "moonflower")
        self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        self.assertEqual(run.seeds.get("eclipse_bloom"), 1)

    def test_multiple_seeds_can_drop_in_one_round(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower")
        for _ in range(3):
            self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        self.assertEqual(run.seeds.get("eclipse_bloom"), 3)

    def test_zero_chance_never_drops(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower")
        with mock.patch.dict(data.PLANTS["eclipse_bloom"], {"chance": 0.0}):
            self.assertTrue(run.harvest(0))
        self.assertNotIn("eclipse_bloom", run.seeds)

    def test_discovery_survives_a_save_round_trip(self):
        run = make_run("eclipse")
        plant_pair(run, "sunflower", "moonflower")
        self.assertTrue(self.harvest_with(run, "eclipse_bloom"))
        loaded = Run.from_dict(run.to_dict())
        self.assertIn("eclipse_bloom", loaded.discovered_crossbreeds)
        self.assertEqual(loaded.seeds.get("eclipse_bloom"), 1)


class CrossbreedTraitTests(unittest.TestCase):
    def test_solar_saffron_speeds_up_in_sunshine(self):
        run = make_run("sunny")
        self.assertEqual(run._plant_speed_mult("solar_saffron"), 1.25)
        run = make_run("none")
        self.assertEqual(run._plant_speed_mult("solar_saffron"), 1.0)

    def test_spiny_pumpkin_treats_drought_and_heat_as_sun(self):
        for twist, weather_growth in (("drought", 0.65), ("heatwave", 0.85)):
            run = make_run(twist)
            mult = run._plant_speed_mult("spiny_pumpkin")
            self.assertAlmostEqual(mult * weather_growth, 1.25, places=6, msg=twist)
        run = make_run("none")
        self.assertEqual(run._plant_speed_mult("spiny_pumpkin"), 1.0)

    def test_ghost_bloom_speeds_up_in_autumn(self):
        run = make_run("none", round_no=19)
        self.assertEqual(run._plant_speed_mult("ghost_bloom"), 1.25)
        self.assertEqual(run._plant_speed_mult("ghost_bloom", cellar=True), 1.25)
        run = make_run("none", round_no=1)
        self.assertEqual(run._plant_speed_mult("ghost_bloom"), 1.0)

    def test_frost_tomato_is_plantable_in_frost(self):
        run = make_run("frost")
        self.assertTrue(run.can_plant("frost_tomato", cellar=False))
        # ...while an ordinary desert crop is still turned away.
        self.assertFalse(run.can_plant("spiny_pumpkin", cellar=False))

    def test_prism_bloom_rewards_waiting(self):
        run = make_run("none")
        run.plots[0] = Plot("prism_bloom", progress=30.0, mature_time=3.0)
        # $450 base + 3s x $30 mature bonus, before multipliers.
        self.assertGreaterEqual(run.harvest_value(0), 450 + 90)

    def test_maneater_tomato_eats_neighbours_and_critters(self):
        run = make_run("none")
        run.plots[0] = Plot("maneater_tomato", progress=14.0)
        run.plots[1] = Plot("daisy", progress=5.0)
        run.critter_eaten(0, species="ant")
        self.assertEqual(run.plots[0].fed, 3)
        self.assertTrue(run.harvest(0))
        self.assertIsNone(run.plots[1].species)  # the neighbour was eaten

    def test_desert_bloom_feeds_both_pairing_families(self):
        run = make_run("none")
        run.plots[0] = Plot("desert_bloom")
        desert = data.RELIC_SYNERGIES["desert_rose"]
        flower = data.RELIC_SYNERGIES["green_thumb"]
        self.assertEqual(run._synergy_count(desert), 1)
        self.assertEqual(run._synergy_count(flower), 1)


class RarityOrderTests(unittest.TestCase):
    def assert_rarity_sorted(self, ids, table=None):
        self.assertEqual(list(ids), data.sort_by_rarity(list(ids), table))

    def test_catalogues_are_in_rarity_order(self):
        self.assert_rarity_sorted(data.PLANT_ORDER)
        self.assert_rarity_sorted(data.SURFACE_PLANTS)
        self.assert_rarity_sorted(data.CELLAR_PLANTS)
        self.assert_rarity_sorted(data.NOCTURNAL_PLANTS)
        self.assert_rarity_sorted(data.FARMER_PLANTS)
        self.assert_rarity_sorted(data.DESERT_PLANTS)
        self.assert_rarity_sorted(data.CROSSBREED_ORDER)
        self.assert_rarity_sorted(data.RELIC_ORDER, data.RELICS)
        for pack in data.PACKS.values():
            self.assert_rarity_sorted(list(pack["pool"]))

    def test_index_categories_are_in_rarity_order(self):
        from .index import _category_ids

        for cat in ("garden", "desert", "farmer", "night", "crossbreed"):
            ids = _category_ids(cat)
            table = {sid: data.PLANTS[sid] for sid in ids}
            self.assertEqual(ids, data.sort_by_rarity(ids, table), cat)
        # ALL is the rarity-ordered plant catalogue followed by the mutants,
        # themselves ordered by their base plant's rarity.
        everything = _category_ids("all")
        self.assertEqual(everything[:len(data.PLANT_ORDER)], data.PLANT_ORDER)
        self.assertEqual(everything[len(data.PLANT_ORDER):], data.sort_mutants(list(data.MUTANTS)))
        self.assertEqual(_category_ids("crossbreed"), data.CROSSBREED_ORDER)
        self.assertEqual(_category_ids("mutant"), data.sort_mutants(list(data.MUTANTS)))
        everything = _category_ids("all")
        for cid in data.CROSSBREEDS:
            self.assertIn(cid, everything)


class CrossbreedSpriteTests(unittest.TestCase):
    def test_each_crossbreed_has_its_own_finished_sprite(self):
        import pygame

        from . import gfx
        from .sprites_data import GRIDS, PALETTE

        pygame.init()
        pygame.display.set_mode((1, 1))
        unknown = pygame.image.tobytes(gfx.sprite("unknown"), "RGBA")
        seen = set()
        for cid, (a, b, _c, _g, _y) in EXPECTED.items():
            with self.subTest(crossbreed=cid):
                self.assertIn(cid, GRIDS)
                rows = GRIDS[cid]
                self.assertEqual(len(rows), 12)
                self.assertTrue(all(len(row) == 12 for row in rows))
                self.assertTrue(set("".join(rows)) <= set(PALETTE) | {"."})
                blob = pygame.image.tobytes(gfx.sprite(cid), "RGBA")
                self.assertNotEqual(blob, unknown)
                self.assertNotIn(blob, seen)  # no two crossbreeds share art
                seen.add(blob)
                # New art, not a recolour: the silhouette itself differs
                # from both parents (mutant parents compare by base art).
                for parent in (a, b):
                    base_art = data.PLANTS[parent].get("art", data.PLANTS[parent].get("base", parent))
                    self.assertNotEqual(rows, GRIDS[base_art], parent)


class CrossbreedIndexTests(unittest.TestCase):
    def make_scene(self, discovered=()):
        from .index import IndexScene

        class AppStub:
            profile = {"perks": {}, "harvested": {}, "heirlooms": 0,
                       "discovered_crossbreeds": list(discovered)}
            run = None
            mouse = (-1, -1)

            def goto(self, _name):
                pass

        scene = IndexScene(AppStub())
        scene.on_enter()
        return scene

    def test_undiscovered_crossbreeds_are_question_marks_with_hints(self):
        scene = self.make_scene()
        scene.set_subsection("crossbreed")
        self.assertEqual(scene.entries(), data.CROSSBREED_ORDER)
        for cid in data.CROSSBREED_ORDER:
            self.assertTrue(scene.is_undiscovered(cid), cid)
            name, _art, _subs, _col, _badge = scene._card_meta(cid)
            self.assertEqual(name, "???")
        # The detail pane renders the hint without naming the plant.
        import pygame

        pygame.init()
        pygame.display.set_mode((1, 1))
        surf = pygame.Surface((320, 180))
        scene.selected = "eclipse_bloom"
        scene.draw(surf)

    def test_discovered_crossbreeds_show_their_recipe(self):
        scene = self.make_scene(discovered=list(data.CROSSBREEDS))
        for cid in data.CROSSBREED_ORDER:
            self.assertFalse(scene.is_undiscovered(cid), cid)
        name, _art, _subs, _col, _badge = scene._card_meta("eclipse_bloom")
        self.assertEqual(name, "Eclipse Bloom")
        recipe = data.crossbreed_recipe_text(data.PLANTS["eclipse_bloom"])
        self.assertIn("Sunflower", recipe)
        self.assertIn("Moonflower", recipe)
        self.assertIn("ECLIPSE", recipe)


class CrossbreedPauseIndexTests(unittest.TestCase):
    def test_pause_menu_opens_index_and_back_restores_the_round(self):
        import os
        import tempfile
        from unittest.mock import patch

        import pygame

        from .app import App
        from .round import plot_rect

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            app.new_run()
            app.run.seeds["daisy"] = 2
            app.goto("round")
            round_scene = app.scene
            px, py, pw, ph = plot_rect(0)
            app.handle_click((px + pw // 2, py + ph // 2))
            self.assertEqual(app.run.plots[0].species, "daisy")

            app.open_pause()
            self.assertIsNotNone(app.pause_modal)
            button = app.pause_modal.index_btn
            app.handle_click((button.x + button.w // 2, button.y + button.h // 2))
            self.assertEqual(app.scene_name, "index")
            self.assertIsNone(app.pause_modal)
            app.scene.set_subsection("crossbreed")
            self.assertEqual(app.scene.entries(), data.CROSSBREED_ORDER)
            app.scene.draw(app.canvas)

            # Back returns to the very same round, paused, plants intact.
            app.handle_key(pygame.K_ESCAPE)
            self.assertEqual(app.scene_name, "round")
            self.assertIs(app.scene, round_scene)
            self.assertIsNotNone(app.pause_modal)
            self.assertEqual(app.run.plots[0].species, "daisy")
            app.pause_modal.resume()
            self.assertIsNone(app.pause_modal)

    def test_packs_shelf_hides_mystery_seeds_until_discovery(self):
        import os
        import tempfile
        from unittest.mock import patch

        from .app import App

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            app = App()
            app.new_run()
            self.assertEqual(app.scene_name, "packs")
            self.assertNotIn("eclipse_bloom", app.scene.shelf_order())
            app.discover_crossbreed("eclipse_bloom")
            self.assertIn("eclipse_bloom", app.scene.shelf_order())
            self.assertIn("eclipse_bloom", app.profile["discovered_crossbreeds"])
            # And the shelf itself is in rarity order.
            order = app.scene.shelf_order()
            self.assertEqual(order, data.sort_by_rarity(order))


if __name__ == "__main__":
    unittest.main()
