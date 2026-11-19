"""The whole-game suite: economy and price ladders, mechanics and hazards, Moss's
dialogue, sprite art, and screen layout. Every class owns one contract, and most
of them are written as promises a player can feel rather than as maths checks:
a hazard has to be answerable, a beat has to play once, a card has to fit.
"""

import os
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

import pygame

from .state import Run, Plot
from . import data, tutorial
from .settings import (
    APHID_SALE, APHID_YIELD, CONTAGION_CHANCE, DISEASE_GROWTH, DISEASE_SALE, DISEASE_YIELD,
    METEOR_BONUS, METEOR_DESTROY, WEED_FEE, WEED_PERIOD,
)
from .sprites_data import FONT
from .tutorial import PREMISE_KEY, guide_steps


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

        self.assertGreater(late_garden, round_one_garden * 50)
        self.assertGreater(late_plot, round_one_plot * 1000)
        self.assertGreater(late_relic, 1000)
        self.assertGreater(late_reroll, 1000)

    def test_late_rounds_have_less_time(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        self.assertEqual(run.round_time(), 45)
        run.round = 8
        self.assertEqual(run.round_time(), 35)
        run.round = 30
        self.assertEqual(run.round_time(), 30)

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

    def test_boss_rounds_rotate_through_a_roster(self):
        """Nine isn't the only disaster any more: each boss round in a run is
        a different boss, and they all come back round again."""
        self.assertGreater(len(data.BOSS_TWISTS), 3)
        self.assertEqual(len(set(data.BOSS_TWISTS)), len(data.BOSS_TWISTS))
        run = Run(seed=1)
        seen = [run.twist_id(9 * (k + 1)) for k in range(len(data.BOSS_TWISTS))]
        self.assertEqual(seen, data.BOSS_TWISTS)
        self.assertEqual(run.twist_id(9 * (len(data.BOSS_TWISTS) + 1)), data.BOSS_TWISTS[0])
        for tid in data.BOSS_TWISTS:
            with self.subTest(boss=tid):
                boss = data.TWISTS[tid]
                self.assertTrue(boss.get("boss"))
                self.assertEqual(boss.get("tone"), "bad")
                self.assertTrue(boss.get("short"))

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
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot("widow_bloom"), Plot("daisy")]
        with_widow = run.harvest_value(1)
        run.plots = [Plot("daisy"), Plot("daisy")]
        without = run.harvest_value(1)
        self.assertEqual(without, data.PLANTS["daisy"]["yield"])
        self.assertEqual(with_widow * 2, without)

    def test_rare_pack_luck_boosts_rarity(self):
        # Garden is the mostly-common baseline; the Rare Pack's 2.5x luck
        # has to more than double its rate of rare or better seeds.
        run = Run(seed=1)
        run.round = 4
        rare_hits = sum(1 for _ in range(3000)
                        if data.PLANTS[run.draw_seed("rare")]["rarity"] in ("rare", "legendary"))
        normal_hits = sum(1 for _ in range(3000)
                          if data.PLANTS[run.draw_seed("garden")]["rarity"] in ("rare", "legendary"))
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

    def test_relic_effects_change_the_numbers(self):
        capsule = Run(seed=1)
        capsule.relics = ["time_capsule"]
        capsule.phase = "round"
        capsule.capsule_income = 100
        before = capsule.money
        capsule._tick_capsule(10)
        self.assertEqual(capsule.money - before, 25)

        def sale(relics):
            run = Run(seed=1)
            run.twist_id = lambda _rnd=None: "none"
            run.relics = list(relics)
            run.round = 1
            run.plots = [Plot("daisy", progress=data.PLANTS["daisy"]["grow"])] \
                + [Plot() for _ in range(11)]
            run.cellar_plots = [Plot() for _ in range(4)]
            run.stock_species = "daisy"
            run.money = 0
            return run.end_round()["sale"]

        self.assertEqual(sale(["stock_market"]), 2 * sale([]))

        collector = Run(seed=1)
        collector.relics = ["collector"]
        collector.plots = [Plot(species) for species in
                           ("daisy", "tomato", "sunflower", "cactus", "pumpkin")] \
            + [Plot() for _ in range(7)]
        self.assertGreater(collector.relic_power(), 1.0)

        def bad_weather_growth(relics):
            run = Run(seed=1)
            run.twist_id = lambda _rnd=None: "drought"
            run.relics = list(relics)
            return run.growth_speed()

        self.assertGreater(bad_weather_growth(["emergency_generator"]),
                           bad_weather_growth([]))

        owl = Run(seed=1)
        owl.relics = ["friendly_owl"]
        owl.phase = "round"
        owl.seeds = {}
        owl._tick_owl(12)
        self.assertTrue(any(e["kind"] == "owl_seed" for e in owl.events))
        self.assertGreater(sum(owl.seeds.values()), 0)

        snail = Run(seed=1)
        snail.relics = ["eternal_snail"]
        self.assertGreater(snail.growth_speed(), 1.0)
        snail.phase = "round"
        snail.started = True
        self.assertTrue(snail.snail_bite())
        self.assertTrue(snail.snail_bitten)

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
        self.assertAlmostEqual(run.interest_rate(), 0.0)
        run.buy_heirloom("cash", run.heirloom_cost("cash"))
        self.assertEqual(run.money, before_money)
        self.assertAlmostEqual(run.interest_rate(), 0.02)
        plots_before = len(run.plots)
        run.buy_heirloom("plots", run.heirloom_cost("plots"))
        self.assertEqual(len(run.plots), plots_before + 1)

    def test_heirlooms_spent_survive_a_save_and_load(self):
        run = Run(seed=1)
        run.buy_heirloom("packs", run.heirloom_cost("packs"))
        again = Run.from_dict(run.to_dict())
        self.assertEqual(again.perk("packs"), 1)
        self.assertEqual(again.heirlooms_spent, run.heirlooms_spent)

    def test_heirlooms_apply_to_a_run(self):
        clock = Run(seed=1, perks={"clock": 2})
        clock.twist_id = lambda _rnd=None: "none"
        clock.plots[0] = Plot("daisy")
        clock.start_timer()
        self.assertGreater(clock.plots[0].progress, 0)

        penny = Run(seed=1, perks={"penny": 3})
        penny.last_summary = {"paid": True}
        penny.shop_offers = ["green_thumb", "beehive", "clover"]
        with patch.object(penny.rng, "random", return_value=0.0):
            penny._roll_free_offer()
        self.assertIsNotNone(penny.free_offer)
        self.assertEqual(penny.relic_offer_price(penny.free_offer), 0)

        insurance = Run(seed=1, perks={"insurance": 1})
        insurance.round = 3
        insurance.money = 50
        summary = insurance.end_round()
        self.assertTrue(summary["can_afford"])
        ok, _msg = insurance.pay_pending_bill()
        self.assertTrue(ok)
        self.assertTrue(summary["waived"])
        self.assertEqual(insurance.bill_waivers, 0)

class PriceTests(unittest.TestCase):
    def test_relics_are_dearer_than_they_used_to_be(self):
        run = Run(seed=1)
        # relic base costs used to be 8 / 165 / 320; they are 45 / 165 / 320 now
        # and, more importantly, they double every round instead of 1.8x
        self.assertGreaterEqual(run.relic_price("green_thumb"), 45)
        run.round = 3
        self.assertGreater(run.relic_price("green_thumb"), 150)

    def test_relics_stay_buyable_deeper_into_a_run(self):
        """Relics used to double every round, which priced them out of the
        game by round 9 (a common relic cost 20x a round's income). They still
        have to climb hard, just slower than the bill ladder (~1.71x a round)."""
        from .settings import PRICE_GROWTH, RELIC_PRICE_GROWTH
        self.assertLess(RELIC_PRICE_GROWTH, 1.71)
        self.assertLess(RELIC_PRICE_GROWTH, PRICE_GROWTH)      # the cheaper tier now
        self.assertLess(PRICE_GROWTH, 1.71)
        run = Run(seed=1)
        early = run.relic_price("scarecrow")
        run.round = 9
        late = run.relic_price("scarecrow")
        self.assertGreater(late, early * 5)                    # prices still bite
        self.assertLessEqual(late, early * RELIC_PRICE_GROWTH ** 9)

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


class SeasonTests(unittest.TestCase):
    def test_a_new_season_starts_every_nine_rounds(self):
        from .settings import SEASON_LENGTH
        self.assertEqual(SEASON_LENGTH, 9)
        starts = [r for r in range(1, 46) if data.is_new_season(r)]
        self.assertEqual(starts, [1, 10, 19, 28, 37])

    def test_seasons_cycle_and_wrap_forever(self):
        self.assertEqual(data.season(1)["name"], "Spring")
        self.assertEqual(data.season(10)["name"], "Summer")
        self.assertEqual(data.season(19)["name"], "Autumn")
        self.assertEqual(data.season(28)["name"], "Winter")
        self.assertEqual(data.season(37)["name"], "Spring")    # wraps
        for rnd in (1, 10, 19, 28):
            self.assertEqual(data.season(rnd + 36)["name"], data.season(rnd)["name"])

    def test_season_number_counts_up_one_per_season(self):
        self.assertEqual(data.season_number(1), 1)
        self.assertEqual(data.season_number(9), 1)
        self.assertEqual(data.season_number(10), 2)
        self.assertEqual(data.season_number(28), 4)
        for rnd in range(1, 60):
            season = data.season(rnd)
            self.assertIn(season["short"], ("SPR", "SUM", "AUT", "WIN"))
            self.assertTrue(season["name"])

    def test_a_run_knows_its_season(self):
        run = Run(seed=1)
        run.round = 19
        self.assertEqual(run.season_name(), "Autumn")
        self.assertEqual(run.season_number(), 3)
        self.assertEqual(run.season(1)["name"], "Spring")


class FarmerPackTests(unittest.TestCase):
    CROPS = ["potato", "wheat", "corn", "carrot", "cranberries", "saffron"]

    def test_every_crop_is_fully_wired_up(self):
        for sid in self.CROPS:
            with self.subTest(crop=sid):
                plant = data.PLANTS[sid]
                self.assertGreater(plant["grow"], 0)
                self.assertGreater(plant["yield"], 0)
                self.assertGreaterEqual(plant["sell"], plant["yield"])
                self.assertTrue(plant["tags"])
                self.assertIn(plant["rarity"], data.RARITY_COLORS)
                self.assertIn(sid, data.SURFACE_PLANTS)      # plantable up top
                self.assertIn(sid, data.PLANT_ORDER)         # shown on the shelf
                self.assertIn(sid, data.PACKS["farmer"]["pool"])
                self.assertTrue(data.mutants_for(sid))

    def test_the_farmer_pack_opens(self):
        run = Run(seed=4)
        run.round = 2
        self.assertIn("farmer", run.unlocked_packs())
        self.assertIn("farmer", data.PACK_ORDER)
        self.assertGreater(data.free_pack_weight("farmer", 2), 0)
        self.assertEqual(data.free_pack_weight("farmer", 1), 0)   # locked at r1
        run.money = 10000
        self.assertTrue(run.buy_pack("farmer"))
        kind, seeds = run.open_pack()
        self.assertEqual(kind, "farmer")
        for sid in seeds:
            self.assertIn(sid, self.CROPS)

    def test_every_crop_can_be_drawn_and_planted(self):
        run = Run(seed=4)
        run.begin_round()
        run.plots = [Plot() for _ in range(len(self.CROPS))]
        run.seeds = {sid: 1 for sid in self.CROPS}
        for i, sid in enumerate(self.CROPS):
            with self.subTest(crop=sid):
                self.assertTrue(run.can_plant(sid))
                self.assertTrue(run.plant(i, sid))
                self.assertEqual(run.plots[i].species, sid)
                self.assertGreater(run.harvest_value(i), 0)
                self.assertGreater(run.draw_seed("farmer") and 1, 0)

    def test_all_farmer_crops_have_dedicated_sprites(self):
        import pygame
        from . import gfx
        from .sprites_data import GRIDS
        pygame.init()
        pygame.display.set_mode((1, 1))
        unknown_bytes = pygame.image.tobytes(gfx.sprite("unknown"), "RGBA")
        for sid in self.CROPS:
            self.assertIn(sid, GRIDS, "%s has no sprite" % sid)
            surf = gfx.sprite(sid)
            self.assertEqual(surf.get_size(), (12, 12))
            self.assertNotEqual(pygame.image.tobytes(surf, "RGBA"), unknown_bytes)

    def test_missing_sprites_fall_back_to_placeholder_art(self):
        import pygame
        from . import gfx
        pygame.init()
        pygame.display.set_mode((1, 1))
        fallback = gfx.sprite("missing_sprite_id")
        self.assertEqual(fallback.get_size(), (12, 12))
        self.assertEqual(
            pygame.image.tobytes(fallback, "RGBA"),
            pygame.image.tobytes(gfx.sprite("unknown"), "RGBA"),
        )


class MutagenTests(unittest.TestCase):
    def test_seeds_can_sprout_already_mutated(self):
        run = Run(seed=21)
        run.relics = ["mutagen"]
        run.begin_round()
        run.plots = [Plot() for _ in range(2)]
        run.seeds = {"daisy": 5000}
        mutations = 0
        for _ in range(2000):
            run.plots[0] = Plot()
            run.seeds["daisy"] = 1
            run.plant(0, "daisy")
            if run.plots[0].species != "daisy":
                mutations += 1
                self.assertTrue(data.PLANTS[run.plots[0].species].get("mutant"))
        rate = mutations / 2000
        self.assertGreater(rate, 0.18)          # 25% +/- noise
        self.assertLess(rate, 0.32)

    def test_no_relic_means_no_free_mutations(self):
        run = Run(seed=21)
        run.begin_round()
        run.plots = [Plot()]
        run.seeds = {"daisy": 500}
        sprouted = 0
        for _ in range(500):
            run.plots[0] = Plot()
            run.seeds["daisy"] = 1
            run.plant(0, "daisy")
            sprouted += run.plots[0].species != "daisy"
        self.assertEqual(sprouted, 0)

    def test_mutants_are_worth_more_with_the_relic(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot("daisy_shiny")]
        plain = run.harvest_value(0)
        run.relics = ["mutagen"]
        boosted = run.harvest_value(0)
        self.assertGreater(boosted, plain)
        # 1.2x on a big enough number to see it
        run.plots = [Plot("sunflower_gold")]
        run.relics = []
        base = run.harvest_value(0)
        run.relics = ["mutagen"]
        self.assertEqual(run.harvest_value(0), int(base * 1.2 + 0.5))

    def test_mutagen_does_not_touch_plain_plants(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot("daisy")]
        before = run.harvest_value(0)
        run.relics = ["mutagen"]
        self.assertEqual(run.harvest_value(0), before)

    def test_mutagen_levels_up(self):
        run = Run(seed=1)
        run.relics = ["mutagen"]
        self.assertEqual(run.relic_level("mutagen"), 0)
        self.assertAlmostEqual(run._sum("mutate_on_plant"), 0.25)
        run.counters["harvest"] = 200
        self.assertEqual(run.relic_level("mutagen"), 1)
        self.assertAlmostEqual(run._sum("mutate_on_plant"), 0.40)


class TwistTests(unittest.TestCase):
    """Every twist has to actually move a number, not just print a name."""

    def pinned(self, twist, species="daisy", plots=4):
        run = Run(seed=3)
        run.round = 5                       # clear of the quota-1 'none' round
        run.twist_id = lambda _rnd=None, t=twist: t
        run.begin_round()
        run.started = True
        run.plots = [Plot(species) for _ in range(plots)]
        return run

    def test_growth_twists_change_growth(self):
        base = self.pinned("none").growth_speed()
        self.assertGreater(self.pinned("sunny").growth_speed(), base)
        self.assertLess(self.pinned("drought").growth_speed(), base)

    def test_yield_twists_change_harvests(self):
        self.assertGreater(self.pinned("market").harvest_value(0),
                           self.pinned("none").harvest_value(0))
        self.assertLess(self.pinned("locusts").harvest_value(0),
                        self.pinned("none").harvest_value(0))

    def test_market_day_survives_rounding(self):
        """2 x 1.25 rounds to 2 with banker's rounding, which quietly turned
        Market Day into a no-op on every cheap flower."""
        for species in ("daisy", "tomato", "sunflower", "pumpkin"):
            with self.subTest(plant=species):
                plain = self.pinned("none", species).harvest_value(0)
                market = self.pinned("market", species).harvest_value(0)
                self.assertGreater(market, plain)

    def test_short_days_shorten_the_round(self):
        self.assertLess(self.pinned("short").round_time(),
                        self.pinned("none").round_time())

    def test_frost_bans_desert_plants(self):
        run = self.pinned("frost")
        desert = [s for s, p in data.PLANTS.items() if "desert" in p["tags"]]
        self.assertTrue(desert)
        for sid in desert:
            self.assertFalse(run.can_plant(sid))
        self.assertTrue(run.can_plant("daisy"))

    def test_rain_waters_without_being_asked(self):
        run = self.pinned("rain")
        run.update(1.0)
        self.assertGreater(run.plots[0].water_left, 0)
        dry = self.pinned("none")
        dry.update(1.0)
        self.assertEqual(dry.plots[0].water_left, 0)

    def test_eclipse_lets_nocturnal_plants_up_top(self):
        run = self.pinned("eclipse")
        self.assertTrue(run.can_plant("brown_mushroom"))
        dark = self.pinned("none")
        self.assertFalse(dark.can_plant("brown_mushroom"))
        # and it flips the growth rates: night plants love it, sun-lovers don't
        shroom = self.pinned("eclipse", "brown_mushroom")
        flower = self.pinned("eclipse", "daisy")
        shroom.update(1.0)
        flower.update(1.0)
        self.assertGreater(shroom.plots[0].progress, flower.plots[0].progress)

    def test_blight_withers_one_plant_at_half_time(self):
        run = self.pinned("blight")
        run.time_total = run.time_left = 20.0
        for _ in range(12):
            run.update(1.0)
        withered = [e for e in run.events if e["kind"] == "wither"]
        self.assertEqual(len(withered), 1)
        self.assertEqual(sum(1 for p in run.plots if p.species), 3)

    def test_crazy_crows_only_ever_take_one_plant(self):
        """No more doubling up at half time: one plant per visit, all round."""
        twist = data.TWISTS["crow_swarm"]
        self.assertEqual(twist["name"], "Crazy Crows!")
        self.assertLessEqual(twist["crow"], 6)          # meaner than the old 10s
        self.assertFalse(twist.get("crow_ramp"))
        self.assertEqual(twist.get("crow_count", 1), 1)
        run = self.pinned("crow_swarm", plots=12)
        run.time_total = run.time_left = 24.0
        eaten_first_half = eaten_second_half = 0
        for _ in range(12):
            run.update(1.0)
            eaten_first_half += sum(1 for ev in run.events if ev["kind"] == "eaten")
            run.events.clear()
            run.plots = [Plot("daisy") for _ in range(12)]
        for _ in range(12):
            run.update(1.0)
            eaten_second_half += sum(1 for ev in run.events if ev["kind"] == "eaten")
            run.events.clear()
            run.plots = [Plot("daisy") for _ in range(12)]
        self.assertGreater(eaten_first_half, 0)
        self.assertEqual(eaten_first_half, eaten_second_half)

    def test_crows_say_what_they_ate(self):
        run = self.pinned("crow_swarm")
        run.time_total = run.time_left = 30.0
        run.update(6.0)
        eaten = [e for e in run.events if e["kind"] == "eaten"]
        self.assertTrue(eaten)
        self.assertTrue(all(e["name"] for e in eaten))

    def test_every_twist_is_reachable_and_defined(self):
        reachable = set(data.RANDOM_TWISTS) | set(data.MINOR_TWISTS) | \
            set(data.BOSS_TWISTS) | {"none"}
        for tid in data.TWISTS:
            with self.subTest(twist=tid):
                self.assertIn(tid, reachable)
                twist = data.TWISTS[tid]
                self.assertTrue(twist["name"])
                self.assertTrue(twist["desc"])
                self.assertIn(twist.get("tone", "neutral"), ("good", "bad", "neutral"))

    def test_events_know_which_board_they_happened_on(self):
        """Cellar harvests used to pop up over the surface plots."""
        run = Run(seed=2)
        run.auto_harvest = True
        run.begin_round()
        run.started = True
        run.cellar_unlocked = True
        run.plots = [Plot("daisy")]
        run.cellar_plots = [Plot("brown_mushroom")]
        run.time_total = run.time_left = 30.0
        for _ in range(120):
            run.update(0.1)
        harvests = [e for e in run.events if e["kind"] == "harvest"]
        self.assertTrue(harvests)
        self.assertIn(True, [bool(e["cellar"]) for e in harvests])
        self.assertIn(False, [bool(e["cellar"]) for e in harvests])

class BossMechanicTests(unittest.TestCase):
    """The boss roster: every boss has to actually do something to the board."""

    def pinned(self, twist, species="daisy", plots=4):
        run = Run(seed=5)
        run.round = 9
        run.twist_id = lambda _rnd=None, t=twist: t
        run.begin_round()
        run.started = True
        run.plots = [Plot(species) for _ in range(plots)]
        run.time_total = run.time_left = 60.0
        return run

    def test_hailstorm_knocks_growth_back(self):
        run = self.pinned("hailstorm", species="orchid")   # slow enough not to harvest
        for p in run.plots:
            p.progress = 2.0
        run.update(7.0)
        self.assertTrue(any(e["kind"] == "hail" for e in run.events))
        # seven seconds of growth (2 + 7 = 9), then halved by the hail
        self.assertTrue(all(p.progress < 6.0 for p in run.plots))

    def test_root_rot_takes_a_plant(self):
        run = self.pinned("root_rot", plots=4)
        run.update(8.0)
        self.assertEqual(sum(1 for p in run.plots if p.species), 3)
        rot = [e for e in run.events if e["kind"] == "rot"]
        self.assertEqual(len(rot), 1)
        self.assertTrue(rot[0]["name"])

    def test_heatwave_dries_the_soil_twice_as_fast(self):
        hot = self.pinned("heatwave")
        mild = self.pinned("none")
        self.assertTrue(hot.water(0))
        self.assertTrue(mild.water(0))
        hot.update(0.5)
        mild.update(0.5)
        self.assertLess(hot.plots[0].water_left, mild.plots[0].water_left)

    def test_heatwave_slows_growth(self):
        self.assertLess(self.pinned("heatwave").growth_speed(),
                        self.pinned("none").growth_speed())

    def test_gale_shortens_the_round(self):
        self.assertLess(self.pinned("gale").round_time(), self.pinned("none").round_time())

    def test_eternal_night_is_an_eclipse(self):
        run = self.pinned("eternal_night")
        self.assertTrue(run.twist().get("eclipse"))
        self.assertTrue(run.can_plant("brown_mushroom"))

    def test_bosses_leave_the_cellar_alone(self):
        run = self.pinned("root_rot", plots=4)
        run.cellar_unlocked = True
        run.cellar_plots[0] = Plot("brown_mushroom")
        run.update(8.0)
        self.assertIsNotNone(run.cellar_plots[0].species)


class MutationCoverageTests(unittest.TestCase):
    """Every plant family can mutate, and cursed mutations stay cursed."""

    def test_farmer_crops_can_mutate(self):
        for sid in data.FARMER_PLANTS:
            with self.subTest(crop=sid):
                self.assertTrue(data.mutants_for(sid))

    def test_nocturnal_crops_can_mutate(self):
        # Crossbreeds are terminal forms (no_mutations), like Crystal Bloom:
        # every ordinary nocturnal crop still has a mutation to chase.
        for sid in data.NOCTURNAL_PLANTS:
            if data.PLANTS[sid].get("no_mutations"):
                continue
            with self.subTest(crop=sid):
                self.assertTrue(data.mutants_for(sid))

    def test_garden_flowers_have_more_than_one_mutation(self):
        # Two deliberate exceptions: Mycelium never mutates, and the Four-Leaf
        # Clover has exactly one mutation - the Five-Leaf Clover.
        one_mutation = {"four_leaf_clover": ["five_leaf_clover"]}
        garden = [
            sid for sid in data.SURFACE_PLANTS
            if sid not in data.FARMER_PLANTS and sid not in one_mutation
            and not data.PLANTS[sid].get("no_mutations")
        ]
        for sid in garden:
            with self.subTest(plant=sid):
                self.assertGreaterEqual(len(data.mutants_for(sid)), 2)
        self.assertFalse(data.mutants_for("mycelium"))
        for sid, only in one_mutation.items():
            self.assertEqual(data.mutants_for(sid), only)

    def test_cursed_plants_get_special_mutants(self):
        for sid in ("devil_ivy", "widow_bloom"):
            with self.subTest(plant=sid):
                mutants = data.mutants_for(sid)
                self.assertGreaterEqual(len(mutants), 2)
                self.assertTrue(any(data.PLANTS[m].get("upkeep") for m in mutants))
                for mid in mutants:
                    self.assertIn("cursed", data.PLANTS[mid]["tags"])
                    self.assertTrue(data.PLANTS[mid].get("cursed_mutant"))

    def test_every_mutation_is_worth_more_than_its_base(self):
        for mid, mutant in data.MUTANTS.items():
            with self.subTest(mutant=mid):
                base = data.PLANTS[mutant["base"]]
                self.assertIn(mid, data.PLANTS)
                self.assertGreater(data.PLANTS[mid]["yield"], base["yield"])
                self.assertGreater(data.PLANTS[mid]["sell"], base["sell"])
                self.assertEqual(data.PLANTS[mid]["rarity"], "mutant")
                self.assertTrue(data.PLANTS[mid]["subs"])   # it recolours the base art

    def test_cursed_mutants_bill_at_round_end(self):
        run = Run(seed=1)
        run.begin_round()
        mutant = next(m for m in data.mutants_for("devil_ivy") if data.PLANTS[m].get("upkeep"))
        run.plots = [Plot(mutant, progress=99.0)]
        run.money = 1000
        summary = run.end_round()
        self.assertEqual(summary["upkeep"], data.PLANTS[mutant]["upkeep"])
        self.assertGreater(data.PLANTS[mutant]["upkeep"], data.PLANTS["devil_ivy"]["upkeep"])

    def test_a_crop_can_actually_mutate_in_a_round(self):
        for species in ("potato", "brown_mushroom", "devil_ivy"):
            with self.subTest(plant=species):
                run = Run(seed=7)
                run.begin_round()
                run.plots = [Plot(species)]
                evolved = None
                for _ in range(500):
                    run.plots[0].species = species
                    run.plots[0].harvests = data.mutation_threshold(species)
                    run._maybe_mutate(0)
                    if data.PLANTS[run.plots[0].species].get("mutant"):
                        evolved = run.plots[0].species
                        break
                self.assertIsNotNone(evolved)
                self.assertEqual(data.PLANTS[evolved]["base"], species)


class ShelfInteractionTests(unittest.TestCase):
    def app(self):
        from types import SimpleNamespace
        return SimpleNamespace(run=Run(seed=1), mouse=(319, 179),
                               toast=lambda *args: None, save_run=lambda: None)

    def test_clicking_each_paged_seed_selects_the_visible_seed(self):
        from importlib import import_module
        RoundScene = import_module('.round', __package__).RoundScene
        scene = RoundScene(self.app())
        scene.on_enter()
        for sid in data.SURFACE_PLANTS:
            scene.run.seeds[sid] = 3
        for offset in range(scene.max_scroll() + 1):
            scene.tray_scroll = offset
            for i, sid in enumerate(scene.visible_seeds()):
                x, y, w, h = scene.tray_rect(i)
                self.assertTrue(scene.on_click((x + w // 2, y + h // 2)))
                self.assertEqual(scene.selected, sid)

    def test_every_owned_pack_is_reachable_and_has_tooltip(self):
        from .packs import PacksScene, PACKS_PER_PAGE
        scene = PacksScene(self.app())
        scene.on_enter()
        scene.run.packs = list(data.PACK_ORDER) * 5
        scene.refresh()
        seen = []
        for page in range(scene.pack_pages):
            scene.pack_page = page
            for kind, index in scene.visible_packs():
                seen.append(index)
                self.assertTrue(scene.pack_lines(kind, index))
        self.assertEqual(seen, list(range(len(scene.run.packs))))
        scene.run.packs = scene.run.packs[:PACKS_PER_PAGE]
        scene.refresh()
        self.assertEqual(scene.pack_page, 0)
        self.assertFalse(scene.pack_down.enabled)
    # ------------------------------------------------------------------
    # the packs screen: the for-sale shelf used to run off the bottom of the
    # screen underneath the seed shelf, so six of the eight packs could not be
    # bought and the wheel only ever paged the seeds
    # ------------------------------------------------------------------
    def packs_scene(self, round_no=24, money=50_000_000):
        from .packs import PacksScene
        app = self.app()
        app.mouse = (160, 90)
        app.goto = lambda name: None
        app.run = Run(seed=1)
        app.run.round = round_no
        app.run.money = money
        app.run.packs = list(data.PACK_ORDER) * 2
        scene = PacksScene(app)
        scene.on_enter()
        return scene

    def test_for_sale_shelf_stays_on_screen(self):
        from .packs import BUY_BOX, PACKS_BOX, SEED_BOX, GO_BTN
        scene = self.packs_scene()
        boxes = [PACKS_BOX, SEED_BOX, BUY_BOX, GO_BTN]
        for name, r in (("packs", PACKS_BOX), ("seeds", SEED_BOX), ("buy", BUY_BOX)):
            self.assertGreaterEqual(r[0], 0, name)
            self.assertGreaterEqual(r[1], 14, name)          # below the topbar
            self.assertLessEqual(r[0] + r[2], 320, name)
            self.assertLessEqual(r[1] + r[3], 180, name)
        def overlap(a, b):
            return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2]
                    and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                self.assertFalse(overlap(a, b), (a, b))

    def test_every_unlocked_pack_can_be_bought_from_the_shelf(self):
        from .packs import BUYS_PER_PAGE
        scene = self.packs_scene()
        self.assertEqual(scene.buy_pages,
                         (len(scene.run.unlocked_packs()) + BUYS_PER_PAGE - 1) // BUYS_PER_PAGE)
        seen = []
        for page in range(scene.buy_pages):
            scene.buy_page = page
            scene.draw(self._surface())
            seen += [kind for kind, _r in scene.buy_rects]
        self.assertEqual(seen, scene.run.unlocked_packs())
        # and the button under the cursor buys the pack it is labelled with
        scene.buy_page = scene.buy_pages - 1
        scene.draw(self._surface())
        kind, rect = scene.buy_rects[-1]
        before = len(scene.run.packs)
        self.assertTrue(scene.on_click((rect[0] + 2, rect[1] + 2)))
        self.assertEqual(scene.run.packs[-1], kind)
        self.assertEqual(len(scene.run.packs), before + 1)

    def test_a_buy_button_hidden_on_another_page_cannot_be_clicked(self):
        from .packs import BUYS_PER_PAGE
        scene = self.packs_scene()
        scene.buy_page = 0
        scene.draw(self._surface())
        hidden = [b for b in scene.buy_buttons if b.slot // BUYS_PER_PAGE]
        self.assertTrue(hidden)
        before = len(scene.run.packs)
        for b in hidden:
            self.assertFalse(scene.on_click((b.x + 1, b.y + 1)))
        self.assertEqual(len(scene.run.packs), before)

    def test_wheel_pages_the_shelf_under_the_cursor(self):
        scene = self.packs_scene()
        scene.app.mouse = (160, 140)                      # over the for-sale shelf
        scene.on_wheel(-1)                                # wheel down
        self.assertEqual(scene.buy_page, 1)
        self.assertEqual(scene.seed_page, 0)
        scene.on_wheel(1)                                 # wheel up
        self.assertEqual(scene.buy_page, 0)
        scene.app.mouse = (40, 40)                        # over the unopened tray
        scene.on_wheel(-1)
        self.assertEqual(scene.pack_page, 1)
        self.assertEqual(scene.buy_page, 0)
        scene.app.mouse = (160, 90)                       # over neither: the seeds
        scene.on_wheel(-1)
        self.assertEqual(scene.seed_page, 1)
        self.assertEqual(scene.pack_page, 1)

    def test_seed_shelf_stays_inside_its_panel_on_every_page(self):
        from .packs import SEED_BOX
        scene = self.packs_scene()
        for page in range(scene.seed_pages):
            scene.seed_page = page
            for i in range(len(scene.visible_seed_order())):
                x, y, w, h = scene.seed_rect(i)
                self.assertGreaterEqual(x, SEED_BOX[0])
                self.assertLessEqual(x + w, SEED_BOX[0] + SEED_BOX[2])
                self.assertGreaterEqual(y, SEED_BOX[1])
                self.assertLessEqual(y + h, SEED_BOX[1] + SEED_BOX[3])

    def test_seed_panel_is_painted_at_its_own_width(self):
        """The panel must be drawn from SEED_BOX, not from a wider stale
        rectangle - a 268px panel runs straight over the for-sale shelf."""
        from .packs import BUY_BOX, SEED_BOX
        surf = self._surface()
        scene = self.packs_scene()
        scene.draw(surf)
        gap_x = SEED_BOX[0] + SEED_BOX[2] + 2       # the gap between the two panels
        self.assertLess(gap_x, BUY_BOX[0])
        background = (30, 26, 46)
        for y in (SEED_BOX[1] + 4, SEED_BOX[1] + 24, SEED_BOX[1] + 44):
            self.assertEqual(tuple(surf.get_at((gap_x, y)))[:3], background,
                             "the seed panel was painted wider than SEED_BOX")

    def test_pack_name_and_price_are_on_separate_lines(self):
        """A shelf button is two lines: name on top, price underneath. Left to
        the generic reflow, a short label collapses onto one line."""
        from .settings import TEXT
        surf = self._surface()
        scene = self.packs_scene(round_no=2, money=5000)
        scene.run.packs = ["garden"] * 3
        scene.refresh()
        scene.draw(surf)
        x, y, w, h = scene.buy_slot_rect(0)
        ink = TEXT[:3]
        rows = sorted({ry for ry in range(y, y + h) for rx in range(x, x + w)
                       if tuple(surf.get_at((rx, ry)))[:3] == ink})
        self.assertTrue(rows, "no text drawn on the shelf button")
        bands = 1
        for above, below in zip(rows, rows[1:]):
            if below - above > 1:
                bands += 1
        self.assertEqual(bands, 2, "pack name and price should be on separate lines")

    def _surface(self):
        try:
            import pygame
        except ImportError:               # headless checkout without pygame
            self.skipTest("pygame not installed")
        pygame.init()
        return pygame.Surface((320, 180))


class DeepPocketsInterestTests(unittest.TestCase):
    def test_deep_pockets_curve_ends_at_25_percent(self):
        expected = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 25]
        actual = [data.deep_pockets_pct(lv) for lv in range(11)]
        self.assertEqual(actual, expected)
        self.assertEqual(data.perk_text("cash", 1), "+2% INTEREST")
        self.assertEqual(data.perk_text("cash", 9), "+18% INTEREST")
        self.assertEqual(data.perk_text("cash", 10), "+25% INTEREST")

    def test_deep_pockets_stacks_with_piggy_bank_and_pays_interest(self):
        from .settings import START_MONEY
        run = Run(seed=1, perks={"cash": 10})
        self.assertEqual(run.money, START_MONEY)  # no flat +$10 per level
        self.assertAlmostEqual(run.interest_rate(), 0.25)
        run.relics = ["piggy_bank"]
        self.assertAlmostEqual(run.interest_rate(), 0.30)
        run.money = 1000
        summary = run.end_round()
        self.assertEqual(summary["interest"], 300)
        self.assertEqual(run.money, 1300)


class CompostHeapTests(unittest.TestCase):
    def test_compost_doubles_harvests_only_in_final_15_seconds(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["compost"]
        run.begin_round()
        run.start_timer()
        run.plots = [Plot("sunflower")]  # yield 14

        run.time_left = 20.0
        self.assertFalse(run.compost_active())
        self.assertEqual(run.harvest_value(0), 14)

        run.time_left = 15.0
        self.assertTrue(run.compost_active())
        self.assertEqual(run.harvest_value(0), 28)

    def test_compost_splits_single_large_update_across_15s_threshold(self):
        run = Run(seed=1)
        run.auto_harvest = True
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["compost"]
        run.begin_round()
        run.start_timer()
        run.money = 0
        # Daisy grows every 5s (yield 2 plain, 4 in final 15s).
        # Start at 20s left and advance 10s in one call:
        #   20s -> 15s (5s): 1 plain harvest ($2)
        #   15s -> 10s (5s): 1 compost-boosted harvest ($4)
        run.time_total = 45.0
        run.time_left = 20.0
        run.plots = [Plot("daisy")]
        run.update(10.0)
        self.assertAlmostEqual(run.time_left, 10.0)
        harvests = [ev["amount"] for ev in run.events if ev["kind"] == "harvest"]
        self.assertEqual(harvests, [2, 4])
        self.assertTrue(any(ev["kind"] == "compost" for ev in run.events))

    def test_compost_doubles_end_of_round_sale_when_in_window_not_early(self):
        # Ending naturally at 0s -> 2x sale
        natural = Run(seed=1)
        natural.relics = ["compost"]
        natural.begin_round()
        natural.start_timer()
        natural.plots = [Plot("pumpkin", progress=10.0)]  # half of 20s, sell 150 -> base 75, 2x = 150
        natural.time_left = 0.0
        natural.finished = True
        s_nat = natural.end_round()
        self.assertEqual(s_nat["sale"], 150)

        # Bailing out early at 30s left -> 1x sale
        early = Run(seed=1)
        early.relics = ["compost"]
        early.begin_round()
        early.start_timer()
        early.plots = [Plot("pumpkin", progress=10.0)]
        early.time_left = 30.0
        early.finish_early()
        s_early = early.end_round()
        self.assertEqual(s_early["sale"], 75)


class UnpaidQuotaTests(unittest.TestCase):
    def test_short_on_quota_does_not_instantly_end_run(self):
        run = Run(seed=1)
        run.round = 3
        run.money = 50  # bill is $300
        summary = run.end_round()
        self.assertFalse(run.dead)
        self.assertEqual(run.phase, "summary")
        self.assertTrue(summary["pending_bill"])
        self.assertFalse(summary["can_afford"])
        self.assertEqual(summary["shortfall"], 250)
        self.assertIsNone(summary["paid"])

        # Attempting to pay fails without killing the run
        ok, _ = run.pay_pending_bill()
        self.assertFalse(ok)
        self.assertFalse(run.dead)
        self.assertEqual(run.pending_bill, 300)

        # Pressing Don't Pay (decline_bill) ends the run
        run.decline_bill()
        self.assertTrue(run.dead)
        self.assertEqual(run.pending_bill, 0)

    def test_summary_scene_disables_pay_and_waits_for_dont_pay(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.round = 3
                app.run.money = 100
                app.after_round()
                self.assertEqual(app.scene_name, "summary")
                self.assertIsNotNone(app.run)
                self.assertFalse(app.scene.pay_btn.enabled)
                self.assertTrue(app.scene.decline_btn.enabled)
                # Space does not skip an unpaid bill
                app.handle_key(pygame.K_SPACE)
                self.assertEqual(app.scene_name, "summary")
                # Clicking Don't Pay finishes the run and opens gameover
                bx, by = app.scene.decline_btn.x + 5, app.scene.decline_btn.y + 5
                app.handle_click((bx, by))
                self.assertEqual(app.scene_name, "gameover")
                self.assertIsNone(app.run)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_insurance_waiver_is_offered_on_the_summary_screen(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.perks["insurance"] = 1
                app.run.bill_waivers = 1
                app.run.round = 3
                app.run.money = 100
                app.after_round()
                self.assertEqual(app.scene_name, "summary")
                self.assertTrue(app.scene.pay_btn.enabled)
                self.assertEqual(app.scene.pay_btn.label, "USE WAIVER")
                bx, by = app.scene.decline_btn.x + 5, app.scene.decline_btn.y + 5
                app.handle_click((bx, by))
                self.assertIsNotNone(app.confirm_modal)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

class RareRelicPricingTests(unittest.TestCase):
    def test_rare_relics_start_slightly_above_uncommon_and_scale_steeper(self):
        from .settings import PRICE_GROWTH, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH
        self.assertGreater(RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH)
        self.assertLess(RARE_RELIC_PRICE_GROWTH, PRICE_GROWTH)

        uncommons = [r for r, d in data.RELICS.items() if d["rarity"] == "uncommon"]
        rares = [r for r, d in data.RELICS.items() if d["rarity"] == "rare"]
        max_uncommon_base = max(data.RELICS[r]["cost"] for r in uncommons)
        for rid in rares:
            self.assertGreater(data.RELICS[rid]["cost"], max_uncommon_base)
            self.assertLessEqual(data.RELICS[rid]["cost"], 850)

        r1 = Run(seed=1)
        max_u_r1 = max(r1.relic_price(r) for r in uncommons)
        min_r_r1 = min(r1.relic_price(r) for r in rares)
        self.assertGreater(min_r_r1, max_u_r1)
        self.assertLess(min_r_r1, max_u_r1 * 2.0)

        r10 = Run(seed=1)
        r10.round = 10
        uncommon_ratio = r10.relic_price("scarecrow") / r1.relic_price("scarecrow")
        rare_ratio = r10.relic_price("clover") / r1.relic_price("clover")
        self.assertGreater(rare_ratio, uncommon_ratio)


class ShovelAndMenuTests(unittest.TestCase):
    def test_remove_plant_clears_surface_and_cellar_plots(self):
        run = Run(seed=1)
        run.begin_round()
        run.plots[0] = Plot("daisy", progress=2.0)
        run.cellar_plots[0] = Plot("brown_mushroom", progress=2.0)
        ok, _ = run.remove_plant(0, cellar=False)
        self.assertTrue(ok)
        self.assertIsNone(run.plots[0].species)
        ok_empty, _ = run.remove_plant(0, cellar=False)
        self.assertFalse(ok_empty)
        ok_cellar, _ = run.remove_plant(0, cellar=True)
        self.assertTrue(ok_cellar)
        self.assertIsNone(run.cellar_plots[0].species)

    def test_shovel_confirmation_pause_settings_and_flower_index(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                # Main page has Flower Index book & Settings cogwheel
                self.assertEqual(app.scene_name, "title")
                self.assertEqual(app.scene.book_btn.icon, "book")
                self.assertEqual(app.scene.cog_btn.icon, "cog")

                # Open settings from main page
                app.handle_click((app.scene.cog_btn.x + 4, app.scene.cog_btn.y + 4))
                self.assertIsNotNone(app.settings_modal)
                app.handle_key(pygame.K_ESCAPE)
                self.assertIsNone(app.settings_modal)

                # Open Flower Index ("Little Book") and inspect plants + mutants
                app.handle_click((app.scene.book_btn.x + 8, app.scene.book_btn.y + 8))
                self.assertEqual(app.scene_name, "index")
                app.scene.draw(app.canvas)
                self.assertTrue(app.scene.mutant_rects)
                mid, mrect = app.scene.mutant_rects[0]
                app.handle_click((mrect[0] + 4, mrect[1] + 4))
                self.assertEqual(app.scene.selected, mid)
                app.scene.draw(app.canvas)
                self.assertIsNotNone(app.scene.base_rect)
                app.handle_key(pygame.K_ESCAPE)
                self.assertEqual(app.scene_name, "title")

                # Start a run, plant a seed, test Shovel + Confirmation
                app.new_run()
                app.run.seeds["daisy"] = 2
                app.goto("round")
                app.scene.selected = "daisy"
                from .round import plot_rect
                px, py, pw, ph = plot_rect(0)
                app.handle_click((px + pw // 2, py + ph // 2))
                self.assertEqual(app.run.plots[0].species, "daisy")

                # Activate shovel and click planted plot -> opens ConfirmModal first
                sx, sy = app.scene.shovel_btn.x + 5, app.scene.shovel_btn.y + 5
                app.handle_click((sx, sy))
                self.assertTrue(app.scene.shovel_mode)
                app.handle_click((px + pw // 2, py + ph // 2))
                self.assertIsNotNone(app.confirm_modal)
                self.assertEqual(app.run.plots[0].species, "daisy")  # still there before confirm
                # Confirm removal
                cx, cy = app.confirm_modal.confirm_btn.x + 5, app.confirm_modal.confirm_btn.y + 5
                app.handle_click((cx, cy))
                self.assertIsNone(app.confirm_modal)
                self.assertIsNone(app.run.plots[0].species)

                # Pause menu opens on ESC, freezes timer, has settings cog, new run, quit, heirlooms
                app.run.start_timer()
                before_t = app.run.time_left
                app.handle_key(pygame.K_ESCAPE)
                self.assertIsNotNone(app.pause_modal)
                self.assertEqual(app.pause_modal.cog_btn.icon, "cog")
                # Open settings from pause menu and close back to pause menu
                app.handle_click((app.pause_modal.cog_btn.x + 4, app.pause_modal.cog_btn.y + 4))
                self.assertIsNotNone(app.settings_modal)
                app.handle_key(pygame.K_ESCAPE)
                self.assertIsNone(app.settings_modal)
                self.assertIsNotNone(app.pause_modal)
                self.assertEqual(app.run.time_left, before_t)

                # New Run from Pause menu asks for confirmation
                nx, ny = app.pause_modal.new_btn.x + 5, app.pause_modal.new_btn.y + 5
                app.handle_click((nx, ny))
                self.assertIsNotNone(app.confirm_modal)
                app.handle_key(pygame.K_ESCAPE)  # cancel
                self.assertIsNone(app.confirm_modal)
                self.assertIsNotNone(app.pause_modal)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_bill_progress_advances_after_paying_bill_in_shop(self):
        run = Run(seed=1)
        run.round = 3
        run.money = 400
        bp_before = run.bill_progress()
        self.assertTrue(bp_before["due_now"])
        self.assertEqual(bp_before["quota_index"], 1)
        self.assertEqual(bp_before["bill"], 300)

        run.end_round()
        ok, _ = run.pay_pending_bill()
        self.assertTrue(ok)
        run.enter_shop()
        bp_after = run.bill_progress()
        self.assertFalse(bp_after["due_now"])
        self.assertEqual(bp_after["quota_index"], 2)
        self.assertEqual(bp_after["quota_round"], 6)
        self.assertEqual(bp_after["bill"], 1500)

class RegressionFixTests(unittest.TestCase):
    def test_compost_and_mutagen_do_not_scale_with_unrelated_relics(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["compost", "almanac", "big_can", "clover"]
        run.begin_round()
        run.start_timer()
        run.time_left = 10.0
        run.plots = [Plot("sunflower")]  # base yield 14 -> 28 in final 15s
        self.assertEqual(run.harvest_value(0), 28)

        run2 = Run(seed=1)
        run2.twist_id = lambda _rnd=None: "none"
        run2.relics = ["mutagen", "almanac", "big_can", "clover"]
        run2.plots = [Plot("sunflower_gold")]  # base yield 42 -> 50 with 1.2x
        self.assertEqual(run2.harvest_value(0), 50)

    def test_compost_does_not_apply_to_unstarted_round_sale(self):
        run = Run(seed=1)
        run.relics = ["compost"]
        run.begin_round()
        run.plots = [Plot("pumpkin", progress=10.0)]  # half of 20s, sell 150 -> 75
        summary = run.end_round()
        self.assertEqual(summary["sale"], 75)

    def test_relic_levels_refresh_even_when_event_queue_is_full(self):
        run = Run(seed=1)
        run.relics = ["fertilizer"]
        run.begin_round()
        run.counters["harvest"] = 249
        run.plots = [Plot("daisy")]
        run.events = [{"kind": "noop"} for _ in range(300)]
        run._harvest(0)
        self.assertEqual(run._relic_lvls.get("fertilizer"), 1)

    def test_shop_buttons_work_and_non_escape_keys_stay_in_shop(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.money = 50000
                app.run.enter_shop()
                app.goto("shop")
                self.assertTrue(app.scene.buttons)

                # Non-Escape keys must not kick the player back to title
                app.handle_key(pygame.K_SPACE)
                app.handle_key(pygame.K_a)
                self.assertEqual(app.scene_name, "shop")

                # Buy relic, reroll, buy plot, and proceed to next round
                b0 = app.scene.buy_buttons[0]
                app.handle_click((b0.x + 4, b0.y + 4))
                self.assertEqual(len(app.run.relics), 1)
                plots_before = len(app.run.plots)
                pb = app.scene.plot_btn
                app.handle_click((pb.x + 4, pb.y + 4))
                self.assertEqual(len(app.run.plots), plots_before + 1)
                nb = app.scene.next_btn
                app.handle_click((nb.x + 4, nb.y + 4))
                self.assertEqual(app.scene_name, "packs")
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_summary_scene_draws_only_relevant_right_panel(self):
        try:
            import pygame  # noqa: F401
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                # Non-pending summary should draw UP NEXT forecast in lower right panel
                app.new_run()
                app.run.round = 1
                app.run.money = 100
                app.after_round()
                app.scene.draw(app.canvas)
                bg = (38, 33, 58, 255)
                non_bg = sum(
                    1
                    for y in range(105, 140)
                    for x in range(170, 305)
                    if app.canvas.get_at((x, y)) != bg
                )
                self.assertGreater(non_bg, 0)

                # Pending summary must not overwrite Bill Collector bottom with UP NEXT
                app.new_run()
                app.run.round = 3
                app.run.money = 500
                app.after_round()
                app.scene.draw(app.canvas)
                stray = sum(
                    1
                    for y in range(120, 138)
                    for x in range(169, 306)
                    if app.canvas.get_at((x, y)) != bg
                )
                self.assertEqual(stray, 0)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_round_scene_update_floaters_fast_shovel_and_topbar(self):
        try:
            import pygame
        except ImportError:
            self.skipTest("pygame not installed")
        import os, tempfile
        from .app import App
        from .scene import TOPBAR_PAUSE_RECT
        from .settings import TEXT
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.cellar_unlocked = True
                app.run.relics = ["compost"]
                app.goto("round")

                # Cellar tray starts at the first page: the left pager is always
                # disabled, and the right one only lights up when it overflows.
                from .round import TRAY_SLOTS
                app.scene.cellar_click()
                self.assertFalse(app.scene.tray_left.enabled)
                self.assertEqual(
                    app.scene.tray_right.enabled, len(app.scene.view_seeds()) > TRAY_SLOTS)
                app.scene.toggle_shovel()
                app.scene.draw(app.canvas)
                self.assertTrue(app.scene.shovel_btn.active)

                # First ESC cancels shovel mode; second ESC opens pause menu
                app.handle_key(pygame.K_ESCAPE)
                self.assertFalse(app.scene.shovel_mode)
                self.assertIsNone(app.pause_modal)
                app.handle_key(pygame.K_ESCAPE)
                self.assertIsNotNone(app.pause_modal)
                app.pause_modal.resume()

                # Surface: update processes fast mode, t sway, floaters, compost toast, and clears events
                app.settings_cfg["auto_harvest"] = True
                app.scene.cellar_click()
                app.run.seeds["daisy"] = 5
                app.run.plant(0, "daisy")
                app.run.start_timer()
                app.run.time_left = 18.0
                app.scene.fast = 10
                app.scene.update(0.5)  # 5s -> 13s left: 1 daisy harvest + compost toast
                self.assertAlmostEqual(app.run.time_left, 13.0)
                self.assertGreater(app.scene.t, 0.0)
                self.assertEqual(len(app.scene.floaters), 1)
                self.assertEqual(app.run.events, [])
                self.assertIn("COMPOST HEAP", app.toasts[0][0])

                # Timer renders strictly left of pause button
                app.scene.draw(app.canvas)
                px = TOPBAR_PAUSE_RECT[0]
                timer_pixels = sum(
                    1
                    for y in range(2, 8)
                    for x in range(px - 22, px)
                    if app.canvas.get_at((x, y))[:3] == TEXT
                )
                self.assertGreater(timer_pixels, 0)

                # Hovering pause button keeps pause bars visible against fill
                app.mouse = (TOPBAR_PAUSE_RECT[0] + 4, 4)
                app.scene.draw(app.canvas)
                colors = {app.canvas.get_at((x, y))[:3] for y in range(3, 11) for x in range(301, 315)}
                self.assertGreaterEqual(len(colors), 2)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_chosen_bloom_is_spent_when_plant_is_destroyed(self):
        for kind in ("crow_swarm", "root_rot", "meteor_shower", "blight", "devour"):
            with self.subTest(kind=kind):
                run = Run(seed=1)
                run.relics = ["chosen_bloom"]
                run.begin_round()
                if kind == "devour":
                    run.plots = [Plot("venus_flytrap_maneater"), Plot("daisy"), Plot(), Plot()]
                    self.assertTrue(run.choose_plant(1))
                    run._devour(0)
                    victim = 1
                else:
                    run.twist_id = lambda _rnd=None, k=kind: k
                    run.begin_round()
                    run.plots = [Plot("daisy")]
                    self.assertTrue(run.choose_plant(0))
                    run.start_timer()
                    if kind == "blight":
                        run.update(run.time_total / 2.0 + 0.1)
                    elif kind == "meteor_shower":
                        with patch.object(run.rng, "random", return_value=0.0):
                            run.update(10.1)
                    else:
                        run.update(8.1)
                    victim = 0
                self.assertIsNone(run.plots[victim].species)
                self.assertFalse(run.is_chosen(victim))
                run.plots.append(Plot("daisy"))
                self.assertFalse(run.choose_plant(len(run.plots) - 1))
                run.seeds["daisy"] = 1
                self.assertTrue(run.plant(victim, "daisy"))
                self.assertFalse(run.is_chosen(victim))
                self.assertEqual(run.harvest_value(victim), data.PLANTS["daisy"]["yield"])

    def test_spare_plot_price_does_not_depend_on_when_it_is_taken(self):
        at_start = Run(seed=1, perks={"plots": 4})
        mid_run = Run(seed=1, perks={})
        for _ in range(4):
            ok, _, _ = mid_run.buy_heirloom("plots", 1000)
            self.assertTrue(ok)
        self.assertEqual(len(at_start.plots), len(mid_run.plots))
        self.assertEqual(at_start.plots_bought, mid_run.plots_bought)
        self.assertEqual(at_start.plot_price(), mid_run.plot_price())

        first_perk = Run(seed=1, perks={"plots": 1})
        first_perk.money = 10000
        self.assertTrue(first_perk.buy_plot())
        shop_first = Run(seed=1, perks={})
        shop_first.money = 10000
        self.assertTrue(shop_first.buy_plot())
        self.assertTrue(shop_first.buy_heirloom("plots", 1000)[0])
        self.assertEqual(len(first_perk.plots), len(shop_first.plots))
        self.assertEqual(first_perk.plot_price(), shop_first.plot_price())

    def test_dead_calm_matches_other_minor_twists(self):
        minor = [Run(seed=s).twist_id(2) for s in range(1, 4001)]
        non_none = [tw for tw in minor if tw != "none"]
        still_share = non_none.count("still") / len(non_none)
        self.assertLess(abs(still_share - 1.0 / len(data.MINOR_TWISTS)), 0.03)

    def test_relic_resale_refunds_half_of_price_paid(self):
        run = Run(seed=1)
        run.round = 3
        run.money = 100000
        run.shop_offers = ["greenhouse"]
        paid = run.relic_offer_price(0)
        self.assertTrue(run.buy_relic(0)[0])
        run.round = 12
        restored = Run.from_dict(run.to_dict())
        ok, _, refund = restored.sell_relic(0)
        self.assertTrue(ok)
        self.assertEqual(refund, int(paid * 0.5))
        self.assertLess(refund, paid)

        free_run = Run(seed=1)
        free_run.round = 3
        free_run.shop_offers = ["greenhouse"]
        free_run.free_offer = 0
        self.assertTrue(free_run.buy_relic(0)[0])
        free_run.round = 15
        ok, _, free_refund = free_run.sell_relic(0)
        self.assertTrue(ok)
        self.assertEqual(free_refund, 0)

    def test_corrupt_saves_back_up_instead_of_wiping_or_crashing(self):
        from .app import App
        from .save import SaveManager
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"BLOOM_SAVE_DIR": tmp}):
            saves = SaveManager()
            saves.profile_path.write_text("{corrupt", encoding="utf-8")
            profile = saves.load_profile()
            self.assertEqual(profile["heirlooms"], 0)
            self.assertTrue((saves.folder / "profile.json.bak").exists())

            saves.profile_path.write_bytes(b"\xff\xfe\xfd")
            profile = saves.load_profile()
            self.assertEqual(profile["perks"], {})

            saves.profile_path.write_text('{"perks": "bad", "heirlooms": "oops"}', encoding="utf-8")
            profile = saves.load_profile()
            self.assertEqual(profile["perks"], {})
            self.assertEqual(profile["heirlooms"], 0)

            saves.run_path.write_bytes(b"\xff\xfe\xfd")
            self.assertIsNone(saves.load_run())
            self.assertTrue((saves.folder / "run.json.bak").exists())

            saves.run_path.write_text('{"rng": [1, "bad"]}', encoding="utf-8")
            app = App()
            app.continue_run()
            self.assertTrue((saves.folder / "run.json.bak").exists())
            self.assertIsNotNone(app.run)




class SpriteAndCleanupTests(unittest.TestCase):
    """Verify completed sprites, gear icon, shop relic icons, and simulation bug fixes."""

    @classmethod
    def setUpClass(cls):
        import pygame
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_every_plant_relic_and_mutant_has_finished_sprite_art(self):
        import pygame
        from . import gfx
        from .sprites_data import GRIDS, PALETTE

        for name, rows in GRIDS.items():
            widths = {len(row) for row in rows}
            self.assertEqual(len(widths), 1, "%s has jagged rows" % name)
            allowed = set(PALETTE) | {"."} | ({"1", "2"} if name == "pack" else set())
            for row in rows:
                self.assertTrue(set(row) <= allowed, "%s uses unknown palette keys" % name)

        unknown_bytes = pygame.image.tobytes(gfx.sprite("unknown"), "RGBA")
        for pid in data.PLANT_ORDER:
            self.assertIn(pid, GRIDS, "missing plant sprite: %s" % pid)
            surf = gfx.sprite(pid)
            self.assertEqual(surf.get_size(), (12, 12))
            self.assertNotEqual(pygame.image.tobytes(surf, "RGBA"), unknown_bytes)

        for rid in data.RELIC_ORDER:
            self.assertIn(rid, GRIDS, "missing relic sprite: %s" % rid)
            surf = gfx.sprite(rid)
            self.assertEqual(surf.get_size(), (12, 12))
            self.assertNotEqual(pygame.image.tobytes(surf, "RGBA"), unknown_bytes)

        for mid in data.MUTANTS:
            sp = data.PLANTS[mid]
            base_surf = gfx.sprite(sp["base"])
            mut_surf = gfx.sprite(sp["base"], 1, sp.get("subs"))
            self.assertNotEqual(
                pygame.image.tobytes(base_surf, "RGBA"),
                pygame.image.tobytes(mut_surf, "RGBA"),
                "%s visually identical to %s" % (mid, sp["base"]),
            )

    def test_cog_sprite_is_toothed_gear_and_recolors_on_hover(self):
        import pygame
        from . import gfx
        from .sprites_data import GRIDS

        cog_rows = GRIDS["cog"]
        self.assertEqual((len(cog_rows[0]), len(cog_rows)), (15, 15))
        # Center axle hole is transparent; cardinal and diagonal tooth tips are opaque.
        self.assertEqual(cog_rows[7][7], ".")
        for tx, ty in ((7, 0), (7, 14), (0, 7), (14, 7), (2, 1), (12, 1), (2, 13), (12, 13)):
            self.assertNotEqual(cog_rows[ty][tx], ".", "missing gear tooth at (%d, %d)" % (tx, ty))

        normal = pygame.image.tobytes(gfx.sprite("cog"), "RGBA")
        hovered = pygame.image.tobytes(gfx.sprite("cog", 1, gfx.COG_HOVER_SUBS), "RGBA")
        self.assertNotEqual(normal, hovered)

    def test_shop_cards_render_relic_sprites_and_evolution_tooltips(self):
        import os
        import tempfile
        from .app import App

        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.enter_shop()
                app.run.shop_offers = ["green_thumb", "mutagen", "beehive"]
                app.goto("shop")
                app.mouse = (14, 28)  # Hover evolving Green Thumb card
                app.scene.draw(app.canvas)
                # Multi-color pixel sprite inside first card's 12x12 icon box (x=11..22, y=25..36)
                icon_colors = {
                    app.canvas.get_at((x, y))[:3]
                    for y in range(25, 37)
                    for x in range(11, 23)
                }
                self.assertGreaterEqual(len(icon_colors), 4)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old

    def test_saved_evolved_relic_does_not_reemit_evolve_toast_after_load(self):
        run = Run(seed=7)
        run.relics = ["big_can"]
        run.counters["water"] = 160
        restored = Run.from_dict(run.to_dict())
        self.assertEqual(restored._relic_lvls.get("big_can"), 1)
        restored.begin_round()
        restored.start_timer()
        restored.update(0.1)
        self.assertFalse(any(ev["kind"] == "evolve" for ev in restored.events))

    def test_hailstorm_event_queue_is_bounded_and_plot_growth_speed_respects_twists(self):
        from .settings import CELLAR_SPEED
        from .state import MAX_EVENTS

        run = Run(seed=9)
        run.twist_id = lambda _rnd=None: "hailstorm"
        run.begin_round()
        run.plant(0, "daisy")
        run.start_timer()
        run.update(60.0)
        self.assertLessEqual(len(run.events), MAX_EVENTS)

        eclipse_run = Run(seed=10)
        eclipse_run.twist_id = lambda _rnd=None: "eclipse"
        eclipse_run.cellar_unlocked = True
        eclipse_run.plots[0] = Plot("daisy")
        eclipse_run.plots[1] = Plot("brown_mushroom")
        eclipse_run.cellar_plots[0] = Plot("brown_mushroom")
        self.assertAlmostEqual(eclipse_run.plot_growth_speed(0, False), 0.8)
        self.assertAlmostEqual(eclipse_run.plot_growth_speed(1, False), 1.3)
        self.assertAlmostEqual(eclipse_run.plot_growth_speed(0, True), CELLAR_SPEED)

        gale_run = Run(seed=11)
        gale_run.twist_id = lambda _rnd=None: "gale"
        gale_run.plots[0] = Plot("daisy")
        self.assertAlmostEqual(gale_run.plot_growth_speed(0, False), 0.8)

    def test_shop_topbar_money_matches_round_position_left_of_pause(self):
        import os
        import tempfile
        from .app import App
        from .scene import TOPBAR_PAUSE_RECT
        from .settings import ACCENT

        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("BLOOM_SAVE_DIR")
            os.environ["BLOOM_SAVE_DIR"] = tmp
            try:
                app = App()
                app.new_run()
                app.run.money = 1250

                def money_xs():
                    app.scene.draw(app.canvas)
                    return {
                        x
                        for y in range(2, 8)
                        for x in range(200, TOPBAR_PAUSE_RECT[0])
                        if app.canvas.get_at((x, y))[:3] == ACCENT
                    }

                app.goto("round")
                round_xs = money_xs()
                self.assertTrue(round_xs)
                self.assertLess(max(round_xs), TOPBAR_PAUSE_RECT[0] - 20)

                app.run.enter_shop()
                app.goto("shop")
                shop_xs = money_xs()
                self.assertEqual(shop_xs, round_xs)
            finally:
                if old is None:
                    os.environ.pop("BLOOM_SAVE_DIR", None)
                else:
                    os.environ["BLOOM_SAVE_DIR"] = old


def sprite_patches(grid, key):
    """Connected patches of one palette key in a sprite grid; diagonal neighbours count as touching."""
    cells = {(x, y) for y, row in enumerate(grid) for x, char in enumerate(row) if char == key}
    patches = []
    while cells:
        patch, todo = set(), [cells.pop()]
        while todo:
            x, y = todo.pop()
            patch.add((x, y))
            for near in ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                if near in cells:
                    cells.remove(near)
                    todo.append(near)
        patches.append(patch)
    return patches


def clover_leaves(grid):
    """Split a clover sprite into its leaves: one set of (x, y) cells per leaf.

    A leaf is a darker eye ('g') completely ringed by light green ('l'). The
    hub and the stem use 'g' too, but they are open to the soil on some side,
    so they are not leaves.
    """
    light = set().union(*sprite_patches(grid, "l"))
    leaves = []
    for eye in sprite_patches(grid, "g"):
        ring = {(x + dx, y + dy) for x, y in eye for dx in (-1, 0, 1) for dy in (-1, 0, 1)} - eye
        if ring <= light:
            leaves.append(eye | ring)
    return leaves


class DesertAndLayoutPlantTests(unittest.TestCase):
    """The desert shelf, the layout plants, and the packs they live in."""

    NEW_PLANTS = ["aloe_vera", "prickly_pear", "agave", "four_leaf_clover", "venus_flytrap", "mycelium"]

    def test_desert_pack_is_desert_only(self):
        pool = data.PACKS["desert"]["pool"]
        self.assertTrue(pool)
        for sid in pool:
            with self.subTest(plant=sid):
                self.assertIn("desert", data.PLANTS[sid]["tags"])
        for sid in ("cactus", "aloe_vera", "prickly_pear", "agave"):
            self.assertIn(sid, pool)

    def test_garden_pack_swapped_cactus_for_a_very_rare_orchid(self):
        pool = data.PACKS["garden"]["pool"]
        self.assertNotIn("cactus", pool)
        self.assertIn("orchid", pool)
        self.assertLessEqual(pool["orchid"], 1)          # 1-in-100 jackpot
        self.assertLess(pool["orchid"], min(w for s, w in pool.items() if s != "orchid"))

    def test_harvest_pack_is_an_autumn_shelf(self):
        pool = data.PACKS["harvest"]["pool"]
        self.assertEqual(
            set(pool), {"pumpkin", "corn", "cranberries", "wheat", "potato", "carrot"})
        for summer in ("tomato", "sunflower", "cactus"):
            self.assertNotIn(summer, pool)

    def test_clover_mycelium_and_flytrap_have_pack_homes(self):
        self.assertIn("four_leaf_clover", data.PACKS["rare"]["pool"])
        self.assertIn("mycelium", data.PACKS["garden"]["pool"])     # garden
        self.assertIn("mycelium", data.PACKS["nocturnal"]["pool"])  # cellar
        self.assertIn("venus_flytrap", data.PACKS["garden"]["pool"])
        self.assertIn("venus_flytrap", data.PLANT_ORDER)

    def test_every_new_plant_is_wired_up(self):
        for sid in self.NEW_PLANTS:
            with self.subTest(plant=sid):
                plant = data.PLANTS[sid]
                self.assertGreater(plant["grow"], 0)
                self.assertGreater(plant["yield"], 0)
                self.assertGreater(plant["sell"], 0)
                self.assertIn(plant["rarity"], data.RARITY_COLORS)
                self.assertIn(sid, data.PLANT_ORDER)
                self.assertIn(sid, data.SURFACE_PLANTS)
                self.assertTrue(data.packs_for_plant(sid))

    def test_every_new_mutant_is_worth_more_than_its_base(self):
        for sid in self.NEW_PLANTS:
            for mid in data.mutants_for(sid):
                with self.subTest(mutant=mid):
                    self.assertGreater(data.PLANTS[mid]["yield"], data.PLANTS[sid]["yield"])
                    self.assertGreater(data.PLANTS[mid]["sell"], data.PLANTS[sid]["sell"])

    def test_all_new_plants_and_mutants_are_in_the_flower_index(self):
        from .index import _category_ids
        everything = _category_ids("all")
        for sid in self.NEW_PLANTS:
            self.assertIn(sid, everything)
        for mid in data.MUTANTS:
            self.assertIn(mid, everything)
        desert = _category_ids("desert")
        for sid in data.DESERT_PLANTS:
            self.assertIn(sid, desert)
        self.assertEqual(set(desert), set(data.DESERT_PLANTS))

    def test_every_new_plant_has_its_own_sprite(self):
        import pygame
        from . import gfx
        from .sprites_data import GRIDS
        pygame.init()
        pygame.display.set_mode((1, 1))
        unknown = pygame.image.tobytes(gfx.sprite("unknown"), "RGBA")
        for sid in self.NEW_PLANTS:
            self.assertIn(sid, GRIDS)
            self.assertNotEqual(pygame.image.tobytes(gfx.sprite(sid), "RGBA"), unknown)
        for mid in data.MUTANTS:
            self.assertIn(data.PLANTS[mid].get("base"), GRIDS)

    def test_five_leaf_clover_has_five_leaves_of_its_own_art(self):
        from .sprites_data import GRIDS
        five = GRIDS["five_leaf_clover"]
        four = GRIDS["four_leaf_clover"]
        self.assertEqual(len(five), len(four))
        self.assertTrue(all(len(row) == 12 for row in five))
        self.assertNotEqual(five, four)
        self.assertGreater(sum(row.count("l") for row in five), sum(row.count("l") for row in four))
        # Count the leaves themselves. More green is not proof: a four-leaf
        # drawing with a thicker middle used to pass as the five-leaf one.
        self.assertEqual(len(clover_leaves(four)), 4)
        leaves = clover_leaves(five)
        self.assertEqual(len(leaves), 5)
        # Five separate leaves: the light green makes five patches that never
        # touch, not even at a corner, and each patch holds exactly one leaf.
        patches = sprite_patches(five, "l")
        self.assertEqual(len(patches), 5)
        for patch in patches:
            self.assertEqual(sum(1 for leaf in leaves if leaf & patch), 1)
        self.assertEqual(data.PLANTS["five_leaf_clover"]["art"], "five_leaf_clover")
        self.assertFalse(data.PLANTS["five_leaf_clover"]["pays"])
        self.assertGreater(
            data.PLANTS["five_leaf_clover"]["bloom_chance"],
            data.PLANTS["four_leaf_clover"]["bloom_chance"])

    def test_a_ripe_five_leaf_clover_shows_its_five_leaves_on_the_plot(self):
        import pygame
        from types import SimpleNamespace
        from . import gfx
        from .round import RoundScene, CELL_W, CELL_H
        pygame.init()
        pygame.display.set_mode((1, 1))
        sp = data.PLANTS["five_leaf_clover"]

        def drawn(species, progress):
            """Draw one plot through the round screen and return its pixels."""
            app = SimpleNamespace(run=Run(seed=5), mouse=(319, 179),
                                  toast=lambda *args: None, save_run=lambda: None)
            scene = RoundScene(app)
            scene.on_enter()
            app.run.plots = [Plot(species, progress=progress)]
            tile = pygame.Surface((CELL_W, CELL_H))
            scene.draw_plot(app.run.plots, tile, 0, 0, 0, CELL_W, CELL_H)
            return tile

        def shows(tile, sprite_name):
            """True if every opaque pixel of the (recoloured, 2x) sprite is somewhere on the tile."""
            art = gfx.sprite(sprite_name, 2, sp["subs"])
            w, h = art.get_size()
            ink = [(x, y, tuple(art.get_at((x, y)))[:3])
                   for y in range(h) for x in range(w) if art.get_at((x, y))[3]]
            return any(
                all(tuple(tile.get_at((ox + x, oy + y)))[:3] == rgb for x, y, rgb in ink)
                for oy in range(tile.get_height() - h + 1)
                for ox in range(tile.get_width() - w + 1)
            )

        ripe = drawn("five_leaf_clover", sp["grow"] * 0.9)
        self.assertTrue(shows(ripe, "five_leaf_clover"))
        self.assertFalse(shows(ripe, "four_leaf_clover"))
        # Still growing, it is a sprout like any other plant.
        self.assertFalse(shows(drawn("five_leaf_clover", sp["grow"] * 0.3), "five_leaf_clover"))


class MyceliumTests(unittest.TestCase):
    def run_with(self, *species):
        run = Run(seed=3)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot(s) for s in species] + [Plot() for _ in range(12 - len(species))]
        return run

    def test_a_connected_patch_pays_more_than_a_lonely_one(self):
        alone = self.run_with("mycelium").harvest_value(0)
        patch = self.run_with("mycelium", "mycelium", "mycelium", "mycelium")
        self.assertGreater(patch.harvest_value(0), alone)
        self.assertGreater(patch.network_share(4), patch.network_share(2))
        self.assertEqual(len(patch.mycelium_network(0)), 4)

    def test_a_detached_mycelium_does_not_join_the_network(self):
        run = self.run_with("mycelium", "mycelium", "daisy", "daisy", "daisy", "daisy", "mycelium")
        self.assertEqual(run.mycelium_network(0), [0, 1])
        self.assertEqual(run.mycelium_network(6), [6])
        self.assertLess(run.harvest_value(6), run.harvest_value(0))

    def test_mycelium_spreads_into_an_empty_neighbour(self):
        run = self.run_with("mycelium")
        run.rng.random = lambda: 0.0            # always roll the spread
        run.started = True
        run._harvest(0)
        self.assertEqual(sum(1 for p in run.plots if p.species == "mycelium"), 2)
        self.assertTrue(any(ev["kind"] == "spread" for ev in run.events))

    def test_spread_stops_when_every_neighbour_is_full(self):
        run = self.run_with(*(["daisy"] * 12))
        run.plots[0] = Plot("mycelium")
        run.rng.random = lambda: 0.0
        run.started = True
        run._harvest(0)
        self.assertEqual(sum(1 for p in run.plots if p.species == "mycelium"), 1)

    def test_a_patch_keeps_creeping_from_its_edge_after_a_harvest_spread(self):
        # Regression: the roll used to belong to the harvested plot alone, so
        # once that plot had all four neighbours filled the patch stopped
        # growing even though the rest of it had room.
        run = self.run_with("mycelium")
        run.rng.random = lambda: 0.0
        run.started = True
        for _ in range(3):
            for p in run.plots:
                p.creep_cd = 0.0
            run._harvest(0)                       # always the original, boxed-in plot
        grown = [i for i, p in enumerate(run.plots) if p.species == "mycelium"]
        self.assertEqual(len(grown), 4, "the patch edge must keep spreading")
        self.assertTrue(
            all(any(n in grown for n in run.neighbours(i)) for i in grown),
            "new plots must land orthogonally beside the existing patch",
        )

    def test_creep_meter_books_a_guaranteed_spread_even_with_no_harvest_luck(self):
        from .settings import MYCELIUM_CREEP_TIME
        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium")] + [Plot() for _ in range(11)]
        run.rng.random = lambda: 0.99             # every harvest roll fails
        run.start_timer()
        step = MYCELIUM_CREEP_TIME / 4.0
        run.update(step * 3)
        self.assertEqual(len([p for p in run.plots if p.species == "mycelium"]), 1)
        run.update(step)
        self.assertEqual(
            len([p for p in run.plots if p.species == "mycelium"]), 2,
            "a full creep meter must spread on its own",
        )
        self.assertEqual(run.plots[0].creep_cd, 0.0, "spreading resets the meter")

    def test_one_seed_cannot_take_over_the_whole_board(self):
        from .settings import MYCELIUM_CREEP_TIME
        cap = data.PLANTS["mycelium"]["spread_cap"]
        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium")] + [Plot() for _ in range(11)]
        run.rng.random = lambda: 0.0
        run.start_timer()
        for _ in range(40):
            for p in run.plots:
                p.creep_cd = 0.0
            run.update(MYCELIUM_CREEP_TIME)
        self.assertLessEqual(run.creep_grown[False], cap)
        self.assertLessEqual(
            len([p for p in run.plots if p.species == "mycelium"]), cap + 1,
        )

    def test_creep_does_nothing_before_the_clock_starts(self):
        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium")] + [Plot() for _ in range(11)]
        run.plots[0].creep_cd = 0.0
        for _ in range(200):
            run.update(0.5)
        self.assertEqual(len([p for p in run.plots if p.species == "mycelium"]), 1)

    def test_a_walled_in_mycelium_does_not_bank_creep(self):
        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium")] + [Plot("daisy") for _ in range(11)]
        run.start_timer()
        run.update(30.0)
        self.assertEqual(run.plots[0].creep_cd, 0.0)
        self.assertEqual(run.creep_grown[False], 0)

    def test_a_plot_carries_its_creep_meter_through_a_snapshot(self):
        restored = Plot.from_dict(Plot("mycelium", creep_cd=6.5).to_dict())
        self.assertEqual(restored.species, "mycelium")
        self.assertAlmostEqual(restored.creep_cd, 6.5)

    def test_mycelium_never_mutates(self):
        self.assertFalse(data.mutants_for("mycelium"))
        self.assertTrue(data.PLANTS["mycelium"].get("no_mutations"))
        run = self.run_with("mycelium")
        run.plots[0].harvests = 99
        for _ in range(200):
            run._maybe_mutate(0)
        self.assertEqual(run.plots[0].species, "mycelium")

    def test_the_creep_meter_belongs_to_the_patch_not_to_each_plot(self):
        """A wide patch must not grow one plot per member every creep cycle."""
        from .settings import MYCELIUM_CREEP_TIME

        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium") for _ in range(4)] + [Plot() for _ in range(8)]
        run.rng.random = lambda: 0.99             # no harvest luck at all
        run.start_timer()
        run.update(MYCELIUM_CREEP_TIME + 0.5)
        self.assertEqual(len([p for p in run.plots if p.species == "mycelium"]), 5,
                         "four connected plots bank one shared expansion, not four")
        self.assertEqual(run.creep_grown[False], 1)
        self.assertTrue(all(p.creep_cd < MYCELIUM_CREEP_TIME
                            for p in run.plots if p.species == "mycelium"),
                        "spreading resets the whole patch's meter")

    def test_one_seed_grows_at_most_its_spread_cap_in_a_round(self):
        from .settings import MYCELIUM_CREEP_TIME
        from .settings import ROUND_TIME

        cap = data.PLANTS["mycelium"]["spread_cap"]
        run = self.run_with()
        run.begin_round()
        run.plots = [Plot("mycelium")] + [Plot() for _ in range(11)]
        run.rng.random = lambda: 0.0             # every harvest roll spreads
        run.auto_harvest = True
        run.start_timer()
        run.update(ROUND_TIME)
        self.assertLessEqual(run.creep_grown[False], cap)
        self.assertLessEqual(len([p for p in run.plots if p.species == "mycelium"]), cap + 1)
        self.assertGreaterEqual(MYCELIUM_CREEP_TIME, 15.0,
                                "a guaranteed spread should be a slow, watchable clock")

    def test_a_full_mycelium_board_stays_below_the_paying_crops(self):
        """Regression for the round-4 millions: a board of mycelium was the best
        money in the game by a wide margin, thanks to a +35% patch bonus on top
        of a fast crop. It should now be a modest, comfortable earner."""
        from .settings import ROUND_TIME

        def round_income(species):
            run = Run(seed=1)
            run.round = 4
            run.twist_id = lambda _rnd=None: "none"
            run.begin_round()
            run.plots = [Plot(species) for _ in range(12)]
            run.auto_harvest = True
            run.start_timer()
            for _ in range(int(ROUND_TIME * 10)):    # step like the game loop
                run.update(0.1)
            return run.round_income

        mycelium = round_income("mycelium")
        pumpkin = round_income("pumpkin")
        self.assertLess(mycelium, pumpkin,
                        "a full mycelium board must not out-earn a full pumpkin board")
        self.assertGreater(mycelium, round_income("daisy"),
                           "mycelium should still beat the cheapest crop")
        self.assertLess(data.PLANTS["mycelium"]["network"], 0.25)
        self.assertLessEqual(data.PLANTS["mycelium"]["spread_cap"], 3)

    def test_mycelium_grows_in_the_garden_and_the_cellar(self):
        run = Run(seed=2)
        run.twist_id = lambda _rnd=None: "none"
        run.seeds = {"mycelium": 2}
        self.assertTrue(run.can_plant("mycelium", cellar=False))
        self.assertTrue(run.can_plant("mycelium", cellar=True))
        self.assertTrue(run.plant(0, "mycelium", cellar=False))
        self.assertTrue(run.plant(0, "mycelium", cellar=True))


class FlytrapTests(unittest.TestCase):
    def run_with(self, *species):
        run = Run(seed=4)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot(s) for s in species] + [Plot() for _ in range(12 - len(species))]
        return run

    def test_flytrap_harvests_feed_its_next_bite(self):
        run = self.run_with("venus_flytrap", "daisy")
        base = run.harvest_value(0)
        for _ in range(5):
            run._harvest(1)
        self.assertEqual(run.plots[0].fed, 5 * data.PLANTS["venus_flytrap"]["feed"])
        fed_value = run.harvest_value(0)
        self.assertGreater(fed_value, base)
        run._harvest(0)
        self.assertEqual(run.plots[0].fed, 0)
        self.assertEqual(run.harvest_value(0), base)

    def test_flytrap_pays_much_less_than_a_normal_plant_alone(self):
        self.assertLess(data.PLANTS["venus_flytrap"]["yield"], data.PLANTS["tomato"]["yield"])

    def test_maneater_eats_a_neighbour_and_keeps_half_its_base(self):
        man_eater = next(m for m in data.mutants_for("venus_flytrap") if data.PLANTS[m].get("consume"))
        run = self.run_with(man_eater, "pumpkin")
        before = run.harvest_value(0)
        run._harvest(0)
        self.assertIsNone(run.plots[1].species)
        self.assertAlmostEqual(run.plots[0].gorged, data.PLANTS["pumpkin"]["yield"] * 0.5)
        self.assertGreater(run.harvest_value(0), before)
        self.assertTrue(any(ev["kind"] == "devour" for ev in run.events))

    def test_maneater_only_takes_orthogonal_neighbours(self):
        man_eater = next(m for m in data.mutants_for("venus_flytrap") if data.PLANTS[m].get("consume"))
        run = Run(seed=4)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot() for _ in range(12)]
        run.plots[0] = Plot(man_eater)
        far = 0
        for n in range(12):
            if n not in run.neighbours(0) and n != 0:
                run.plots[n] = Plot("daisy")
                far += 1
        run._harvest(0)
        self.assertEqual(run.plots[0].gorged, 0)
        self.assertEqual(sum(1 for p in run.plots if p.species == "daisy"), far)

    def test_flytrap_eats_nearby_critters(self):
        import types
        from . import ambient
        from .settings import CRITTER_FEED_VALUE

        run = self.run_with("venus_flytrap")
        run.twist_id = lambda _rnd=None: "none"
        run.phase = "round"
        run.finished = False
        manager = ambient.GardenAmbient(run)
        critter = types.SimpleNamespace(
            species="ant", x=32.0, y=55.0, away=0.0, offscreen=False,
            _leave_for_a_while=lambda _rng: None,
        )
        manager.critters = [critter]
        manager.flytrap_cd.clear()
        manager._feed_flytraps(0.1, run, plot_rects=[(10, 40, 50, 30)])
        self.assertEqual(run.plots[0].fed, CRITTER_FEED_VALUE)
        self.assertTrue(any(e["kind"] == "critter_eaten" for e in run.events))
        self.assertIn((False, 0), manager.flytrap_cd)

class CloverTests(unittest.TestCase):
    def run_with(self, *species):
        run = Run(seed=5)
        run.twist_id = lambda _rnd=None: "none"
        run.plots = [Plot(s) for s in species] + [Plot() for _ in range(12 - len(species))]
        return run

    def test_clover_pays_nothing_itself(self):
        run = self.run_with("four_leaf_clover")
        self.assertEqual(run.harvest_value(0), 0)
        run.money = 0
        run._harvest(0)
        self.assertEqual(run.money, 0)

    def test_clover_can_lift_a_neighbours_base_harvest(self):
        run = self.run_with("four_leaf_clover", "pumpkin")
        before = run.harvest_value(1)
        run.rng.random = lambda: 0.0           # always lucky
        run._harvest(0)
        self.assertAlmostEqual(run.plots[1].bloom, 1.5)
        self.assertGreater(run.harvest_value(1), before)
        self.assertTrue(any(ev["kind"] == "bloom" for ev in run.events))

    def test_clover_never_buffs_another_clover(self):
        run = self.run_with("four_leaf_clover", "four_leaf_clover")
        run.rng.random = lambda: 0.0
        run._harvest(0)
        self.assertEqual(run.plots[1].bloom, 1.0)
        self.assertEqual(run.plots[0].bloom, 1.0)

    def test_the_mutant_is_the_five_leaf_clover(self):
        # The one and only: no second clover mutation sits beside it.
        self.assertEqual(data.mutants_for("four_leaf_clover"), ["five_leaf_clover"])
        self.assertEqual(data.PLANTS["five_leaf_clover"]["name"], "Five-Leaf Clover")

    def test_a_clover_can_only_ever_mutate_into_the_five_leaf_clover(self):
        threshold = data.mutation_threshold("four_leaf_clover")
        # Mid-round, once it has been harvested enough...
        run = self.run_with("four_leaf_clover")
        grown = set()
        for _ in range(2000):
            run.plots[0] = Plot("four_leaf_clover", harvests=threshold)
            run._maybe_mutate(0)
            grown.add(run.plots[0].species)
        self.assertEqual(grown, {"four_leaf_clover", "five_leaf_clover"})
        # ...and straight from the seed with the Mutagen relic.
        run = self.run_with()
        run.relics = ["mutagen"]
        sprouted = set()
        for _ in range(2000):
            run.plots[0] = Plot()
            run.seeds["four_leaf_clover"] = 1
            self.assertTrue(run.plant(0, "four_leaf_clover"))
            sprouted.add(run.plots[0].species)
        self.assertEqual(sprouted, {"four_leaf_clover", "five_leaf_clover"})

    def test_the_five_leaf_clover_is_nothing_but_a_clover_mutation(self):
        five = data.PLANTS["five_leaf_clover"]
        self.assertTrue(five["mutant"])
        self.assertEqual(five["base"], "four_leaf_clover")
        # Only the Four-Leaf Clover turns into it, and it mutates no further.
        self.assertEqual(
            [sid for sid in data.PLANTS if "five_leaf_clover" in data.mutants_for(sid)],
            ["four_leaf_clover"])
        self.assertEqual(data.mutants_for("five_leaf_clover"), [])
        # It has no seed of its own: on no shelf and in no pack, so a run can
        # only reach it by growing a Four-Leaf Clover.
        self.assertNotIn("five_leaf_clover", data.PLANT_ORDER)
        self.assertNotIn("five_leaf_clover", data.CELLAR_PLANTS)
        for kind, pack in data.PACKS.items():
            self.assertNotIn("five_leaf_clover", pack["pool"], kind)

    def test_a_save_that_remembers_the_retired_shamrock_still_loads(self):
        # "Lucky Shamrock" used to be a second clover mutation. Saves that
        # counted its harvests must load cleanly now that it is gone.
        self.assertIsNone(data.PLANTS.get("four_leaf_clover_shamrock"))
        saved = Run(seed=5).to_dict()
        saved["mastery"] = {"four_leaf_clover_shamrock": 7, "four_leaf_clover": 3}
        saved["seeds"] = {"four_leaf_clover_shamrock": 2, "four_leaf_clover": 1}
        saved["plots"] = [Plot("four_leaf_clover").to_dict()]
        saved["plots"][0]["species"] = "four_leaf_clover_shamrock"
        loaded = Run.from_dict(saved)
        self.assertEqual(loaded.mastery, {"four_leaf_clover": 3})
        self.assertEqual(loaded.seeds, {"four_leaf_clover": 1})
        self.assertIsNone(loaded.plots[0].species)


class RelicEvolutionFixTests(unittest.TestCase):
    """Evolved Scarecrow and Spore Lantern have to get better, not worse."""

    def test_scarecrow_evolution_reaches_x2_25(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["scarecrow"]
        run.plots = [Plot("pumpkin")]
        plain = run.harvest_value(0)
        run.counters["harvest"] = 400
        self.assertEqual(run.relic_level("scarecrow"), 1)
        evolved = run.harvest_value(0)
        self.assertGreater(evolved, plain)
        self.assertAlmostEqual(evolved / data.PLANTS["pumpkin"]["yield"], 2.25, places=1)
        self.assertGreater(evolved, plain * 1.4)

    def test_spore_lantern_evolution_reaches_x4(self):
        run = Run(seed=1)
        run.twist_id = lambda _rnd=None: "none"
        run.relics = ["spore_lantern"]
        run.cellar_unlocked = True
        run.cellar_plots[0] = Plot("brown_mushroom")
        base = data.PLANTS["brown_mushroom"]["yield"]
        self.assertEqual(run.harvest_value(0, cellar=True), base * 2)
        run.counters["mushroom"] = 300
        self.assertEqual(run.relic_level("spore_lantern"), 2)
        self.assertEqual(run.harvest_value(0, cellar=True), base * 4)
        from .settings import CELLAR_SPEED
        self.assertGreater(run.plot_growth_speed(0, cellar=True), CELLAR_SPEED)

    def test_evolved_relics_still_emit_one_toast(self):
        run = Run(seed=1)
        run.relics = ["scarecrow"]
        run.counters["harvest"] = 400
        run.refresh_relic_levels()
        events = [ev for ev in run.events if ev["kind"] == "evolve"]
        self.assertEqual(len(events), 1)
        self.assertIn("2.25", events[0]["desc"])

        class SpritePreviewTests(unittest.TestCase):
            """preview_sprites.py is only worth having if it shows what the game shows."""

    def test_preview_draws_every_sprite_and_recolour_exactly_as_the_game_does(self):
        import pygame
        from types import SimpleNamespace
        from unittest import mock
        from . import gfx, preview_sprites
        from .round import RoundScene, CELL_W, CELL_H
        pygame.init()
        pygame.display.set_mode((1, 1))
        app = SimpleNamespace(run=Run(seed=5), mouse=(319, 179), toast=lambda *args: None, save_run=lambda: None)
        scene = RoundScene(app)
        scene.on_enter()

        def on_a_plot(species):
            """The sprite and the recolour the round screen asks for when `species` is ripe."""
            app.run.plots = [Plot(species, progress=data.PLANTS[species]["grow"])]
            with mock.patch.object(gfx, "draw_sprite") as draw:
                scene.draw_plot(app.run.plots, pygame.Surface((CELL_W, CELL_H)), 0, 0, 0, CELL_W, CELL_H)
            return draw.call_args_list[0].args[1], draw.call_args_list[0].args[5]

        art = preview_sprites.load()
        names = list(art.grids) + list(data.PLANTS)
        for name in names + ["no_such_sprite"]:
            grid_name, subs = on_a_plot(name) if name in data.PLANTS else (name, None)
            self.assertEqual(preview_sprites.lookup(art, name), (grid_name, subs), name)
            for scale in (1, 2):
                self.assertEqual(
                    pygame.image.tobytes(preview_sprites.render(art, name, scale), "RGBA"),
                    pygame.image.tobytes(gfx.sprite(grid_name, scale, subs), "RGBA"), name)
        # None of the game's own art trips the checks.
        self.assertEqual(preview_sprites.report(art, names), [])

    def test_preview_points_out_the_mistakes_a_hand_typed_grid_invites(self):
        import pygame
        from . import preview_sprites
        from .settings import BAD
        art = preview_sprites.load()
        daisy = list(art.grids["daisy"])
        art.grids["no_comma"] = daisy[:3] + [daisy[3] + daisy[4]] + daisy[5:]  # two rows run together
        art.grids["short_row"] = daisy[:6] + [daisy[6][:-1]] + daisy[7:]
        art.grids["typo"] = daisy[:6] + ["?" + daisy[6][1:]] + daisy[7:]
        art.grids["daisy"] = daisy + daisy[:1]  # a plant's sprite with a thirteenth row
        art.palette["q"] = (300, 0, 0)
        art.grids["bad_colour"] = daisy[:6] + ["q" + daisy[6][1:]] + daisy[7:]
        art.plants["bluebell"] = {"name": "Bluebell"}  # a plant added to data.py before its sprite is drawn
        names = ["no_comma", "short_row", "typo", "daisy", "daisey", "bad_colour", "bluebell", "sunflower"]
        said = {name: " / ".join(preview_sprites.problems(art, name)) for name in names}
        self.assertIn("row 4 is 24 wide, the others are 12", said["no_comma"])
        self.assertIn("comma", said["no_comma"])
        self.assertIn("row 7 is 11 wide, the others are 12", said["short_row"])
        self.assertNotIn("comma", said["short_row"])
        self.assertIn("row 7 uses '?'", said["typo"])
        self.assertIn("12x13", said["daisy"])
        self.assertIn("did you mean daisy", said["daisey"])
        self.assertIn("uses 'q', but its colour is (300, 0, 0)", said["bad_colour"])
        self.assertIn("there is no sprite called 'bluebell'", said["bluebell"])
        self.assertNotIn("did you mean bluebell", said["bluebell"])
        self.assertEqual(said["sunflower"], "")
        # The picture is still drawn, with a mark on each cell where the game would have crashed.
        for name in ("typo", "bad_colour"):
            self.assertEqual(tuple(preview_sprites.render(art, name, 1).get_at((0, 6)))[:3], preview_sprites.STRAY)

        def red(surface):
            return pygame.mask.from_threshold(surface, BAD, (1, 1, 1, 255)).count()

        # Red is kept for trouble: the name over a sprite that has some, and the messages above the cards.
        pygame.font.init()
        face = pygame.font.Font(None, preview_sprites.TEXT_SIZE)
        self.assertEqual(red(preview_sprites.compose(art, ["sunflower"], 2, 900)), 0)
        flagged = red(preview_sprites.card(art, "typo", 2, face))
        self.assertGreater(flagged, 0)
        self.assertGreater(red(preview_sprites.compose(art, ["typo"], 2, 900)), flagged)
        self.assertGreater(preview_sprites.compose(art, names, 2, 900).get_height(), 0)

    def test_preview_follows_the_files_as_they_are_saved(self):
        import os
        import shutil
        import tempfile
        from pathlib import Path
        from unittest import mock
        import pygame
        from . import preview_sprites
        with tempfile.TemporaryDirectory() as folder:
            for name in preview_sprites.WATCHED:
                shutil.copy(str(preview_sprites.FOLDER / name), folder)
            sprites = Path(folder) / "sprites_data.py"
            original = sprites.read_text(encoding="utf-8")
            start = original.index('"daisy": [')
            end = original.index("]", start)
            repainted = original[:start] + original[start:end].replace("w", "r") + original[end:]
            preview = preview_sprites.Preview(["daisy"], 2, folder)
            saved_at = [os.stat(str(sprites)).st_mtime_ns]

            def save(text):
                """Save the file the way an editor would, then look at it twice as the window does."""
                sprites.write_text(text, encoding="utf-8")
                saved_at[0] += 10 ** 10  # a later timestamp even where the clock is coarse
                os.utime(str(sprites), ns=(saved_at[0], saved_at[0]))
                return preview.update(), preview.update()

            def petals():
                return set("".join(preview.art.grids["daisy"][1:7])) - set(".y")

            def looks():
                return pygame.image.tobytes(preview.picture(), "RGB")

            before = looks()
            self.assertEqual(petals(), {"w"})
            self.assertFalse(preview.update())  # nothing was saved, so there is nothing to redraw
            # The first look after a save only notes it; the second, finding it settled, redraws.
            self.assertEqual(save(repainted), (False, True))
            self.assertEqual(petals(), {"r"})
            self.assertNotEqual(looks(), before)
            self.assertEqual(preview.messages(), [])
            # A half-typed edit keeps the last good picture up and says where the file broke.
            self.assertEqual(save(original[:end] + '"' + original[end:]), (False, True))
            self.assertIn("sprites_data.py, line", preview.error)
            self.assertEqual(petals(), {"r"})
            self.assertEqual(preview.messages(), [preview.error])
            self.assertGreater(len(looks()), len(before))  # the sheet grew by the red lines
            # So does a file that runs but leaves no sprites to draw.
            self.assertEqual(save(original + "\nGRIDS = None\n"), (False, True))
            self.assertIn("still showing the last version that loaded", preview.error)
            self.assertEqual(petals(), {"r"})
            self.assertGreater(len(looks()), len(before))
            # Putting the file right clears the message.
            self.assertEqual(save(original), (False, True))
            self.assertEqual((preview.error, petals()), ("", {"w"}))
            self.assertEqual(looks(), before)
            # Saving again with nothing drawn differently is not worth a redraw.
            self.assertEqual(save(original + "\n# a note to self\n"), (False, False))
            # A file that cannot be opened at the moment it is looked at gets another go, with no new save needed.
            with mock.patch.object(preview_sprites, "read", side_effect=PermissionError("in use")):
                self.assertEqual(save(repainted), (False, True))
            self.assertEqual(preview.error.split(" - ")[0], "PermissionError: in use")
            self.assertEqual(petals(), {"w"})
            self.assertEqual((preview.update(), preview.update()), (False, True))
            self.assertEqual((preview.error, petals()), ("", {"r"}))
            self.assertEqual((preview.update(), preview.update()), (False, False))

    def test_preview_writes_a_picture_without_opening_a_window(self):
        import contextlib
        import io
        import os
        import tempfile
        from unittest import mock
        import pygame
        from . import preview_sprites
        from .sprites_data import GRIDS
        with tempfile.TemporaryDirectory() as folder:
            target = os.path.join(folder, "sheets", "clover")  # no ".png", in a folder that is not there yet
            complaints = io.StringIO()
            no_window = mock.patch("pygame.display.set_mode", side_effect=AssertionError("a window was opened"))
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(complaints), no_window:
                self.assertEqual(preview_sprites.main(["five_leaf_clover", "--png", target, "--scale", "3"]), 0)
                pixels = pygame.image.tobytes(pygame.image.load(target + ".png"), "RGB")
                self.assertEqual(preview_sprites.main(["five_leaf_clovr", "--png", target]), 1)
            self.assertIn("did you mean five_leaf_clover", complaints.getvalue())
        # Every gold leaf rim cell is there twice: at 2x and at 1x, three screen pixels to the game pixel.
        gold = bytes(data.PLANTS["five_leaf_clover"]["subs"]["l"])
        rims = sum(row.count("l") for row in GRIDS["five_leaf_clover"])
        self.assertEqual(
            sum(pixels[i:i + 3] == gold for i in range(0, len(pixels), 3)), rims * (6 * 6 + 3 * 3))

    def test_preview_window_takes_keys_and_closes(self):
        from unittest import mock
        import pygame
        from . import preview_sprites
        self.addCleanup(pygame.display.quit)
        for closing in (pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE), pygame.event.Event(pygame.QUIT)):
            preview = preview_sprites.Preview(["daisy"], 2)
            frames = []

            def flip():
                """Stand in for the screen update: keep what was drawn, then press the next key."""
                frames.append(pygame.image.tobytes(pygame.display.get_surface(), "RGB"))
                if len(frames) == 1:
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_g))
                elif len(frames) == 2:
                    pygame.event.post(closing)
                elif len(frames) > 5:
                    raise AssertionError("the window stayed open after %s" % closing)

            pygame.display.init()
            pygame.event.clear()
            with mock.patch("pygame.display.flip", flip):
                preview_sprites.watch(preview)
            # One frame as it opens, one with the pixel grid G asked for, and none once it is closed.
            self.assertEqual(len(frames), 2)
            self.assertNotEqual(frames[0], frames[1])
            self.assertTrue(preview.grid)
            self.assertFalse(pygame.display.get_init())


class SpritePreviewLayoutTests(unittest.TestCase):
    """One outsized portrait must not push every other sprite a screen apart."""

    def test_a_large_portrait_gets_its_own_rows_instead_of_inflating_every_cell(self):
        import pygame
        from . import preview_sprites
        pygame.font.init()
        art = preview_sprites.load()
        names = list(art.grids)
        self.assertIn("moss", names)

        usual = preview_sprites.usual_tile(art, names)
        self.assertTrue(preview_sprites.is_outsized(art, "moss", usual))
        self.assertFalse(preview_sprites.is_outsized(art, "daisy", usual))

        sheet = preview_sprites.compose(art, names, 3, 1280)
        without_portrait = preview_sprites.compose(
            art, [name for name in names if name != "moss"], 3, 1280)
        # Moss used to set the shared cell size: one card per row, 113 rows tall.
        # It now adds a single row of its own below the same tight grid.
        self.assertEqual(sheet.get_width(), without_portrait.get_width())
        self.assertLess(sheet.get_height(), without_portrait.get_height() * 2)
        self.assertGreater(sheet.get_height(), without_portrait.get_height())
        # Asking for the portrait by itself is still a normal, drawable sheet.
        alone = preview_sprites.compose(art, ["moss"], 3, 1280)
        self.assertGreater(alone.get_height(), 0)


if __name__ == "__main__":
    unittest.main()


def hazard_round(twist_id, seed=3, species="daisy", plots=1, cellar=False, relics=()):
    """A running round under `twist_id`, with `plots` daisies on the surface.

    The clock is 40s so every hazard period fires at least once inside a single
    `update` call, and the plot list keeps its four starting plots so tests can
    talk about empty neighbours.
    """
    run = Run(seed=seed)
    run.twist_id = lambda _rnd=None: twist_id
    run.relics = list(relics)
    run.begin_round()
    run.cellar_unlocked = True
    run.time_total = run.time_left = 40.0
    for i in range(plots):
        run.plots[i] = Plot(species)
    if cellar:
        run.cellar_plots[0] = Plot("brown_mushroom")
    run.start_timer()
    return run


@contextmanager
def rig(run, value=0.5, target=0):
    """Force a random-target hazard to hit plot `target` and roll `value`."""
    with patch.object(run.rng, "randrange", return_value=target), \
            patch.object(run.rng, "random", return_value=value):
        yield


class DiseaseTests(unittest.TestCase):
    def test_a_crop_sickens_on_the_period_and_grows_slow(self):
        run = hazard_round("disease", plots=1)
        with patch.object(run.rng, "random", return_value=1.0):
            run.update(14.9)
            self.assertEqual(run.diseased_count(), 0)
            run.update(0.3)
            self.assertEqual(run.diseased_count(), 1)
        self.assertTrue(run.plots[0].sick)

        # Same elapsed clock, same crop, no rot: the sick one must lag behind.
        healthy = hazard_round("none", plots=1)
        run.plots[0].progress = healthy.plots[0].progress = 0.0
        with patch.object(run.rng, "random", return_value=1.0):
            run.update(1.0)
            healthy.update(1.0)
        self.assertLess(run.plots[0].progress, healthy.plots[0].progress)
        self.assertAlmostEqual(
            run.plot_growth_speed(0) / healthy.plot_growth_speed(0), DISEASE_GROWTH, places=4)

    def test_sick_crops_pay_less_at_harvest_and_at_the_buzzer(self):
        run = hazard_round("disease", plots=1)
        clean = hazard_round("none", plots=1)
        run.plots[0].sick = True
        run.plots[0].progress = clean.plots[0].progress = data.PLANTS["daisy"]["grow"]
        self.assertEqual(run.harvest_value(0), max(1, int(clean.harvest_value(0) * DISEASE_YIELD + 0.5)))
        # Checked before the liquidation, which clears the plot's flags with it.
        self.assertAlmostEqual(run.hazard_sale_mult(run.plots[0]), DISEASE_SALE, places=6)
        self.assertEqual(clean.hazard_sale_mult(clean.plots[0]), 1.0)
        run.money = clean.money = 0
        run.end_round()
        clean.end_round()
        self.assertLess(run.money, clean.money)

    def test_disease_walks_plot_to_plot_and_not_across_a_gap(self):
        run = hazard_round("disease", seed=11, plots=2)
        run.plots[0].sick = True
        with patch.object(run.rng, "random", return_value=0.0):
            self.assertEqual(run._disease_spread(), 1)
        self.assertTrue(run.plots[1].sick)

        gap = hazard_round("disease", seed=11, plots=3)
        gap.plots[0].sick = True
        gap.plots[1] = Plot()          # the empty plot in the middle
        with patch.object(gap.rng, "random", return_value=0.0):
            self.assertEqual(gap._disease_spread(), 0)
        self.assertFalse(gap.plots[2].sick)

    def test_one_roll_per_sick_plant_even_with_several_neighbours(self):
        run = hazard_round("disease", seed=5, plots=4)
        run.plots[1].sick = True
        for i in (0, 2, 3):
            run.plots[i] = Plot("daisy")
        # Above CONTAGION_CHANCE, and nothing catches it despite three neighbours.
        with patch.object(run.rng, "random", return_value=CONTAGION_CHANCE + 0.2):
            self.assertEqual(run._disease_spread(), 0)
        with patch.object(run.rng, "random", return_value=CONTAGION_CHANCE - 0.2):
            self.assertEqual(run._disease_spread(), 1)
            self.assertEqual(run.diseased_count(), 2)

    def test_the_shovel_is_the_only_cure(self):
        run = hazard_round("disease", plots=1)
        plot = run.plots[0]
        plot.sick = True
        plot.progress = data.PLANTS["daisy"]["grow"]
        self.assertTrue(run.harvest(0))
        self.assertTrue(plot.sick, "harvesting must not quietly cure a crop")
        ok, _ = run.remove_plant(0)
        self.assertTrue(ok)
        self.assertFalse(plot.sick)
        self.assertIsNone(plot.species)
        self.assertEqual([e["kind"] for e in run.events if e["kind"] == "cured"], ["cured"])

        run.seeds["daisy"] = 1
        self.assertTrue(run.plant(0, "daisy"))
        self.assertFalse(run.plots[0].sick, "dug soil comes back clean")

    def test_the_cellar_is_insulated(self):
        run = hazard_round("disease", plots=1, cellar=True)
        with patch.object(run.rng, "random", return_value=0.0):
            run.update(40.0)
        self.assertTrue(all(not p.sick for p in run.cellar_plots))
        self.assertTrue(run.cellar_plots[0].species)
        self.assertTrue(run.plots[0].sick, "the surface crop is the one that caught it")

    def test_sulphur_duster_softens_the_penalty_and_the_spread(self):
        plain = hazard_round("disease", plots=2)
        duster = hazard_round("disease", plots=2, relics=["sulphur_duster"])
        for run in (plain, duster):
            run.plots[0].sick = True
        self.assertGreater(duster.plot_growth_speed(0), plain.plot_growth_speed(0))
        self.assertGreater(duster.harvest_value(0), plain.harvest_value(0))
        self.assertLess(plain.disease_factors()[0], 1.0)
        # Relief of 0.5 pulls every penalty halfway back, no further.
        self.assertAlmostEqual(duster.disease_factors()[0], 1.0 - (1.0 - DISEASE_GROWTH) * 0.5, places=6)

        roll = CONTAGION_CHANCE - 0.05
        with patch.object(plain.rng, "random", return_value=roll):
            self.assertEqual(plain._disease_spread(), 1)
        with patch.object(duster.rng, "random", return_value=roll):
            self.assertEqual(duster._disease_spread(), 0, "the duster should eat a borderline roll")


class MeteorTests(unittest.TestCase):
    def test_a_strike_on_a_crop_either_flattens_or_starlights_it(self):
        doomed = hazard_round("meteor_shower", plots=1)
        with rig(doomed, value=0.0):
            doomed._meteor_strike()
        self.assertIsNone(doomed.plots[0].species)
        self.assertFalse(doomed.plots[0].starlit)
        self.assertIn("meteor", [e["kind"] for e in doomed.events])

        lucky = hazard_round("meteor_shower", plots=1)
        with rig(lucky, value=METEOR_DESTROY + 0.4):
            lucky._meteor_strike()
        self.assertTrue(lucky.plots[0].species, "a crop survives a lucky strike")
        self.assertTrue(lucky.plots[0].starlit)

    def test_a_starlit_crop_is_fifty_percent_better(self):
        plain = hazard_round("none", plots=1)
        star = hazard_round("none", plots=1)
        star.plots[0].starlit = True
        self.assertAlmostEqual(star.harvest_value(0) / plain.harvest_value(0), METEOR_BONUS, places=4)
        plain.plots[0].progress = star.plots[0].progress = data.PLANTS["daisy"]["grow"]
        plain.money = star.money = 0
        plain.end_round()
        star.end_round()
        self.assertGreater(star.money, plain.money)

    def test_a_strike_rewrites_the_species_when_it_can(self):
        run = hazard_round("meteor_shower", plots=1, species="daisy")
        with rig(run, value=1.0):
            run._meteor_strike()
        self.assertNotEqual(run.plots[0].species, "daisy")
        self.assertTrue(data.PLANTS[run.plots[0].species].get("mutant"))

    def test_a_crop_that_cannot_mutate_still_gets_the_bonus(self):
        run = hazard_round("meteor_shower", plots=1, species="crystal_bloom")
        self.assertTrue(data.PLANTS["crystal_bloom"].get("no_mutations"))
        with rig(run, value=1.0):
            run._meteor_strike()
        self.assertEqual(run.plots[0].species, "crystal_bloom")
        self.assertTrue(run.plots[0].starlit)

    def test_stardust_survives_planting_and_is_spent_by_it(self):
        run = hazard_round("meteor_shower", plots=0)
        with rig(run, value=1.0):
            self.assertTrue(run._meteor_strike())
        self.assertTrue(run.plots[0].starlit)
        self.assertIsNone(run.plots[0].species)

        run.seeds["daisy"] = 2
        self.assertTrue(run.plant(0, "daisy"))
        self.assertTrue(run.plots[0].starlit, "the dust has to reach the crop, not just the soil")
        self.assertIn("stardust", [e["kind"] for e in run.events])

        run.remove_plant(0)
        self.assertFalse(run.plots[0].starlit, "shovelling sweeps the plot clean")
        self.assertTrue(run.plant(0, "daisy"))
        self.assertFalse(run.plots[0].starlit)

    def test_a_strike_on_a_weedy_plot_digs_it_out_for_free(self):
        run = hazard_round("meteor_shower", plots=0)
        run.plots[0].weed = True
        with rig(run, value=1.0):
            run._meteor_strike()
        self.assertFalse(run.plots[0].weed)
        self.assertFalse(run.plots[0].starlit)

    def test_a_strike_on_a_full_garden_still_lands_somewhere(self):
        run = hazard_round("meteor_shower", plots=4)
        with patch.object(run.rng, "random", return_value=1.0):
            run.update(10.1)
        self.assertEqual(sum(1 for p in run.plots if p.starlit), 1)

    def test_lightning_rod_removes_the_downside(self):
        run = hazard_round("meteor_shower", plots=1, relics=["lightning_rod"])
        with rig(run, value=0.0):
            run._meteor_strike()
        self.assertTrue(run.plots[0].species)
        self.assertTrue(run.plots[0].starlit)

    def test_meteors_only_land_on_the_surface(self):
        run = hazard_round("meteor_shower", plots=1, cellar=True)
        with rig(run, value=0.0):
            for _ in range(8):
                run._meteor_strike()
        self.assertTrue(run.cellar_plots[0].species)
        self.assertFalse(any(p.starlit or p.sick for p in run.cellar_plots))


class WeedTests(unittest.TestCase):
    def test_empty_plots_get_choked_on_the_period(self):
        run = hazard_round("weeds", plots=1)
        with patch.object(run.rng, "random", return_value=1.0):
            run.update(WEED_PERIOD + 0.01)
        self.assertEqual(run.weedy_count(), 1)
        self.assertFalse(run.plots[0].weed, "a planted plot is not a weed's target")

    def test_weedy_soil_refuses_a_seed_but_digs_clear(self):
        run = hazard_round("weeds", plots=1)
        run.plots[1].weed = True
        run.seeds["daisy"] = 2
        self.assertFalse(run.plant(1, "daisy"))
        self.assertEqual(run.seeds["daisy"], 2, "the seed stays in the tray")
        self.assertTrue(run.clear_weeds(1))
        self.assertFalse(run.plots[1].weed)
        self.assertTrue(run.plant(1, "daisy"))

    def test_a_shovelled_weed_reports_clean_soil(self):
        run = hazard_round("weeds", plots=0)
        run.plots[2].weed = True
        ok, msg = run.remove_plant(2)
        self.assertTrue(ok)
        self.assertIn("weeds", msg.lower())
        self.assertIn("weed_clear", [e["kind"] for e in run.events])

    def test_weeds_seed_their_own_neighbours(self):
        run = hazard_round("weeds", plots=0)
        run.plots[1].weed = True
        with patch.object(run.rng, "random", return_value=0.0):
            run._sprout_weed()
        self.assertTrue(run.plots[0].weed or run.plots[2].weed, "a weed spreads sideways")

    def test_left_weeds_are_billed_at_the_buzzer(self):
        run = hazard_round("weeds", plots=1)
        run.money = 500
        for i in (1, 2):
            run.plots[i].weed = True
        run.end_round()
        self.assertEqual(run.last_summary["weeds"], 2)
        self.assertEqual(run.last_summary["weed_fee"], 2 * WEED_FEE)
        self.assertEqual(run.money, 500 - 2 * WEED_FEE)

    def test_a_full_garden_never_weeds(self):
        run = hazard_round("weeds", plots=4)
        self.assertFalse(run._sprout_weed())

    def test_the_cellar_needs_no_weeding(self):
        run = hazard_round("weeds", plots=1, cellar=True)
        self.assertFalse(run.clear_weeds(0, cellar=True))
        self.assertFalse(run.plot_is_weedy(0, cellar=True))
        with patch.object(run.rng, "random", return_value=0.0):
            run.update(40.0)
        self.assertTrue(all(not p.weed for p in run.cellar_plots))


class AphidTests(unittest.TestCase):
    def test_a_colony_halves_the_harvest_until_it_is_watered(self):
        run = hazard_round("aphids", plots=1)
        plot = run.plots[0]
        plot.progress = data.PLANTS["daisy"]["grow"]
        clean = run.harvest_value(0)
        plot.aphids = True
        self.assertEqual(run.harvest_value(0), max(1, int(clean * APHID_YIELD + 0.5)))
        self.assertTrue(run.water(0))
        self.assertFalse(plot.aphids)
        self.assertIn("aphid_wash", [e["kind"] for e in run.events])
        self.assertEqual(run.harvest_value(0), clean)

    def test_aphids_settle_on_one_more_crop_at_a_time(self):
        run = hazard_round("aphids", seed=8, plots=3)
        run.plots[0].aphids = True
        with patch.object(run.rng, "random", return_value=1.0):
            self.assertTrue(run._aphid_colony())
        self.assertEqual(sum(1 for p in run.plots if p.aphids), 2)

    def test_watering_is_the_answer_even_for_an_auto_watered_garden(self):
        # A Hired Gardener soaks plots on its own, so the colony never survives
        # a full watering cycle - the relic is an answer, not a second problem.
        run = hazard_round("aphids", plots=1, relics=["gardener"])
        run.plots[0].aphids = True
        run.update(5.0)
        self.assertFalse(run.plots[0].aphids)
        self.assertGreater(run.counters["water"], 0)

    def test_aphids_shorten_the_end_of_round_sale(self):
        run = hazard_round("aphids", plots=1)
        clean = hazard_round("none", plots=1)
        run.plots[0].progress = clean.plots[0].progress = data.PLANTS["daisy"]["grow"]
        run.plots[0].aphids = True
        run.money = clean.money = 0
        run.end_round()
        clean.end_round()
        self.assertLess(run.money, clean.money)


class HazardRosterTests(unittest.TestCase):
    def test_the_four_hazards_are_reachable_and_described(self):
        reachable = set(data.RANDOM_TWISTS) | set(data.MINOR_TWISTS) | set(data.BOSS_TWISTS)
        for tid in ("disease", "meteor_shower", "weeds", "aphids"):
            with self.subTest(twist=tid):
                self.assertIn(tid, reachable)
                twist = data.TWISTS[tid]
                self.assertEqual(twist["growth"], 1.0)
                self.assertEqual(twist["yield"], 1.0)
                self.assertEqual(twist["time"], 0)
                self.assertIsNone(twist["ban"])
                self.assertTrue(twist["desc"])
                self.assertTrue(twist["short"])
                self.assertTrue(twist.get("lore"), "a hazard without a story hint is a bug")

    def test_the_new_bosses_land_at_the_end_of_the_roster(self):
        # Appending keeps every existing round number on the boss it already had,
        # so a saved run's forecast cannot shift underneath the player.
        self.assertEqual(data.BOSS_TWISTS[:8], [
            "crow_swarm", "hailstorm", "ghost", "queen_bee",
            "root_rot", "heatwave", "eternal_night", "gale",
        ])
        self.assertEqual(data.BOSS_TWISTS[-2:], ["disease", "meteor_shower"])
        self.assertEqual(Run(seed=1).twist_id(9), "crow_swarm")

    def test_hazards_only_run_while_the_twist_is_the_forecast(self):
        run = hazard_round("none", plots=2)
        run.plots[0].sick = True
        with patch.object(run.rng, "random", return_value=0.0):
            run.update(40.0)
        self.assertEqual(run.weedy_count(), 0)
        self.assertEqual(sum(1 for p in run.plots if p.aphids), 0)

    def test_clear_skies_freezes_a_hazard_round(self):
        # Clear Skies removes the forecast, not what the forecast already did -
        # the crops it infected stay infected. This pins that the *ticking* stops.
        run = hazard_round("disease", plots=4, seed=9, relics=["clear_skies"])
        with patch.object(run.rng, "random", return_value=0.0):
            run.update(16.0)
            self.assertGreaterEqual(run.diseased_count(), 1)
            run.update(5.0)          # crosses halfway, where the roll is made
            self.assertTrue(run.weather_cleared)
            frozen = run.diseased_count()
            run.update(18.0)
            self.assertEqual(run.diseased_count(), frozen)

    def test_every_plot_flag_survives_the_save_round_trip(self):
        plot = Plot("daisy", sick=True, aphids=True, starlit=True)
        back = Plot.from_dict(plot.to_dict())
        self.assertEqual((back.sick, back.aphids, back.starlit, back.weed), (True, True, True, False))

    def test_the_new_relics_are_pure_counterplay(self):
        from .sprites_data import GRIDS

        for rid, keys in (("sulphur_duster", ("disease_resist", "sick_relief")),
                          ("lightning_rod", ("rod_protects",))):
            with self.subTest(relic=rid):
                relic = data.RELICS[rid]
                self.assertEqual(sorted(relic["effects"]), sorted(keys))
                self.assertTrue(relic["lore"])
                self.assertIn(rid, GRIDS)
                run = hazard_round("none", plots=1, relics=[rid])
                self.assertAlmostEqual(run.growth_speed(), 1.0)
                self.assertEqual(run.harvest_value(0), hazard_round("none", plots=1).harvest_value(0))

    def test_hazard_penalties_are_ordered_the_documented_way(self):
        # Aphids are the milder hazard at the buzzer than in the hand, and Disease
        # is the only one that also slows growth: this pins the intent, so a
        # retune has to be a decision rather than a typo in `settings.py`.
        self.assertLess(APHID_YIELD, 1.0)
        self.assertLess(APHID_SALE, 1.0)
        self.assertGreater(APHID_SALE, APHID_YIELD)
        self.assertLess(DISEASE_SALE, 1.0)
        self.assertLess(DISEASE_GROWTH, 1.0)
        self.assertEqual(WEED_FEE, 6)
        self.assertEqual(METEOR_BONUS, 1.5)


class RoundSceneHazardTests(unittest.TestCase):
    """The draw path for hazard states, because a bad rect is a crash not a typo."""

    def setUp(self):
        import pygame

        pygame.init()
        pygame.display.set_mode((1, 1))
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"BLOOM_SAVE_DIR": self.tmp.name})
        self.env.start()
        from .app import App

        self.app = App()
        self.app.new_run()
        self.app.dialogue_modal = None
        self.app.goto("round")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_hazard_states_draw_and_report_in_the_round_scene(self):
        import pygame

        from .settings import CANVAS_H, CANVAS_W

        scene = self.app.scene
        scene.run.twist_id = lambda _rnd=None: "meteor_shower"
        scene.run.seeds["daisy"] = 3
        self.assertTrue(scene.run.plant(0, "daisy"))
        self.assertTrue(scene.run.plant(2, "daisy"))
        scene.run.plots[0].aphids = True
        scene.run.plots[1].weed = True
        scene.run.plots[2].starlit = True
        scene.run.start_timer()
        self.assertTrue(scene.run.infect(0))
        scene.update(0.16)
        note = scene.hazard_note()
        self.assertIn("STARLIT", note)
        self.assertIn("SICK", note)
        self.assertIn("WEED", note)
        self.assertTrue(self.app.toasts, "the infection should have announced itself")
        self.app.mouse = (30, 50)
        scene.draw(pygame.Surface((CANVAS_W, CANVAS_H)))

    def test_shovelling_a_weed_needs_no_confirmation(self):
        from .round import plot_rect

        scene = self.app.scene
        scene.run.plots[1].weed = True
        scene.shovel_mode = True
        x, y, w, h = plot_rect(1)
        scene.on_click((x + w // 2, y + h // 2))
        self.assertIsNone(self.app.confirm_modal, "pulling a weed is not a destructive action")
        self.assertFalse(scene.run.plots[1].weed)

    def test_lawn_rent_is_itemised_on_the_ledger(self):
        # Money that leaves without a line on the summary reads as a bug, so the
        # weed charge has to be drawn, not merely subtracted.
        import pygame

        from . import gfx
        from .settings import CANVAS_H, CANVAS_W

        run = self.app.run
        run.money = 500
        run.plots[1].weed = True
        run.plots[2].weed = True
        run.end_round()
        self.assertEqual(run.last_summary["weed_fee"], 2 * WEED_FEE)

        painted = []
        real = gfx.draw_text

        def spy(surf, text, *args, **kwargs):
            painted.append(str(text))
            return real(surf, text, *args, **kwargs)

        with patch.object(gfx, "draw_text", side_effect=spy):
            self.app.goto("summary")
            self.app.scene.draw(pygame.Surface((CANVAS_W, CANVAS_H)))
        text = " ".join(painted).upper()
        self.assertIn("LAWN RENT", text)
        self.assertIn("2 PATCHES", text)
        self.assertIn("-$12", text.replace(",", ""))

    def test_the_ledger_still_fits_with_every_hazard_charged_at_once(self):
        # Upkeep and lawn rent each add a row to the breakdown panel; the panel is
        # a fixed height, so this asserts the extra line cannot push the totals off.
        import pygame

        from . import gfx
        from .settings import CANVAS_H, CANVAS_W

        run = self.app.run
        run.money = 900
        run.plots[0] = Plot("devil_ivy")
        run.plots[0].progress = data.PLANTS["devil_ivy"]["grow"]
        for i in (1, 2, 3):
            run.plots[i].weed = True
        run.end_round()
        self.assertGreater(run.last_summary["upkeep"], 0)
        self.assertGreater(run.last_summary["weed_fee"], 0)

        ys = []
        real = gfx.draw_text

        def spy(surf, text, x, y, *a, **k):
            ys.append((str(text), y))
            return real(surf, text, x, y, *a, **k)

        with patch.object(gfx, "draw_text", side_effect=spy):
            self.app.goto("summary")
            self.app.scene.draw(pygame.Surface((CANVAS_W, CANVAS_H)))
        rows = [y for text, y in ys if "LAWN RENT" in text or "NET EARNED" in text or "TOTAL CASH" in text]
        self.assertEqual(len(rows), 3, "all three rows should be on screen")
        self.assertEqual(rows, sorted(rows))
        self.assertLess(rows[-1], CANVAS_H, "the breakdown must not run off the panel")

    def test_a_quiet_round_adds_no_lawn_rent_line(self):
        import pygame

        from . import gfx
        from .settings import CANVAS_H, CANVAS_W

        run = self.app.run
        run.money = 500
        run.end_round()
        painted = []
        real = gfx.draw_text
        with patch.object(gfx, "draw_text",
                          side_effect=lambda s, t, *a, **k: (painted.append(str(t)), real(s, t, *a, **k))[1]):
            self.app.goto("summary")
            self.app.scene.draw(pygame.Surface((CANVAS_W, CANVAS_H)))
        self.assertNotIn("LAWN RENT", " ".join(painted).upper())

    def test_weedy_soil_refuses_a_click_with_an_explanation(self):
        from .round import plot_rect

        scene = self.app.scene
        scene.selected = "daisy"
        scene.run.seeds["daisy"] = 1
        scene.run.plots[1].weed = True
        x, y, w, h = plot_rect(1)
        scene.on_click((x + w // 2, y + h // 2))
        self.assertEqual(scene.run.seeds["daisy"], 1)
        self.assertIn("WEEDS HAVE THAT PLOT", self.app.toasts[0][0])


if __name__ == "__main__":
    unittest.main()


class AppTestCase(unittest.TestCase):
    """An app on a throwaway save dir, plus the dialogue helpers Moss needs."""

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

    def modal_text(self, modal=None):
        modal = modal if modal is not None else self.app.dialogue_modal
        return " ".join(" ".join(lines) for _step, lines in modal.pages).upper()

    def quiet_run(self, round_no=2, twist="none"):
        """A run past the intro and the walkthrough, ready for exactly one beat."""
        from .tutorial import TUTORIAL_STAGES

        self.app.new_run()
        # A new run opens on the packs walkthrough; a beat wants the dialogue
        # that follows it, not the walkthrough itself.
        self.app.profile["tutorial_done"] = list(TUTORIAL_STAGES)
        tutorial.mark_beat_seen(self.app.profile, PREMISE_KEY)
        self.app.dialogue_modal = None
        run = self.app.run
        run.round = round_no
        run.twist_id = lambda _rnd=None: twist
        return run


class IntroTests(AppTestCase):
    def test_the_premise_is_folded_onto_the_front_of_the_first_walkthrough(self):
        self.app.new_run()
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        self.assertEqual(modal.pages[0][0].text[:5], "MOSS.")
        # The stage's own targeted steps still run, in order, after the intro.
        from .tutorial import TUTORIAL_BUILDERS

        steps = [page[0] for page in modal.pages]
        seen, distinct = set(), []
        for step in steps:
            if id(step) not in seen:
                seen.add(id(step))
                distinct.append(step)
        builder = TUTORIAL_BUILDERS["packs"]()
        self.assertEqual([s.text for s in distinct[-len(builder):]], [s.text for s in builder])
        self.assertEqual(len(distinct) - len(builder), len(tutorial.intro_steps()))

    def test_the_full_intro_only_plays_on_a_first_ever_run(self):
        self.app.new_run()
        self.finish_dialogue()
        self.assertIn(PREMISE_KEY, self.app.profile["story_seen"])
        self.app.goto("title")
        self.app.new_run()
        self.assertIn("BACK AGAIN", self.app.dialogue_modal.pages[0][0].text)

    def test_the_short_intro_is_two_lines_and_the_long_one_is_five(self):
        self.assertEqual(len(tutorial.intro_steps(fresh=True)), 5)
        self.assertEqual(len(tutorial.intro_steps(fresh=False)), 2)
        for step in tutorial.intro_steps():
            self.assertEqual(step.speaker, "MOSS")
            self.assertIsNone(step.target)
            self.assertEqual(step.text, step.text.upper())


class RunArcTests(AppTestCase):
    def test_a_beat_plays_on_the_packs_screen_and_is_remembered_by_the_run(self):
        run = self.quiet_run(2)
        self.app.goto("packs")
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        self.assertIn("NOTE IN THE SEED JAR", self.modal_text(modal))
        self.finish_dialogue()
        self.assertEqual(run.story_beats, ["arc-shed"])
        self.app.save_run()
        # A reload cannot make Moss repeat himself, but a new run hears it again.
        reloaded = Run.from_dict(run.to_dict())
        self.assertEqual(reloaded.story_beats, ["arc-shed"])
        beat = tutorial.beat_for(reloaded, self.app.profile)
        self.assertFalse(beat and beat[0].startswith("arc-"),
                         "Moss must not repeat a run beat after a reload")

    def test_a_skipped_beat_counts_as_heard(self):
        run = self.quiet_run(2)
        self.app.goto("packs")
        self.app.dialogue_modal.on_key(pygame.K_ESCAPE)
        self.assertIsNone(self.app.dialogue_modal)
        self.assertEqual(run.story_beats, ["arc-shed"])

    def test_beats_only_play_where_a_player_is_not_being_timed(self):
        self.quiet_run(2, twist="disease")
        self.app.goto("round")
        self.assertIsNone(self.app.dialogue_modal, "the round screen must never be interrupted")
        self.app.goto("packs")
        self.finish_dialogue()          # the round-two beat, on the packs screen

        # And a beat never stacks on top of another modal.
        self.app.run.story_beats = []
        self.app.open_pause()
        self.app.start_story()
        self.assertIsNone(self.app.dialogue_modal, "a modal already on screen wins")
        self.app.pause_modal = None
        self.app.start_story()
        self.assertIsNotNone(self.app.dialogue_modal, "a free packs screen does get its beat")

    def test_a_bill_beat_quotes_the_real_bill(self):
        run = Run(seed=4)
        run.grant_round_packs()
        run.round = 3
        beat = tutorial.beat_for(run, self.app.profile)
        self.assertEqual(beat[0], "arc-first-bill")
        self.assertEqual(beat[2], False, "arc beats are per-run, not per-profile")
        self.assertIn("$300", beat[1][0].text)

    def test_no_beat_waits_on_a_quiet_round(self):
        # Round 8 with fair weather and nothing paid off is deliberately silent:
        # a beat every round would be noise, and Moss talking at all is the
        # exception the player learns to look for.
        run = Run(seed=4)
        run.round = 8
        run.twist_id = lambda _rnd=None: "none"
        self.assertIsNone(tutorial.beat_for(run, self.app.profile))

    def test_a_paid_bill_unlocks_the_next_arc_beat(self):
        run = Run(seed=4)
        run.round = 4
        self.assertNotEqual((tutorial.beat_for(run, self.app.profile) or ("",))[0], "arc-first-paid")
        run.quotas_paid = 1
        self.assertEqual(tutorial.beat_for(run, self.app.profile)[0], "arc-first-paid")

    def test_the_endless_beat_needs_the_deed_to_be_paid_off(self):
        run = Run(seed=4)
        run.round = 25
        self.assertNotEqual(tutorial.beat_for(run, self.app.profile)[0], "arc-past")
        run.endless = True
        run.quotas_paid = 8
        self.assertEqual(tutorial.beat_for(run, self.app.profile)[0], "arc-past")

    def test_the_deed_beat_lands_on_the_last_bill(self):
        run = Run(seed=4)
        run.round = 24
        self.assertEqual(tutorial.beat_for(run, self.app.profile)[0], "arc-deed")


class SeasonAndHazardBeatTests(AppTestCase):
    def test_a_season_beat_lands_on_the_first_round_of_that_season_only(self):
        # Seasons are nine rounds, so each one begins where a boss round begins:
        # the arc beats are marked heard here to isolate the season text.
        for round_no, season in ((10, "Summer"), (19, "Autumn"), (28, "Winter"), (37, "Spring")):
            with self.subTest(round=round_no, season=season):
                run = Run(seed=round_no)
                run.round = round_no
                for beat in tutorial.RUN_BEATS:
                    run.mark_story_beat(beat["id"])
                beat = tutorial.beat_for(run, self.app.profile)
                self.assertEqual(beat[0], "season-" + season.lower())
                run.mark_story_beat(beat[0])
                self.assertNotEqual((tutorial.beat_for(run, self.app.profile) or ("",))[0],
                                    "season-" + season.lower(),
                                    "a season beat must not follow you through all nine rounds")
                # Round 1 is the intro's own moment; Moss keeps quiet about seasons.
                first = Run(seed=1)
                first.round = 1
                self.assertNotEqual((tutorial.beat_for(first, self.app.profile) or ("",))[0], "season-spring")

    def test_a_hazard_warning_carries_the_rule_it_warns_about(self):
        for tid, keyword in (("disease", "SHOVEL"), ("meteor_shower", "STARLIT"),
                             ("weeds", "DIG"), ("aphids", "WATER")):
            with self.subTest(twist=tid):
                run = Run(seed=4)
                run.round = 8
                run.twist_id = lambda _rnd=None, t=tid: t
                beat = tutorial.beat_for(run, self.app.profile)
                self.assertEqual(beat[0], "haz-" + tid)
                self.assertTrue(beat[2], "hazard warnings persist in the profile")
                self.assertIn(keyword, " ".join(s.text for s in beat[1]),
                              "a beat that is all mood and no rule is a wasted click")

    def test_a_warning_is_explained_once_per_save_file_ever(self):
        self.quiet_run(8, twist="disease")
        self.app.goto("packs")
        modal = self.app.dialogue_modal
        self.assertIsNotNone(modal)
        self.assertIn("DISEASE TODAY", self.modal_text(modal))
        self.finish_dialogue()
        self.assertIn("haz-disease", self.app.profile["story_seen"])
        self.assertIn("haz-disease", self.app.saves.load_profile()["story_seen"])

        # Same rot, later run: the plots still get sick, the lecture does not.
        run = self.quiet_run(8, twist="disease")
        run.story_beats = []
        self.app.goto("packs")
        self.assertIsNone(self.app.dialogue_modal, "Moss explains a rot once, ever")

    def test_the_run_arc_outranks_a_hazard_warning_on_the_same_round(self):
        # Round 9 is both the tenants beat and a boss forecast; the arc is the one
        # that only gets one chance, so it goes first and the rot waits its turn.
        run = Run(seed=4)
        run.round = 9
        beat = tutorial.beat_for(run, self.app.profile)
        self.assertEqual(beat[0], "arc-tenants")


class LorePassTests(AppTestCase):
    def test_every_twist_carries_a_story_hint(self):
        self.assertEqual({tid for tid, twist in data.TWISTS.items() if twist.get("lore")},
                         set(data.TWISTS))
        for tid, twist in data.TWISTS.items():
            with self.subTest(twist=tid):
                self.assertGreater(len(twist["lore"]), 20)
                self.assertNotIn("\n", twist["lore"])
        self.assertEqual(data.twist_lore("disease"), data.TWISTS["disease"]["lore"])
        self.assertEqual(data.twist_lore("nope"), "")

    def test_lore_never_touches_the_maths(self):
        for tid in ("disease", "meteor_shower", "weeds", "aphids"):
            twist = data.TWISTS[tid]
            self.assertEqual((twist["growth"], twist["yield"], twist["time"]), (1.0, 1.0, 0))
            self.assertIsNone(twist["ban"])

    def test_the_plants_she_kept_are_documented(self):
        documented = {sid for sid, plant in data.PLANTS.items() if plant.get("lore")}
        self.assertTrue(documented <= set(data.PLANTS))
        self.assertGreaterEqual(len(documented), 25)
        for sid in ("daisy", "aloe_vera", "crystal_bloom"):
            self.assertIn(sid, documented, "a crop she was known for should have a line")
        self.assertEqual(data.plant_lore("daisy"), data.PLANTS["daisy"]["lore"])
        self.assertTrue(data.plant_lore("daisy_shiny"), "a mutant inherits its base plant's line")
        self.assertEqual(data.plant_lore("nope"), "")

    def test_every_plant_and_relic_with_a_slot_for_lore_uses_it(self):
        # The counterplay relics must explain themselves, or their whole purpose
        # (an answer to a hazard) is invisible in the shop.
        for rid, relic in data.RELICS.items():
            if {"disease_resist", "sick_relief", "rod_protects"} & set(relic["effects"]):
                self.assertTrue(relic.get("lore"), rid)
        documented = [plant for plant in data.PLANTS.values() if plant.get("lore")]
        self.assertEqual(len(documented), 25, "the crops she kept, and no others")

    def test_the_title_screen_and_the_guide_agree_on_the_premise(self):
        self.assertIn("EIGHT UNPAID BILLS", tutorial.PREMISE)
        guide = tutorial.guide_steps()
        self.assertGreaterEqual(len(guide), 4)
        self.assertTrue(any("DEED" in step.text for step in guide))
        self.assertEqual([s.text for s in guide_steps()], [s.text for s in guide],
                         "the title guide must not fork the story")

    def test_the_forecast_tooltip_is_where_the_hint_lives(self):
        # A player reads the forecast before every round, so this is the one
        # place a hint cannot be skipped by reflex-clicking.
        run = self.quiet_run(8, twist="disease")
        self.app.goto("packs")
        lines = [text for text, _col in self.app.scene.forecast_lines()]
        self.assertIn("DISEASE", " ".join(lines))
        self.assertEqual(lines[3], data.twist_lore("disease"), "the hint belongs on the forecast")
        self.assertTrue(lines[-1].startswith("ROUND TIME"), "the numbers stay last")
        run.twist_id = lambda _rnd=None: "weeds"
        self.assertIn(data.twist_lore("weeds"), [text for text, _c in self.app.scene.forecast_lines()])


class CopyTests(unittest.TestCase):
    def test_every_story_line_fits_the_font_and_the_box(self):
        from . import gfx
        from .tutorial import BODY_LINES, BOX_W, TEXT_PAD

        texts = [s.text for s in tutorial.guide_steps()]
        texts += [s.text for step in (tutorial.intro_steps(), tutorial.intro_steps(fresh=False)) for s in step]
        run = Run(seed=4)
        for beat in tutorial.RUN_BEATS + tutorial.SEASON_BEATS + tutorial.HAZARD_BEATS:
            steps = beat["steps"]
            texts += [s.text for s in (steps(run) if callable(steps) else steps)]
        missing = {ch for text in texts for ch in text.upper() if ch not in FONT}
        self.assertEqual(missing, set())
        for text in texts:
            self.assertNotIn(";", text)
            self.assertNotIn('"', text)
            # Two pages of the dialogue box is the ceiling: past that, Moss is
            # giving a lecture and the player is clicking through it unread.
            lines = gfx.wrap(text, BOX_W - TEXT_PAD * 2)
            self.assertLessEqual(len(lines), BODY_LINES * 2, text)

    def test_a_beat_never_runs_past_three_pages(self):
        from . import gfx
        from .tutorial import BODY_LINES, BOX_W, TEXT_PAD

        run = Run(seed=4)
        for beat in tutorial.RUN_BEATS + tutorial.SEASON_BEATS + tutorial.HAZARD_BEATS:
            steps = beat["steps"]
            steps = steps(run) if callable(steps) else steps
            pages = sum(max(1, -(-len(gfx.wrap(s.text, BOX_W - TEXT_PAD * 2)) // BODY_LINES)) for s in steps)
            self.assertLessEqual(pages, 3, beat["id"])

    def test_the_title_premise_fits_the_screen_width(self):
        from . import gfx
        from .settings import CANVAS_W

        self.assertLessEqual(gfx.text_width(gfx.fit_text(tutorial.PREMISE, CANVAS_W - 20), 1), CANVAS_W - 20)

    def test_beats_are_keyed_to_rounds_the_game_reaches(self):
        # A beat on a round past the last bill can only fire in endless mode, so
        # the roster is checked against the ladder it is supposed to ride.
        from .settings import QUOTA_EVERY, WIN_QUOTAS

        last_bill_round = QUOTA_EVERY * WIN_QUOTAS
        self.assertEqual(last_bill_round, 24)
        for beat in tutorial.RUN_BEATS:
            for round_no in beat.get("rounds", ()):
                self.assertLessEqual(round_no, last_bill_round, beat["id"])
            self.assertTrue(beat["steps"], beat["id"])
        ids = [b["id"] for b in tutorial.RUN_BEATS + tutorial.SEASON_BEATS + tutorial.HAZARD_BEATS]
        self.assertEqual(len(ids), len(set(ids)), "beat ids are save keys")


if __name__ == "__main__":
    unittest.main()
