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
        for sid in data.NOCTURNAL_PLANTS:
            with self.subTest(crop=sid):
                self.assertTrue(data.mutants_for(sid))

    def test_garden_flowers_have_more_than_one_mutation(self):
        garden = [sid for sid in data.SURFACE_PLANTS if sid not in data.FARMER_PLANTS]
        for sid in garden:
            with self.subTest(plant=sid):
                self.assertGreaterEqual(len(data.mutants_for(sid)), 2)

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


if __name__ == "__main__":
    unittest.main()
