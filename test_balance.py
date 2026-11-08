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
        run.twist_id = lambda _rnd=None: "none"
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

    def test_relics_stay_buyable_deeper_into_a_run(self):
        """Relics used to double every round, which priced them out of the
        game by round 9 (a common relic cost 20x a round's income). They still
        have to climb hard, just slower than the bill ladder (~1.71x a round)."""
        from .settings import PRICE_GROWTH, RELIC_PRICE_GROWTH
        self.assertLess(RELIC_PRICE_GROWTH, 1.71)
        self.assertGreater(RELIC_PRICE_GROWTH, PRICE_GROWTH)   # still the dearer tier
        self.assertLess(PRICE_GROWTH, 1.71)
        run = Run(seed=1)
        early = run.relic_price("scarecrow")
        run.round = 9
        late = run.relic_price("scarecrow")
        self.assertGreater(late, early * 10)                   # prices still bite
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


if __name__ == "__main__":
    unittest.main()

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
                self.assertIn(sid, data.mutants_for(sid) or [] or [sid])  # no crash

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

    def test_four_crops_have_sprites_and_two_borrow_the_placeholder(self):
        from .sprites_data import GRIDS
        for sid in ("potato", "wheat", "corn", "carrot"):
            self.assertIn(sid, GRIDS, "%s has no sprite" % sid)
        # cranberries and saffron are stats-only for now: the renderer has to
        # fall back instead of exploding
        for sid in ("cranberries", "saffron"):
            self.assertNotIn(sid, GRIDS)

    def test_missing_sprites_fall_back_to_placeholder_art(self):
        import pygame
        from . import gfx
        pygame.init()
        pygame.display.set_mode((1, 1))
        for sid in ("cranberries", "saffron", "potato"):
            surface = gfx.sprite(sid)
            self.assertEqual(surface.get_size(), (12, 12))
            self.assertNotEqual(surface, gfx.sprite("daisy"))


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

    def test_crazy_crows_eat_plants_and_speed_up(self):
        twist = data.TWISTS["crow_swarm"]
        self.assertEqual(twist["name"], "Crazy Crows!")
        self.assertLessEqual(twist["crow"], 6)          # meaner than the old 10s
        self.assertTrue(twist["crow_ramp"])
        run = self.pinned("crow_swarm", plots=8)
        run.time_total = run.time_left = 24.0
        eaten_first_half = eaten_second_half = 0
        for _ in range(12):
            run.update(1.0)
            for ev in run.events:
                if ev["kind"] == "eaten":
                    eaten_first_half += 1
            run.events.clear()
        for _ in range(12):
            run.update(1.0)
            for ev in run.events:
                if ev["kind"] == "eaten":
                    eaten_second_half += 1
            run.events.clear()
        self.assertGreater(eaten_first_half, 0)
        self.assertGreater(eaten_second_half, eaten_first_half)

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