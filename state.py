"""The game rules. Pure Python with no pygame, so it can be tested without a
window and reused if you ever change the graphics layer."""

from __future__ import annotations

import random

try:
    from . import data
    from .settings import (
        BASE_FREE_PACKS, COLS, MAX_PLOTS, MUTATION_CHANCE, PLOT_BASE_PRICE, PLOT_PRICE_GROWTH,
        LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, PRICE_GROWTH, QUOTA_EVERY,
        RELIC_SLOTS, REROLL_BASE_PRICE, ROUND_TIME,
        SEEDS_PER_PACK, START_MONEY, START_PLOTS, WATER_BOOST, WATER_REST,
        WATER_TIME, WIN_QUOTAS,
    )
except ImportError:
    import data
    from settings import (
        BASE_FREE_PACKS, COLS, MAX_PLOTS, MUTATION_CHANCE, PLOT_BASE_PRICE, PLOT_PRICE_GROWTH,
        LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, PRICE_GROWTH, QUOTA_EVERY,
        RELIC_SLOTS, REROLL_BASE_PRICE, ROUND_TIME,
        SEEDS_PER_PACK, START_MONEY, START_PLOTS, WATER_BOOST, WATER_REST,
        WATER_TIME, WIN_QUOTAS,
    )


def milestone_level(count):
    return sum(1 for t in data.MILESTONES if count >= t)


class Plot:
    __slots__ = ("species", "progress", "water_left", "water_cd", "harvests")

    def __init__(self, species=None, progress=0.0, water_left=0.0, water_cd=0.0, harvests=0):
        self.species = species
        self.progress = progress
        self.water_left = water_left
        self.water_cd = water_cd
        self.harvests = harvests

    def clear(self):
        self.species, self.progress, self.water_left, self.water_cd, self.harvests = None, 0.0, 0.0, 0.0, 0

    def to_dict(self):
        return {"species": self.species, "progress": self.progress,
                "water_left": self.water_left, "water_cd": self.water_cd, "harvests": self.harvests}

    @classmethod
    def from_dict(cls, d):
        species = d.get("species")
        if species not in data.PLANTS:
            species = None
        return cls(species, float(d.get("progress", 0)), float(d.get("water_left", 0)),
                   float(d.get("water_cd", 0)), int(d.get("harvests", 0)))


class Run:

    def __init__(self, seed=None, perks=None):
        self.seed = seed if seed is not None else random.randrange(1, 1 << 30)
        self.rng = random.Random(self.seed)
        self.perks = {k: int(v) for k, v in (perks or {}).items() if k in data.PERKS}

        self.round = 1
        self.phase = "packs"            # packs -> round -> summary -> shop -> packs ...
        self.money = START_MONEY + 10 * self.perks.get("cash", 0)
        self.seeds = {}                 # species id -> count in your pocket
        self.packs = []                 # unopened pack kinds
        self.plots = [Plot() for _ in range(min(MAX_PLOTS, START_PLOTS + self.perks.get("plots", 0)))]
        self.plots_bought = 0
        self.relics = []
        self.mastery = {}               # species id -> total harvests this run
        self.shop_offers = []           # relic ids (or None once bought)
        self.rerolls = 0
        self.quotas_paid = 0
        self.total_earned = 0
        self.won = False
        self.dead = False

        # live round state
        self.time_total = ROUND_TIME
        self.time_left = ROUND_TIME
        self.started = False
        self.finished = False
        self.round_income = 0
        self.blight_done = False
        self.events = []                # UI feed: harvest popups etc. (not saved)
        self.last_summary = None
        self.pending_bill = 0

    # ------------------------------------------------------------ helpers
    def perk(self, key):
        return self.perks.get(key, 0)

    def _effects(self):
        for rid in self.relics:
            yield data.RELICS[rid]["effects"]

    def _sum(self, key):
        return sum(e.get(key, 0) for e in self._effects())

    def _has(self, key):
        return any(e.get(key) for e in self._effects())

    # ------------------------------------------------------ round / quota
    @staticmethod
    def is_quota_round(rnd):
        return rnd % QUOTA_EVERY == 0

    @staticmethod
    def quota_number(rnd):
        return rnd // QUOTA_EVERY

    def bill_for_round(self, rnd):
        return data.bill_for_quota(self.quota_number(rnd)) if self.is_quota_round(rnd) else 0

    def next_quota_round(self, rnd=None):
        rnd = self.round if rnd is None else rnd
        return ((rnd + QUOTA_EVERY - 1) // QUOTA_EVERY) * QUOTA_EVERY

    def twist_id(self, rnd):
        if not self.is_quota_round(rnd):
            return "none"
        k = self.quota_number(rnd)
        if k == 1:
            return "none"
        return random.Random(self.seed * 7919 + k).choice(data.RANDOM_TWISTS)

    def twist(self, rnd=None):
        return data.TWISTS[self.twist_id(self.round if rnd is None else rnd)]

    # ------------------------------------------------------------ numbers
    def growth_speed(self):
        return (1.0 + self._sum("growth")) * self.twist()["growth"]

    def water_time(self):
        return WATER_TIME + self._sum("water_time")

    def round_time(self):
        late_reduction = max(0, self.round - 3) * LATE_ROUND_TIME_DROP
        base_time = max(LATE_ROUND_TIME_FLOOR, ROUND_TIME - late_reduction)
        return max(10, base_time + self._sum("round_time") + self.twist()["time"])

    def interest_rate(self):
        return self._sum("interest")

    def neighbours(self, i):
        if not 0 <= i < len(self.plots):
            return []
        out = []
        r, c = divmod(i, COLS)
        if c > 0:
            out.append(i - 1)
        if c < COLS - 1 and i + 1 < len(self.plots):
            out.append(i + 1)
        if r > 0:
            out.append(i - COLS)
        if i + COLS < len(self.plots):
            out.append(i + COLS)
        return out

    def harvest_breakdown(self, i):
        """(chips, mult) for a plot: harvest value is chips x mult."""
        if not 0 <= i < len(self.plots):
            return 0, 0.0
        plot = self.plots[i]
        if plot.species not in data.PLANTS:
            return 0, 0.0
        sp = data.PLANTS[plot.species]
        tags = sp["tags"]
        chips = sp["yield"]
        for e in self._effects():
            for tag, amount in e.get("yield_add", []):
                if tag == "all" or tag in tags:
                    chips += amount
            for tag, needs, amount in e.get("adjacent", []):
                if tag in tags:
                    for n in self.neighbours(i):
                        other = self.plots[n].species
                        if other and needs in data.PLANTS[other]["tags"]:
                            chips += amount

        mult = 2.0 ** milestone_level(self.mastery.get(plot.species, 0))
        planted = [p.species for p in self.plots if p.species]
        distinct = len(set(planted))
        for e in self._effects():
            for tag, m in e.get("yield_mult", []):
                if tag == "all" or tag in tags:
                    mult *= m
            if e.get("distinct_bonus"):
                mult *= 1.0 + e["distinct_bonus"] * distinct
            if e.get("mono_mult") and distinct == 1 and len(planted) >= 2:
                mult *= e["mono_mult"]
        mult *= 1.0 + 0.10 * self.perk("yield")
        mult *= self.twist()["yield"]
        return chips, mult

    def harvest_value(self, i):
        chips, mult = self.harvest_breakdown(i)
        return max(1, int(round(chips * min(mult, 1e250))))

    # ------------------------------------------------------------- packs
    def free_pack_count(self):
        return BASE_FREE_PACKS + self.perk("packs") + int(self._sum("free_packs"))

    def pick_free_pack_kind(self):
        kinds = [k for k in data.PACK_ORDER if data.free_pack_weight(k, self.round) > 0]
        weights = [data.free_pack_weight(k, self.round) for k in kinds]
        return self.rng.choices(kinds, weights)[0]

    def grant_round_packs(self):
        for _ in range(self.free_pack_count()):
            self.packs.append(self.pick_free_pack_kind())

    def unlocked_packs(self):
        return [k for k in data.PACK_ORDER if data.PACKS[k]["unlock"] <= self.round]

    def pack_price(self, kind):
        return int(data.PACKS[kind]["cost"] * PRICE_GROWTH ** (self.round - 1))

    def draw_seed(self, kind):
        luck = self._effects_product("pack_luck")
        pool = data.PACKS[kind]["pool"]
        ids = list(pool)
        weights = []
        for sid in ids:
            w = pool[sid]
            if data.PLANTS[sid]["rarity"] in ("rare", "legendary"):
                w *= luck
            weights.append(w)
        return self.rng.choices(ids, weights)[0]

    def _effects_product(self, key):
        p = 1.0
        for e in self._effects():
            p *= e.get(key, 1.0)
        return p

    def open_pack(self):
        """Opens the oldest pack. Returns (kind, [seed ids]) or None."""
        if not self.packs:
            return None
        kind = self.packs.pop(0)
        got = [self.draw_seed(kind) for _ in range(SEEDS_PER_PACK)]
        for sid in got:
            self.seeds[sid] = self.seeds.get(sid, 0) + 1
        return kind, got

    def buy_pack(self, kind):
        if kind not in self.unlocked_packs():
            return False
        price = self.pack_price(kind)
        if self.money < price:
            return False
        self.money -= price
        self.packs.append(kind)
        return True

    # ----------------------------------------------------- planting etc.
    def can_plant(self, species):
        if species not in data.PLANTS:
            return False
        ban = self.twist()["ban"]
        return not (ban and ban in data.PLANTS[species]["tags"])

    def plant(self, i, species):
        if not (0 <= i < len(self.plots)) or self.plots[i].species is not None:
            return False
        if self.seeds.get(species, 0) <= 0 or not self.can_plant(species):
            return False
        self.seeds[species] -= 1
        self.plots[i] = Plot(species)
        return True

    def can_water(self, i):
        if not 0 <= i < len(self.plots):
            return False
        p = self.plots[i]
        return self.started and not self.finished and p.species is not None and p.water_cd <= 0

    def water(self, i):
        if not self.can_water(i):
            return False
        p = self.plots[i]
        wt = self.water_time()
        p.water_left = wt
        p.water_cd = wt if self._has("auto_water") else wt + WATER_REST
        return True

    # -------------------------------------------------------- the round
    def begin_round(self):
        self.phase = "round"
        self.pending_bill = 0
        self.time_total = self.round_time()
        self.time_left = self.time_total
        self.started = False
        self.finished = False
        self.blight_done = False
        self.round_income = 0
        self.events = []
        for p in self.plots:
            p.clear()

    def start_timer(self):
        self.started = True

    def finish_early(self):
        if self.started:
            self.finished = True

    def update(self, dt):
        if self.phase != "round" or not self.started or self.finished or dt <= 0:
            return
        dt = min(dt, self.time_left)
        speed = self.growth_speed()
        auto = self._has("auto_water")
        for i, p in enumerate(self.plots):
            if p.species is None:
                continue
            if auto and p.water_cd <= 0:
                self.water(i)
            boosted = min(dt, max(p.water_left, 0.0))
            p.progress += speed * (dt + (WATER_BOOST - 1.0) * boosted)
            p.water_left = max(0.0, p.water_left - dt)
            p.water_cd = max(0.0, p.water_cd - dt)
            grow = data.PLANTS[p.species]["grow"]
            guard = 0
            while p.progress >= grow and guard < 1000:
                p.progress -= grow
                self._harvest(i)
                guard += 1
            if guard >= 1000:
                p.progress = 0.0

        previous = self.time_left
        self.time_left -= dt
        half = self.time_total / 2.0
        if self.twist()["blight"] and not self.blight_done and previous > half >= self.time_left:
            self.blight_done = True
            alive = [i for i, p in enumerate(self.plots) if p.species]
            if alive:
                victim = self.rng.choice(alive)
                self.events.append({"kind": "wither", "plot": victim})
                self.plots[victim].clear()
        if self.time_left <= 1e-9:
            self.time_left = 0.0
            self.finished = True

    def _harvest(self, i):
        value = self.harvest_value(i)
        species = self.plots[i].species
        self.money += value
        self.round_income += value
        self.total_earned += value
        self.mastery[species] = self.mastery.get(species, 0) + 1
        self.plots[i].harvests += 1
        if len(self.events) < 300:
            self.events.append({"kind": "harvest", "plot": i, "amount": value})
        self._maybe_mutate(i)

    def _maybe_mutate(self, i):
        """After enough harvests, a plant may turn into its mutant version
        for the rest of the round: different value, growth speed, even tags."""
        plot = self.plots[i]
        if plot.species not in data.PLANTS or plot.harvests < data.mutation_threshold(plot.species):
            return
        options = data.mutants_for(plot.species)
        if not options or self.rng.random() >= MUTATION_CHANCE:
            return
        mid = self.rng.choice(options)
        plot.species = mid
        plot.harvests = 0
        if len(self.events) < 300:
            self.events.append({"kind": "mutate", "plot": i, "name": data.PLANTS[mid]["name"]})
            
    def end_round(self):
        """Sells ripe plants, pays interest, and settles the bill if one is due."""
        comp = 1.0 + self._sum("sell_mult")
        sale = 0
        for p in self.plots:
            if p.species:
                sp = data.PLANTS[p.species]
                frac = min(1.0, p.progress / sp["grow"])
                sale += int(sp["sell"] * frac * comp)
            p.clear()
        self.money += sale
        self.total_earned += sale
        interest = int(self.money * self.interest_rate())
        self.money += interest
        self.total_earned += interest

        bill = self.bill_for_round(self.round)
        self.pending_bill = bill
        paid = None
        victory = False
        if bill and self.money < bill:
            paid = False
            self.dead = True
            self.pending_bill = 0

        self.last_summary = {
            "round": self.round, "harvest": self.round_income, "earned": self.round_income + sale + interest, "sale": sale,
            "interest": interest, "bill": bill, "paid": paid, "money": self.money,
            "victory": victory, "twist": self.twist_id(self.round), "pending_bill": bool(self.pending_bill),
        }
        self.phase = "gameover" if self.dead else "summary"
        return self.last_summary

    def pay_pending_bill(self):
        bill = self.pending_bill
        if not bill:
            return True, "No bill due."
        if self.money < bill:
            self.dead = True
            self.pending_bill = 0
            self.last_summary["paid"] = False
            return False, "Not enough money. The run is over."
        self.money -= bill
        self.quotas_paid += 1
        self.pending_bill = 0
        self.last_summary["paid"] = True
        self.last_summary["money"] = self.money
        if self.quotas_paid >= WIN_QUOTAS and not self.won:
            self.won = True
            self.last_summary["victory"] = True
        return True, "Bill paid!"

    def decline_bill(self):
        self.pending_bill = 0
        self.dead = True
        if self.last_summary:
            self.last_summary["paid"] = False
            self.last_summary["money"] = self.money
        return False, "Bill unpaid. The run is over."

    def heirloom_reward(self):
        return max(0, self.round - 1) + 3 * self.quotas_paid

    # --------------------------------------------------------------- shop
    def enter_shop(self):
        self.phase = "shop"
        self.rerolls = 0
        self.roll_offers()

    def roll_offers(self):
        pool = [r for r in data.RELIC_ORDER if r not in self.relics]
        offers = []
        for _ in range(3):
            if not pool:
                break
            weights = [data.RARITY_WEIGHT[data.RELICS[r]["rarity"]] for r in pool]
            pick = self.rng.choices(pool, weights)[0]
            pool.remove(pick)
            offers.append(pick)
        self.shop_offers = offers

    def relic_price(self, rid):
        rarity = data.RELICS[rid]["rarity"]
        rarity_multiplier = {"common": 1.0, "uncommon": 1.3, "rare": 1.7, "legendary": 2.2}[rarity]
        return int(data.RELICS[rid]["cost"] * rarity_multiplier * PRICE_GROWTH ** (self.round - 1))

    def reroll_price(self):
        return int(REROLL_BASE_PRICE * 2.0 ** self.rerolls * PRICE_GROWTH ** (self.round - 1))

    def reroll(self):
        price = self.reroll_price()
        if self.money < price:
            return False
        self.money -= price
        self.rerolls += 1
        self.roll_offers()
        return True

    def buy_relic(self, index):
        """Returns (ok, reason)."""
        if not (0 <= index < len(self.shop_offers)) or self.shop_offers[index] is None:
            return False, "Nothing there."
        if len(self.relics) >= RELIC_SLOTS:
            return False, "Relic slots are full."
        rid = self.shop_offers[index]
        price = self.relic_price(rid)
        if self.money < price:
            return False, "Not enough money."
        self.money -= price
        self.relics.append(rid)
        self.shop_offers[index] = None
        return True, "Bought %s!" % data.RELICS[rid]["name"]

    def sell_relic(self, index):
        if not 0 <= index < len(self.relics):
            return False, "No relic there.", 0
        rid = self.relics[index]
        refund = max(1, int(self.relic_price(rid) * 0.5))
        self.relics.pop(index)
        self.money += refund
        return True, "Sold %s for $%d!" % (data.RELICS[rid]["name"], refund), refund

    def plot_price(self):
        return int(PLOT_BASE_PRICE * PLOT_PRICE_GROWTH ** self.plots_bought)

    def buy_plot(self):
        if len(self.plots) >= MAX_PLOTS or self.money < self.plot_price():
            return False
        self.money -= self.plot_price()
        self.plots_bought += 1
        self.plots.append(Plot())
        return True

    def start_next_round(self):
        self.round += 1
        self.phase = "packs"
        self.grant_round_packs()

    # --------------------------------------------------------- save / load
    def to_dict(self):
        version, internal, gauss = self.rng.getstate()
        return {
            "v": 1, "seed": self.seed, "rng": [version, list(internal), gauss],
            "perks": self.perks, "round": self.round, "phase": self.phase,
            "money": self.money, "seeds": self.seeds, "packs": self.packs,
            "plots": [p.to_dict() for p in self.plots], "plots_bought": self.plots_bought,
            "relics": self.relics, "mastery": self.mastery,
            "shop_offers": self.shop_offers, "rerolls": self.rerolls,
            "quotas_paid": self.quotas_paid, "total_earned": self.total_earned,
            "won": self.won, "dead": self.dead, "pending_bill": self.pending_bill,
        }

    @classmethod
    def from_dict(cls, d):
        run = cls(seed=d.get("seed"), perks=d.get("perks"))
        rng = d.get("rng")
        if rng:
            run.rng.setstate((rng[0], tuple(rng[1]), rng[2]))
        run.round = max(1, int(d.get("round", 1)))
        phase = d.get("phase", "packs")
        run.phase = phase if phase in ("packs", "shop", "summary") else "packs"
        run.money = int(d.get("money", 0))
        run.seeds = {k: int(v) for k, v in d.get("seeds", {}).items() if k in data.PLANTS and v > 0}
        run.packs = [k for k in d.get("packs", []) if k in data.PACKS]
        plots = [Plot.from_dict(p) for p in d.get("plots", [])]
        if plots:
            run.plots = plots[:MAX_PLOTS]
        run.plots_bought = int(d.get("plots_bought", 0))
        run.relics = [r for r in d.get("relics", []) if r in data.RELICS][:RELIC_SLOTS]
        run.mastery = {k: int(v) for k, v in d.get("mastery", {}).items() if k in data.PLANTS}
        run.shop_offers = [r if r in data.RELICS else None for r in d.get("shop_offers", [])]
        run.rerolls = int(d.get("rerolls", 0))
        run.quotas_paid = int(d.get("quotas_paid", 0))
        run.total_earned = int(d.get("total_earned", 0))
        run.won = bool(d.get("won", False))
        run.dead = bool(d.get("dead", False))
        run.pending_bill = int(d.get("pending_bill", 0))
        if run.phase == "summary" and run.pending_bill:
            run.last_summary = {"round": run.round, "bill": run.pending_bill, "paid": None,
                                 "money": run.money, "pending_bill": True}
        if run.phase == "shop" and not run.shop_offers:
            run.roll_offers()
        for p in run.plots:      # saves are taken between rounds: boards start empty
            p.clear()
        return run
