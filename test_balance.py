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
        summary = run.end_round()
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


if __name__ == "__main__":
    unittest.main()
