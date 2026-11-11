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
