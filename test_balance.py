import unittest

from .state import Run, Plot
from . import data


class EconomyTests(unittest.TestCase):
    def test_auto_water_drains_and_restarts(self):
        run = Run(seed=1)
        run.relics = ["gardener"]
        run.plots = [Plot("daisy")]
        run.phase = "round"
        run.started = True
        run.time_total = run.round_time()
        run.time_left = run.time_total
        run.update(0.2)
        self.assertGreaterEqual(run.plots[0].progress, 0)
        self.assertGreaterEqual(run.plots[0].water_left, 0)
        self.assertLess(run.plots[0].water_left, run.water_time() + 0.01)

    def test_relic_sale_refunds_money_and_removes_relic(self):
        run = Run(seed=1)
        run.relics = ["clover"]
        before = run.money
        ok, _, refund = run.sell_relic(0)
        self.assertTrue(ok)
        self.assertEqual(run.relics, [])
        self.assertEqual(run.money, before + refund)
        self.assertGreater(refund, 0)

    def test_plot_price_rises_faster(self):
        run = Run(seed=1)
        first = run.plot_price()
        run.plots_bought = 1
        second = run.plot_price()
        self.assertGreater(first, 0)
        self.assertGreater(second, first * 1.7)

    def test_bill_requires_explicit_choice(self):
        run = Run(seed=1)
        run.round = 3
        run.money = run.bill_for_round(3)
        run.begin_round()
        run.update(0)
        summary = run.end_round()
        self.assertTrue(summary["pending_bill"])
        self.assertIsNone(summary["paid"])
        self.assertGreater(run.pending_bill, 0)
        ok, _ = run.pay_pending_bill()
        self.assertTrue(ok)
        self.assertEqual(run.pending_bill, 0)

    def test_declining_bill_ends_run(self):
        run = Run(seed=1)
        run.round = 3
        run.money = run.bill_for_round(3)
        run.end_round()
        run.decline_bill()
        self.assertTrue(run.dead)

    def test_rare_relic_costs_more_than_common(self):
        run = Run(seed=1)
        common = run.relic_price("green_thumb")
        rare = run.relic_price("gardener")
        self.assertGreater(rare, common)

    def test_late_game_prices_scale_far_above_round_one(self):
        run = Run(seed=1)
        round_one_garden = run.pack_price("garden")
        round_one_plot = run.plot_price()

        run.round = 12
        run.plots_bought = 8
        run.rerolls = 2
        late_garden = run.pack_price("garden")
        late_plot = run.plot_price()
        late_relic = run.relic_price("gardener")
        late_reroll = run.reroll_price()

        self.assertGreater(late_garden, round_one_garden * 100)
        self.assertGreater(late_plot, round_one_plot * 1000)
        self.assertGreater(late_relic, 1000)
        self.assertGreater(late_reroll, 1000)

    def test_late_rounds_have_less_time(self):
        run = Run(seed=1)
        round_three = run.round_time()
        run.round = 8
        round_eight = run.round_time()
        self.assertGreater(round_three, round_eight)

    def test_quotas_climb_faster_after_round_three(self):
        run = Run(seed=1)
        first = run.bill_for_round(3)
        second = run.bill_for_round(6)
        third = run.bill_for_round(9)
        self.assertGreater(first, 0)
        self.assertGreater(second, first * 4)
        self.assertGreater(third, second * 4)


class MechanicTests(unittest.TestCase):
    def test_boss_round_every_nine(self):
        run = Run(seed=1)
        self.assertFalse(run.is_boss_round(8))
        self.assertTrue(run.is_boss_round(9))
        self.assertTrue(run.is_boss_round(18))
        self.assertEqual(run.twist_id(9), "crow_swarm")
        self.assertTrue(run.twist(9).get("boss"))
        self.assertTrue(run.twist(9).get("crow"))

    def test_positive_and_neutral_weather_exist(self):
        for tid in ("sunny", "rain", "market", "eclipse", "still"):
            self.assertIn(tid, data.TWISTS)
        self.assertGreater(data.TWISTS["sunny"]["growth"], 1.0)
        self.assertGreater(data.TWISTS["market"]["yield"], 1.0)
        self.assertTrue(data.TWISTS["eclipse"].get("eclipse"))

    def test_cellar_planting_rules(self):
        run = Run(seed=1)
        run.begin_round()
        run.cellar_unlocked = True
        run.seeds = {"sunflower": 1, "brown_mushroom": 1}
        self.assertFalse(run.plant(0, "sunflower", cellar=True))       # needs sunlight
        self.assertTrue(run.plant(0, "brown_mushroom", cellar=True))
        self.assertFalse(run.plant(1, "brown_mushroom", cellar=False))  # surface needs dark
        self.assertFalse(run.can_water(0, cellar=True))                 # cellar self-waters

    def test_eclipse_allows_nocturnal_on_surface(self):
        run = Run(seed=1)
        run.begin_round()
        run.twist_id = lambda _rnd=None: "eclipse"
        run.seeds = {"brown_mushroom": 2}
        self.assertTrue(run.can_plant("brown_mushroom", cellar=False))
        self.assertTrue(run.plant(0, "brown_mushroom", cellar=False))

    def test_relic_levels_up_and_merges_effects(self):
        run = Run(seed=1)
        run.relics = ["spore_lantern"]
        self.assertEqual(run.relic_level("spore_lantern"), 0)
        self.assertEqual(run._sum("growth"), 0)
        run.counters["mushroom"] = 100
        self.assertEqual(run.relic_level("spore_lantern"), 1)
        self.assertAlmostEqual(run._sum("growth"), 0.25)
        run.counters["mushroom"] = 300
        self.assertEqual(run.relic_level("spore_lantern"), 2)
        self.assertAlmostEqual(run._sum("growth"), 0.25)   # level 2 adds yield, not growth

    def test_spore_lantern_boosts_mushrooms_only(self):
        run = Run(seed=1)
        run.relics = ["spore_lantern"]
        run.twist_id = lambda _rnd=None: "none"          # pin the weather
        run.plots = [Plot("daisy")]
        run.cellar_plots = [Plot("brown_mushroom")]
        daisy = run.harvest_value(0)
        shroom = run.harvest_value(0, cellar=True)
        self.assertEqual(daisy, data.PLANTS["daisy"]["yield"])
        self.assertEqual(shroom, data.PLANTS["brown_mushroom"]["yield"] * 2)

    def test_cursed_upkeep_drains_money(self):
        run = Run(seed=1)
        run.begin_round()
        run.plots[0] = Plot("devil_ivy", progress=6.0)
        run.money = 100
        summary = run.end_round()
        self.assertEqual(summary["upkeep"], data.PLANTS["devil_ivy"]["upkeep"])
        self.assertEqual(run.money, 100 + summary["sale"] - summary["upkeep"])

    def test_widow_bloom_aura_halves_others(self):
        run = Run(seed=1)
        run.plots = [Plot("widow_bloom"), Plot("daisy")]
        with_widow = run.harvest_value(1)
        run.plots = [Plot("daisy"), Plot("daisy")]
        without = run.harvest_value(1)
        self.assertEqual(without, data.PLANTS["daisy"]["yield"])
        self.assertEqual(with_widow * 2, without)

    def test_rare_pack_luck_boosts_rarity(self):
        run = Run(seed=1)
        run.round = 4
        rare_hits = sum(1 for _ in range(3000)
                        if data.PLANTS[run.draw_seed("rare")]["rarity"] in ("rare", "legendary"))
        normal_hits = sum(1 for _ in range(3000)
                          if data.PLANTS[run.draw_seed("harvest")]["rarity"] in ("rare", "legendary"))
        self.assertGreater(rare_hits / 3000, normal_hits / 3000 * 2)

    def test_crow_eats_surface_not_cellar(self):
        run = Run(seed=1)
        run.relics = []
        run.round = 9                    # boss round: crow swarm
        run.begin_round()
        run.started = True
        run.time_total = run.round_time()
        run.time_left = run.time_total
        run.plots[0] = Plot("daisy")
        run.cellar_plots[0] = Plot("brown_mushroom")
        for _ in range(30):
            run.update(1.0)              # 30s: crows fire every 10s
        self.assertIsNone(run.plots[0].species)
        self.assertIsNotNone(run.cellar_plots[0].species)

    def test_cellar_grows_without_water(self):
        run = Run(seed=1)
        run.begin_round()
        run.started = True
        run.time_total = run.round_time()
        run.time_left = run.time_total
        run.cellar_plots[0] = Plot("brown_mushroom")
        for _ in range(80):
            run.update(0.1)
        self.assertGreater(run.money, 0)     # it harvested on its own


class HeirloomTests(unittest.TestCase):
    def test_heirloom_rewards_scale_with_progress(self):
        run = Run(seed=1)
        run.round = 1
        early = run.heirloom_reward()
        run.round = 10
        run.quotas_paid = 3
        late = run.heirloom_reward()
        self.assertEqual(early, 0)
        self.assertGreater(late, early)
        run.won = True
        self.assertGreater(run.heirloom_reward(), late)      # winning pays a jackpot

    def test_heirloom_prices_climb_with_each_level(self):
        costs = [data.perk_cost("cash", level) for level in range(data.PERKS["cash"]["max"])]
        self.assertEqual(costs, sorted(costs))
        self.assertEqual(len(set(costs)), len(costs))
        self.assertEqual(data.perk_cost("cash", data.PERKS["cash"]["max"]), 0)

    def test_buying_an_heirloom_level(self):
        run = Run(seed=1)
        cost = run.heirloom_cost("yield")
        ok, _, paid = run.buy_heirloom("yield", cost)
        self.assertTrue(ok)
        self.assertEqual(paid, cost)
        self.assertEqual(run.perk("yield"), 1)
        self.assertEqual(run.heirlooms_spent, cost)
        # the next level costs more than the one just bought
        self.assertGreater(run.heirloom_cost("yield"), cost)

    def test_cannot_buy_an_heirloom_without_enough(self):
        run = Run(seed=1)
        cost = run.heirloom_cost("plots")
        ok, _, _ = run.buy_heirloom("plots", cost - 1)
        self.assertFalse(ok)
        self.assertEqual(run.perk("plots"), 0)

    def test_heirloom_levels_apply_to_the_run_immediately(self):
        run = Run(seed=1)
        before_money = run.money
        run.buy_heirloom("cash", run.heirloom_cost("cash"))
        self.assertEqual(run.money, before_money + 10)
        plots_before = len(run.plots)
        run.buy_heirloom("plots", run.heirloom_cost("plots"))
        self.assertEqual(len(run.plots), plots_before + 1)

    def test_heirlooms_spent_survive_a_save_and_load(self):
        run = Run(seed=1)
        run.buy_heirloom("packs", run.heirloom_cost("packs"))
        again = Run.from_dict(run.to_dict())
        self.assertEqual(again.perk("packs"), 1)
        self.assertEqual(again.heirlooms_spent, run.heirlooms_spent)


class PriceTests(unittest.TestCase):
    def test_relics_are_dearer_than_they_used_to_be(self):
        run = Run(seed=1)
        # relic base costs used to be 8 / 165 / 320; they are 45 / 165 / 320 now
        # and, more importantly, they double every round instead of 1.8x
        self.assertGreaterEqual(run.relic_price("green_thumb"), 45)
        run.round = 3
        self.assertGreater(run.relic_price("green_thumb"), 150)

    def test_relic_prices_grow_faster_than_seed_prices(self):
        run = Run(seed=1)
        early = run.relic_price("scarecrow")
        run.round = 6
        late = run.relic_price("scarecrow")
        from .settings import PRICE_GROWTH, RELIC_PRICE_GROWTH
        self.assertGreater(RELIC_PRICE_GROWTH, PRICE_GROWTH)
        self.assertGreater(late, early * RELIC_PRICE_GROWTH ** 4)

    def test_each_plot_costs_more_than_the_last(self):
        from .settings import PLOT_PRICE_GROWTH
        self.assertGreaterEqual(PLOT_PRICE_GROWTH, 3.0)
        run = Run(seed=1)
        prices = []
        for bought in range(6):
            run.plots_bought = bought
            prices.append(run.plot_price())
        self.assertEqual(prices, sorted(prices))
        for first, second in zip(prices, prices[1:]):
            self.assertAlmostEqual(second / first, PLOT_PRICE_GROWTH, places=1)


if __name__ == "__main__":
    unittest.main()