"""Headless run simulation: garden plots, weather twists, relics, quotas, and serialization.

Imports no graphics libraries so balance tests and simulations can run without a display.
"""

from __future__ import annotations

import math
import random

try:
    from . import data
    from .settings import (
        BASE_FREE_PACKS, BOSS_EVERY, CELLAR_PLOTS, CELLAR_PRICE, CELLAR_SPEED,
        COLS, LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, MAX_PLOTS,
        MUTATION_CHANCE, MYCELIUM_CREEP_SHARE, MYCELIUM_CREEP_TIME, MYCELIUM_MAX_SPREAD,
        PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEED_SELL_SHARE, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WIN_QUOTAS,
    )
except ImportError:
    import data
    from settings import (
        BASE_FREE_PACKS, BOSS_EVERY, CELLAR_PLOTS, CELLAR_PRICE, CELLAR_SPEED,
        COLS, LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, MAX_PLOTS,
        MUTATION_CHANCE, MYCELIUM_CREEP_SHARE, MYCELIUM_CREEP_TIME, MYCELIUM_MAX_SPREAD,
        PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEED_SELL_SHARE, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WIN_QUOTAS,
    )

MAX_EVENTS = 300


def milestone_level(count):
    """Number of harvest-mastery thresholds reached; each level doubles species yield."""
    return sum(1 for t in data.MILESTONES if count >= t)


class Plot:
    """State of a single soil plot on either the surface garden or underground cellar.

    Besides the growth timers a plot carries the layout-mechanic bookkeeping:
    `fed` is flytrap food collected since its last harvest, `gorged` is the
    base harvest a Man-Eater has eaten for good, and `bloom` is the multiplier
    a lucky clover has stacked onto this plant.

    Mycelium adds `creep_cd`: seconds its creep meter has banked. A mycelium
    with a full meter grows into an empty orthogonal neighbour on its own, so a
    patch keeps advancing round after round instead of sitting still.
    """

    __slots__ = ("species", "progress", "water_left", "water_cd", "harvests", "fed", "gorged", "bloom",
                 "creep_cd", "mature_time")

    def __init__(self, species=None, progress=0.0, water_left=0.0, water_cd=0.0, harvests=0,
                fed=0, gorged=0.0, bloom=1.0, creep_cd=0.0, mature_time=0.0):
        self.species = species
        self.progress = progress
        self.water_left = water_left
        self.water_cd = water_cd
        self.harvests = harvests
        self.fed = fed
        self.gorged = gorged
        self.bloom = bloom
        self.creep_cd = creep_cd
        self.mature_time = mature_time

    def clear(self):
        self.species = None
        self.progress = 0.0
        self.water_left = 0.0
        self.water_cd = 0.0
        self.harvests = 0
        self.fed = 0
        self.gorged = 0.0
        self.bloom = 1.0
        self.creep_cd = 0.0
        self.mature_time = 0.0

    def to_dict(self):
        return {
            "species": self.species, "progress": self.progress,
            "water_left": self.water_left, "water_cd": self.water_cd,
            "harvests": self.harvests, "fed": self.fed,
            "gorged": self.gorged, "bloom": self.bloom,
            "creep_cd": self.creep_cd,
            "mature_time": self.mature_time,
        }

    @classmethod
    def from_dict(cls, d):
        species = d.get("species")
        if species not in data.PLANTS:
            species = None
        return cls(
            species,
            float(d.get("progress", 0)),
            float(d.get("water_left", 0)),
            float(d.get("water_cd", 0)),
            int(d.get("harvests", 0)),
            int(d.get("fed", 0)),
            float(d.get("gorged", 0)),
            float(d.get("bloom", 1.0)),
            float(d.get("creep_cd", 0)),
            float(d.get("mature_time", 0.0)),
        )


class Run:
    """Complete state and rules engine for a single Bloom & Bills run."""

    def __init__(self, seed=None, perks=None):
        self.seed = seed if seed is not None else random.randrange(1, 1 << 30)
        self.rng = random.Random(self.seed)
        self.perks = {k: int(v) for k, v in (perks or {}).items() if k in data.PERKS}

        self.round = 1
        self.phase = "packs"
        self.money = START_MONEY
        self.seeds = {}
        self.packs = []
        self.plots = [Plot() for _ in range(min(MAX_PLOTS, START_PLOTS + self.perks.get("plots", 0)))]
        self.plots_bought = 0
        self.cellar_plots = [Plot() for _ in range(CELLAR_PLOTS)]
        self.cellar_unlocked = False
        self.relics = []
        self.mastery = {}
        self.counters = {"harvest": 0, "water": 0, "rounds": 0}
        self.shop_offers = []
        self.rerolls = 0
        self.quotas_paid = 0
        self.total_earned = 0
        self.won = False
        self.dead = False

        self.time_total = ROUND_TIME
        self.time_left = ROUND_TIME
        self.auto_harvest = False
        self.weather_cleared = False
        self.weather_roll_done = False
        self._suppress_blight = False
        self.chosen_plant = None
        self._chosen_ref = None
        self.started = False
        self.finished = False
        self.round_income = 0
        self.blight_done = False
        self.compost_announced = False
        self.crow_timer = 0.0
        self.hail_timer = 0.0
        self.rot_timer = 0.0
        self.ghost_timer = 0.0
        self.creep_grown = {False: 0, True: 0}
        self.events = []
        self.last_summary = None
        self.pending_bill = 0
        self._relic_lvls = {}
        self._effects_cache = (None, ())
        self.heirlooms_spent = 0

    def _emit(self, kind, **payload):
        if len(self.events) < MAX_EVENTS:
            self.events.append({"kind": kind, **payload})

    def perk(self, key):
        return self.perks.get(key, 0)

    def heirloom_cost(self, key):
        return data.perk_cost(key, self.perk(key))

    def heirloom_now(self, key, level=None):
        return data.perk_text(key, self.perk(key) if level is None else level)

    def buy_heirloom(self, key, banked):
        """Purchase the next permanent perk level from `banked` profile heirlooms.

        This run's own heirloom payout is credited only after the run ends, so
        `banked` is the sole balance and cannot be double-spent. Returns
        `(ok, message, cost)` where the caller deducts `cost` from the profile.
        """
        if key not in data.PERKS:
            return False, "No such heirloom.", 0
        perk = data.PERKS[key]
        level = self.perk(key)
        if level >= perk["max"]:
            return False, "Already maxed.", 0
        cost = self.heirloom_cost(key)
        if banked < cost:
            return False, "Not enough heirlooms.", cost
        self.perks[key] = level + 1
        self.heirlooms_spent += cost
        self._apply_perk(key)
        return True, "%s is level %d!" % (perk["name"], level + 1), cost

    def _apply_perk(self, key):
        """Grant immediate in-run benefits when a perk level is acquired mid-run."""
        if key == "plots" and len(self.plots) < MAX_PLOTS:
            self.plots.append(Plot())
            # Advance plots_bought so shop plot pricing continues scaling cleanly.
            self.plots_bought += 1
        elif key == "packs":
            self.packs.append(self.pick_free_pack_kind())
        elif key == "relics" and self.perk(key) == 3 and self.phase == "shop":
            # Add the new slot without rerolling existing or already sold offers.
            self._fill_relic_offers()

    def relic_level(self, rid):
        """Number of evolution thresholds met by `self.counters` for relic `rid`."""
        lv = 0
        for step in data.RELICS[rid].get("levels", []):
            if self.counters.get(step["stat"], 0) >= step["goal"]:
                lv += 1
            else:
                break
        return lv

    def refresh_relic_levels(self):
        """Record newly reached relic evolutions and emit one evolution event per threshold."""
        for rid in self.relics:
            lv = self.relic_level(rid)
            if lv > self._relic_lvls.get(rid, 0):
                self._relic_lvls[rid] = lv
                steps = data.RELICS[rid].get("levels", [])
                desc = steps[lv - 1]["desc"] if 0 <= lv - 1 < len(steps) else "EVOLVED!"
                self._emit("evolve", name=data.RELICS[rid]["name"], desc=desc)

    def _effects(self):
        """Return resolved effect dicts for owned relics, merging active level-up bonuses."""
        key = tuple((rid, self.relic_level(rid)) for rid in self.relics)
        if self._effects_cache[0] != key:
            resolved = []
            for rid, lv in key:
                eff = dict(data.RELICS[rid]["effects"])
                for step in data.RELICS[rid].get("levels", [])[:lv]:
                    for k, val in step["effects"].items():
                        if k == "yield_mult":
                            # Evolution steps describe an *increase* ("x2.25
                            # total" from a 1.5 relic and a 0.5 step), so each
                            # entry is a multiplier of (1 + amount), not a bare
                            # factor. Reading 0.5 as x0.5 used to make an
                            # evolved Scarecrow worse than an un-evolved one.
                            eff[k] = list(eff.get(k, [])) + [(tag, 1.0 + amount) for tag, amount in val]
                        elif isinstance(val, list):
                            eff[k] = list(eff.get(k, [])) + list(val)
                        elif isinstance(val, (int, float)) and not isinstance(val, bool):
                            eff[k] = eff.get(k, 0) + val
                        else:
                            eff[k] = val
                resolved.append(eff)
            self._effects_cache = (key, tuple(resolved))
        return self._effects_cache[1]

    def _sum(self, key):
        return sum(e.get(key, 0) for e in self._effects())

    def _has(self, key):
        return any(e.get(key) for e in self._effects())

    def _effects_product(self, key):
        p = 1.0
        for e in self._effects():
            p *= e.get(key, 1.0)
        return p

    @staticmethod
    def is_quota_round(rnd):
        return rnd % QUOTA_EVERY == 0

    @staticmethod
    def is_boss_round(rnd):
        return rnd % BOSS_EVERY == 0

    @staticmethod
    def quota_number(rnd):
        return rnd // QUOTA_EVERY

    def bill_for_round(self, rnd):
        return data.bill_for_quota(self.quota_number(rnd)) if self.is_quota_round(rnd) else 0

    def next_quota_round(self, rnd=None):
        rnd = self.round if rnd is None else rnd
        return ((rnd + QUOTA_EVERY - 1) // QUOTA_EVERY) * QUOTA_EVERY

    def bill_progress(self):
        """Snapshot cash progress toward the next unpaid bill and overall quota ladder."""
        already_paid = (
            self.is_quota_round(self.round)
            and (self.phase == "shop" or self.quotas_paid >= self.quota_number(self.round))
        )
        ref_round = self.round + 1 if already_paid else self.round
        qr = self.next_quota_round(ref_round)
        due_now = self.is_quota_round(self.round) and not already_paid
        bill = self.bill_for_round(qr)
        return {
            "quota_round": qr,
            "due_now": due_now,
            "rounds_until": max(0, qr - self.round),
            "bill": bill,
            "money": self.money,
            "fraction": min(1.0, self.money / bill) if bill > 0 else 1.0,
            "shortfall": max(0, bill - self.money),
            "quota_index": self.quota_number(qr),
            "quotas_paid": self.quotas_paid,
            "win_quotas": WIN_QUOTAS,
        }

    def twist_id(self, rnd=None):
        """Deterministically derive a round's weather twist from `(seed, round)` so forecasts never drift."""
        rnd = self.round if rnd is None else rnd
        # The first round is onboarding: keep it deterministic and fair. This
        # also prevents a seeded Eclipse from making the very first harvest
        # unexpectedly miss its normal five-second timing.
        if int(rnd) == 1:
            return "none"
        if self.is_boss_round(rnd):
            start = ((int(rnd) // BOSS_EVERY) - 1) % len(data.BOSS_TWISTS)
            # Keep the roster deterministic, but never schedule a seasonal boss
            # outside its allowed season. The current ordering naturally lands
            # the Ghost in Autumn; this guard keeps that rule true if the roster
            # or season length changes later.
            for offset in range(len(data.BOSS_TWISTS)):
                twist_id = data.BOSS_TWISTS[(start + offset) % len(data.BOSS_TWISTS)]
                twist = data.TWISTS[twist_id]
                if twist.get("autumn_only") and data.season(rnd)["name"] != "Autumn":
                    continue
                return twist_id
            return "none"
        if self.is_quota_round(rnd):
            k = self.quota_number(rnd)
            if k == 1:
                return "none"
            return random.Random(self.seed * 7919 + k).choice(data.RANDOM_TWISTS)
        roll_rng = random.Random(self.seed * 104729 + rnd)
        if roll_rng.random() < 0.6:
            return "none"
        return random.Random(self.seed * 104729 + rnd).choice(data.MINOR_TWISTS)

    def twist(self, rnd=None):
        if self.weather_cleared and (rnd is None or rnd == self.round):
            return data.TWISTS["none"]
        return data.TWISTS[self.twist_id(self.round if rnd is None else rnd)]

    def season(self, rnd=None):
        return data.season(self.round if rnd is None else rnd)

    def season_number(self, rnd=None):
        return data.season_number(self.round if rnd is None else rnd)

    def season_name(self, rnd=None):
        return self.season(rnd)["name"]

    def growth_speed(self):
        return (1.0 + self._sum("growth")) * self.twist()["growth"]

    def plant_disabled(self, i, cellar=False):
        """Return whether the active boss has made a planted plot dormant."""
        plots = self.cellar_plots if cellar else self.plots
        if cellar or not 0 <= i < len(plots) or not plots[i].species:
            return False
        return bool(self.twist().get("honey_only") and not data.produces_honey(plots[i].species))

    def plot_growth_speed(self, i, cellar=False):
        """Effective growth rate of plot `i`, including cellar, eclipse, and watering modifiers."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return 0.0
        p = plot_list[i]
        if cellar:
            return (1.0 + self._sum("growth")) * CELLAR_SPEED * (1.5 if self.is_chosen(i, cellar) else 1.0)
        if self.plant_disabled(i):
            return 0.0
        speed = self.growth_speed() * (1.5 if self.is_chosen(i, cellar) else 1.0)
        if p.species and self.twist().get("eclipse"):
            speed *= 1.3 if "nocturnal" in data.PLANTS[p.species]["tags"] else 0.8
        if p.water_left > 0:
            speed *= WATER_BOOST
        return speed

    def water_time(self):
        return WATER_TIME + self._sum("water_time")

    def round_time(self):
        late_reduction = max(0, self.round - 3) * LATE_ROUND_TIME_DROP
        base_time = max(LATE_ROUND_TIME_FLOOR, ROUND_TIME - late_reduction)
        return max(10, base_time + self._sum("round_time") + self.twist()["time"])

    def interest_rate(self):
        return self._sum("interest") + data.deep_pockets_rate(self.perk("cash"))

    def compost_window(self):
        return max((e.get("compost_window", 0.0) for e in self._effects()), default=0.0)

    def compost_mult(self):
        return self._effects_product("compost_mult")

    def compost_active(self):
        w = self.compost_window()
        return w > 0 and (self.started or self.finished) and self.time_left <= w + 1e-9

    def neighbours(self, i, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return []
        out = []
        r, c = divmod(i, COLS)
        if c > 0:
            out.append(i - 1)
        if c < COLS - 1 and i + 1 < len(plot_list):
            out.append(i + 1)
        if r > 0:
            out.append(i - COLS)
        if i + COLS < len(plot_list):
            out.append(i + COLS)
        return out

    def mycelium_network(self, i, cellar=False):
        """Indices of the connected mycelium patch that plot `i` belongs to.

        Connectivity is orthogonal adjacency on the same board, so a patch can
        snake around other crops and the whole network pays out together.
        """
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return []
        species = plot_list[i].species
        if not species or not data.PLANTS[species].get("network"):
            return []
        seen = {i}
        stack = [i]
        while stack:
            current = stack.pop()
            for n in self.neighbours(current, cellar):
                if n in seen:
                    continue
                other = plot_list[n].species
                if other and data.PLANTS[other].get("network"):
                    seen.add(n)
                    stack.append(n)
        return sorted(seen)

    def network_share(self, size):
        """Bonus multiplier a mycelium patch of `size` members applies to each of them."""
        if size <= 1:
            return 1.0
        return 1.0 + data.PLANTS["mycelium"]["network"] * (size - 1)

    def harvest_breakdown(self, i, cellar=False):
        """Compute `(chips, mult)` for plot `i` before final integer rounding."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return 0, 0.0
        plot = plot_list[i]
        if plot.species not in data.PLANTS:
            return 0, 0.0

        sp = data.PLANTS[plot.species]
        tags = sp["tags"]
        chips = float(sp["yield"]) + sp.get("mature_bonus", 0) * int(plot.mature_time + 1e-9)
        effects = self._effects()

        # Layout mechanics reshape the base harvest before relics multiply it.
        chips += plot.fed + plot.gorged
        if sp.get("network"):
            chips *= self.network_share(len(self.mycelium_network(i, cellar)))
        if plot.bloom != 1.0:
            chips *= plot.bloom
        chips = int(round(chips))

        for e in effects:
            for tag, amount in e.get("yield_add", []):
                if tag == "all" or tag in tags:
                    chips += amount
            for tag, needs, amount in e.get("adjacent", []):
                if tag in tags:
                    for n in self.neighbours(i, cellar):
                        other = plot_list[n].species
                        if other and needs in data.PLANTS[other]["tags"]:
                            chips += amount

        mult = 2.0 ** milestone_level(self.mastery.get(plot.species, 0))
        planted = [
            p.species
            for group in (self.plots, self.cellar_plots)
            for p in group
            if p.species
        ]
        distinct = len(set(planted))
        for e in effects:
            for tag, m in e.get("yield_mult", []):
                if tag == "all" or tag in tags:
                    mult *= m
            if e.get("distinct_bonus"):
                mult *= 1.0 + e["distinct_bonus"] * distinct
            if e.get("mono_mult") and distinct == 1 and len(planted) >= 2:
                mult *= e["mono_mult"]

        if sp.get("mutant"):
            mult *= 1.0 + self._sum("mutant_bonus")
        if self.compost_active():
            mult *= self.compost_mult()
        mult *= 1.0 + 0.10 * self.perk("yield")
        mult *= self.twist()["yield"]
        if self.is_chosen(i, cellar):
            mult *= 2.0

        if "cursed" not in tags:
            has_jealous = any(
                other.species and other is not plot and "aura" in data.PLANTS[other.species]
                for group in (self.plots, self.cellar_plots)
                for other in group
            )
            if has_jealous:
                mult *= 0.5
        return chips, mult

    def harvest_value(self, i, cellar=False):
        """Final integer payout for harvesting plot `i`.

        Uses half-up rounding (`floor(x + 0.5)`) rather than Python's round-to-even
        so +25% modifiers like Market Day still lift $2 yields to $3 instead of $2.
        """
        plot_list = self.cellar_plots if cellar else self.plots
        species = plot_list[i].species if 0 <= i < len(plot_list) else None
        if species and data.PLANTS[species].get("pays", True) is False:
            return 0
        chips, mult = self.harvest_breakdown(i, cellar)
        return max(1, int(math.floor(chips * min(mult, 1e250) + 0.5)))

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
        luck = self._effects_product("pack_luck") * data.PACKS[kind].get("luck", 1.0)
        pool = data.PACKS[kind]["pool"]
        ids = list(pool)
        weights = [
            pool[sid] * (luck if data.PLANTS[sid]["rarity"] in ("rare", "legendary") else 1.0)
            for sid in ids
        ]
        return self.rng.choices(ids, weights)[0]

    def open_pack(self):
        """Open the oldest queued pack and return `(kind, [seed_ids])`, or None if empty."""
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

    def can_plant(self, species, cellar=False):
        if species not in data.PLANTS:
            return False
        sp = data.PLANTS[species]
        nocturnal = "nocturnal" in sp["tags"]
        if cellar:
            # Fungi are the exception: they grow in the dark and up top.
            return nocturnal or "fungus" in sp["tags"]
        if nocturnal and not self.twist().get("eclipse"):
            return False
        ban = self.twist()["ban"]
        return not (ban and ban in sp["tags"])

    def plant(self, i, species, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)) or plot_list[i].species is not None:
            return False
        if self.seeds.get(species, 0) <= 0 or not self.can_plant(species, cellar):
            return False
        self.seeds[species] -= 1
        planted = self._starting_mutation(species)
        plot_list[i] = Plot(planted)
        if planted != species:
            self._emit("mutate", plot=i, cellar=cellar, name=data.PLANTS[planted]["name"])
        return True

    def is_chosen(self, i, cellar=False):
        plots = self.cellar_plots if cellar else self.plots
        return (self.chosen_plant == (bool(cellar), i) and 0 <= i < len(plots)
                and plots[i] is self._chosen_ref and plots[i].species is not None
                and self._has("choose_plant"))

    def choose_plant(self, i, cellar=False):
        plots = self.cellar_plots if cellar else self.plots
        if (self.phase != "round" or self.finished or not self._has("choose_plant")
                or self.chosen_plant is not None or not 0 <= i < len(plots)
                or not plots[i].species):
            return False
        self.chosen_plant = (bool(cellar), i)
        self._chosen_ref = plots[i]
        return True

    def harvest(self, i, cellar=False):
        plots = self.cellar_plots if cellar else self.plots
        if self.phase != "round" or not self.started or self.finished or not 0 <= i < len(plots):
            return False
        p = plots[i]
        if (not p.species or self.plant_disabled(i, cellar)
                or p.progress < data.PLANTS[p.species]["grow"]):
            return False
        self._harvest(i, cellar)
        p.progress = 0.0
        p.mature_time = 0.0
        return True

    def remove_plant(self, i, cellar=False):
        """Uproot the crop in plot `i` without refunding its seed."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)) or plot_list[i].species is None:
            return False, "Nothing planted there."
        name = data.PLANTS[plot_list[i].species]["name"]
        plot_list[i].clear()
        if self.chosen_plant == (bool(cellar), i):
            self.chosen_plant = (None, -1)
        return True, "Removed %s." % name

    def _starting_mutation(self, species):
        chance = self._sum("mutate_on_plant")
        if chance <= 0 or self.rng.random() >= chance:
            return species
        options = data.mutants_for(species)
        return self.rng.choice(options) if options else species

    def can_water(self, i, cellar=False):
        if cellar or not 0 <= i < len(self.plots):
            return False
        p = self.plots[i]
        return (self.started and not self.finished and p.species is not None
                and not self.plant_disabled(i) and p.water_cd <= 0)

    def water(self, i):
        if not self.can_water(i):
            return False
        p = self.plots[i]
        wt = self.water_time()
        p.water_left = wt
        p.water_cd = wt if self._has("auto_water") else wt + WATER_REST
        self.counters["water"] = self.counters.get("water", 0) + 1
        return True

    def buy_cellar(self):
        if self.cellar_unlocked or self.money < CELLAR_PRICE:
            return False
        self.money -= CELLAR_PRICE
        self.cellar_unlocked = True
        return True

    def begin_round(self):
        self.phase = "round"
        self.weather_cleared = False
        self.weather_roll_done = False
        self._suppress_blight = False
        self.chosen_plant = None
        self._chosen_ref = None
        self.pending_bill = 0
        self.time_total = self.round_time()
        self.time_left = self.time_total
        self.started = False
        self.finished = False
        self.blight_done = False
        self.compost_announced = False
        self.crow_timer = 0.0
        self.hail_timer = 0.0
        self.rot_timer = 0.0
        self.ghost_timer = 0.0
        self.creep_grown = {False: 0, True: 0}
        self.round_income = 0
        self.events = []
        for group in (self.plots, self.cellar_plots):
            for p in group:
                p.clear()

    def start_timer(self):
        self.started = True

    def finish_early(self):
        if self.started:
            self.finished = True

    def _advance(self, plot_list, cellar, speed, auto, dt):
        """Advance growth and watering timers on one board and resolve completed harvests."""
        tw = self.twist()
        eclipse = tw.get("eclipse")
        dry = tw.get("dry", 1.0)
        for i, p in enumerate(plot_list):
            if p.species is None:
                continue
            disabled = bool(not cellar and tw.get("honey_only") and not data.produces_honey(p.species))
            if disabled:
                # Queen Bee leaves non-honey plants completely dormant. Existing
                # water still expires, but growth, harvesting, and creep all stop.
                p.water_left = max(0.0, p.water_left - dt * dry)
                p.water_cd = max(0.0, p.water_cd - dt)
                continue
            if auto and not cellar and p.water_cd <= 0:
                self.water(i)
            boosted = 0.0 if cellar else min(dt, max(p.water_left, 0.0) / dry)
            plot_speed = speed
            if eclipse and not cellar:
                plot_speed *= 1.3 if "nocturnal" in data.PLANTS[p.species]["tags"] else 0.8
            if self.is_chosen(i, cellar):
                plot_speed *= 1.5
            grow = data.PLANTS[p.species]["grow"]
            if self.auto_harvest:
                p.progress += plot_speed * (dt + (WATER_BOOST - 1.0) * boosted)
                if p.progress >= grow and p.mature_time:
                    self._harvest(i, cellar)
                    p.progress -= grow
                    p.mature_time = 0.0
                guard = 0
                while p.progress >= data.PLANTS[p.species]["grow"] and guard < 1000:
                    p.progress -= data.PLANTS[p.species]["grow"]
                    self._harvest(i, cellar)
                    guard += 1
                if guard >= 1000:
                    p.progress = 0.0
            elif p.progress >= grow:
                p.progress = grow
                p.mature_time += dt
            else:
                # Water boost is applied first, then normal growth for the remainder.
                needed = grow - p.progress
                boosted_growth = plot_speed * WATER_BOOST * boosted
                total_growth = boosted_growth + plot_speed * (dt - boosted)
                if total_growth >= needed and plot_speed > 0:
                    reach = (needed / (plot_speed * WATER_BOOST) if needed <= boosted_growth
                             else boosted + (needed - boosted_growth) / plot_speed)
                    p.progress = grow
                    p.mature_time += max(0.0, dt - reach)
                else:
                    p.progress += total_growth
            if not cellar:
                p.water_left = max(0.0, p.water_left - dt * dry)
                p.water_cd = max(0.0, p.water_cd - dt)
        if cellar or not tw.get("honey_only"):
            self._creep_patches(plot_list, cellar, dt)

    def _ghost_swap(self):
        """Swap two surface plants, reset both growth cycles, and report the haunting."""
        alive = [i for i, p in enumerate(self.plots) if p.species]
        if len(alive) < 2:
            return False
        first, second = self.rng.sample(alive, 2)
        first_name = data.PLANTS[self.plots[first].species]["name"]
        second_name = data.PLANTS[self.plots[second].species]["name"]
        self.plots[first], self.plots[second] = self.plots[second], self.plots[first]
        for i in (first, second):
            self.plots[i].progress = 0.0
            self.plots[i].mature_time = 0.0

        # Chosen Bloom follows the plant rather than being stranded on its old soil.
        if self.chosen_plant == (False, first):
            self.chosen_plant = (False, second)
        elif self.chosen_plant == (False, second):
            self.chosen_plant = (False, first)

        self._emit(
            "ghost_swap", plot=first, other_plot=second, cellar=False,
            first_name=first_name, second_name=second_name,
        )
        return True

    def update(self, dt):
        """Step the active round, splitting at weather and Compost Heap boundaries."""
        if self.phase != "round" or not self.started or self.finished or dt <= 0:
            return
        dt = min(dt, self.time_left)
        # Split at both boundaries so growth, payouts and weather events use
        # the correct effects even when a single update crosses halfway.
        remaining = dt
        while remaining > 1e-9 and not self.finished:
            half = self.time_total / 2.0
            crosses_half = (not self.weather_roll_done and self.time_left > half
                            and self.time_left - remaining <= half)
            step = remaining
            if crosses_half:
                step = min(step, self.time_left - half)
            w = self.compost_window()
            if w > 0 and self.time_left > w > self.time_left - step:
                step = self.time_left - w
                crosses_half = False
            clearing = crosses_half and self._has("clear_weather") and self.rng.random() < 0.25
            self._suppress_blight = clearing
            self._step_round(step)
            self._suppress_blight = False
            remaining -= step
            if crosses_half:
                self.weather_roll_done = True
                if clearing:
                    self.weather_cleared = True
                    self._emit("weather_clear")

    def _announce_compost(self, window):
        if window > 0 and not self.compost_announced and self.time_left <= window + 1e-9:
            self.compost_announced = True
            self._emit("compost", window=int(window))

    def crow_pick(self, alive, twist=None):
        """Pick the plot the flock eats next, weighted by how tasty it looks.

        Every plant in `alive` has an equal chance except mutants, which the
        twist's `crow_mutant_weight` (0.8) marks as a less appealing meal, so a
        hard-won Golden Sunflower survives slightly more often than a Daisy in
        the same garden.
        """
        tw = self.twist() if twist is None else twist
        mutant_weight = float(tw.get("crow_mutant_weight", 1.0))
        weights = [
            mutant_weight if data.PLANTS[self.plots[i].species].get("mutant") else 1.0
            for i in alive
        ]
        return self.rng.choices(alive, weights=weights)[0]

    def _step_round(self, dt):
        if dt <= 0 or self.finished:
            return
        w = self.compost_window()
        self._announce_compost(w)

        tw = self.twist()
        auto = self._has("auto_water") or bool(tw.get("rain"))
        self._advance(self.plots, cellar=False, speed=self.growth_speed(), auto=auto, dt=dt)
        if self.cellar_unlocked:
            cellar_speed = (1.0 + self._sum("growth")) * CELLAR_SPEED
            self._advance(self.cellar_plots, cellar=True, speed=cellar_speed, auto=False, dt=dt)

        previous = self.time_left
        self.time_left -= dt
        if self.time_left > 1e-9:
            self._announce_compost(w)

        half = self.time_total / 2.0
        if tw["blight"] and not self._suppress_blight and not self.blight_done and previous > half >= self.time_left:
            self.blight_done = True
            alive = [i for i, p in enumerate(self.plots) if p.species]
            if alive:
                victim = self.rng.choice(alive)
                self._emit("wither", plot=victim, cellar=False)
                self.plots[victim].clear()

        crow = tw.get("crow")
        if crow:
            self.crow_timer += dt
            while self.crow_timer >= crow:
                self.crow_timer -= crow
                for _ in range(max(1, tw.get("crow_count", 1))):
                    alive = [i for i, p in enumerate(self.plots) if p.species]
                    if not alive:
                        break
                    victim = self.crow_pick(alive, tw)
                    eaten = data.PLANTS[self.plots[victim].species]["name"]
                    self.plots[victim].clear()
                    self._emit("eaten", plot=victim, cellar=False, name=eaten)

        hail = tw.get("hail")
        if hail:
            self.hail_timer += dt
            while self.hail_timer >= hail:
                self.hail_timer -= hail
                for i, p in enumerate(self.plots):
                    if p.species:
                        if p.progress < data.PLANTS[p.species]["grow"]:
                            p.progress *= 0.5
                        self._emit("hail", plot=i, cellar=False)

        rot = tw.get("rot")
        if rot:
            self.rot_timer += dt
            while self.rot_timer >= rot:
                self.rot_timer -= rot
                alive = [i for i, p in enumerate(self.plots) if p.species]
                if alive:
                    victim = self.rng.choice(alive)
                    name = data.PLANTS[self.plots[victim].species]["name"]
                    self.plots[victim].clear()
                    self._emit("rot", plot=victim, cellar=False, name=name)

        ghost = tw.get("ghost")
        if ghost:
            self.ghost_timer += dt
            while self.ghost_timer >= ghost:
                self.ghost_timer -= ghost
                self._ghost_swap()

        if self.time_left <= 1e-9:
            self.time_left = 0.0
            self.finished = True

    def _harvest(self, i, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        plot = plot_list[i]
        species = plot.species
        sp = data.PLANTS[species]

        # A Man-Eater feeds before it is paid, so the bite counts this harvest.
        if sp.get("consume"):
            self._devour(i, cellar)
        value = self.harvest_value(i, cellar)

        self.money += value
        self.round_income += value
        self.total_earned += value
        self.mastery[species] = self.mastery.get(species, 0) + 1
        self.counters["harvest"] = self.counters.get("harvest", 0) + 1
        for tag in sp["tags"]:
            self.counters[tag] = self.counters.get(tag, 0) + 1
        plot.harvests += 1
        self._emit("harvest", plot=i, amount=value, cellar=cellar)
        if sp.get("feed"):
            plot.fed = 0                        # the collected food is paid out
        if sp.get("bloom_chance"):
            self._clover_bloom(i, cellar)
        if sp.get("spread"):
            self._spread_mycelium(i, cellar)
        self._feed_flytraps(i, cellar)
        self.refresh_relic_levels()
        self._maybe_mutate(i, cellar)

    def _feed_flytraps(self, i, cellar=False):
        """Every harvest on the farm feeds each growing flytrap a little."""
        for board_cellar, group in ((False, self.plots), (True, self.cellar_plots)):
            for j, other in enumerate(group):
                if other.species is None or (j == i and board_cellar == cellar):
                    continue
                feed = data.PLANTS[other.species].get("feed", 0)
                if feed:
                    other.fed += feed

    def _devour(self, i, cellar=False):
        """A Man-Eater eats one orthogonal neighbour and keeps half its base harvest."""
        plot_list = self.cellar_plots if cellar else self.plots
        targets = [n for n in self.neighbours(i, cellar) if plot_list[n].species]
        if not targets:
            return
        victim_index = self.rng.choice(targets)
        victim = plot_list[victim_index].species
        gained = data.PLANTS[victim]["yield"] * 0.5
        plot_list[i].gorged += gained
        plot_list[victim_index].clear()
        self._emit(
            "devour", plot=victim_index, cellar=cellar,
            name=data.PLANTS[victim]["name"], gained=int(round(gained)),
        )

    def _clover_bloom(self, i, cellar=False):
        """Roll the lucky clover: sometimes a neighbouring plant gets a base-harvest boost."""
        plot_list = self.cellar_plots if cellar else self.plots
        sp = data.PLANTS[plot_list[i].species]
        chance = sp.get("bloom_chance", 0.0)
        if chance <= 0 or self.rng.random() >= chance:
            return
        targets = [
            n for n in self.neighbours(i, cellar)
            if plot_list[n].species and data.PLANTS[plot_list[n].species].get("pays", True) is not False
        ]
        if not targets:
            return
        target = self.rng.choice(targets)
        mult = sp.get("bloom_mult", 1.5)
        plot_list[target].bloom *= mult
        self._emit(
            "bloom", plot=target, cellar=cellar, mult=mult,
            name=data.PLANTS[plot_list[target].species]["name"],
        )

    def _is_creeping(self, plot_list, i):
        """True when plot `i` is a mycelium that spreads from where it stands."""
        p = plot_list[i]
        return p.species is not None and bool(data.PLANTS[p.species].get("spread"))

    def _can_creep(self, plot_list, i, cellar):
        """A mycelium can take a plot only if it has an empty orthogonal neighbour."""
        return self._is_creeping(plot_list, i) and any(
            plot_list[n].species is None for n in self.neighbours(i, cellar)
        )

    def _spread_cap(self, plot_list, i):
        """How many plots one mycelium seed may grow this round (from `data`)."""
        sp = data.PLANTS[plot_list[i].species]
        return int(sp.get("spread_cap", MYCELIUM_MAX_SPREAD))

    def creep_cap(self, plot_list, i):
        """Public cap lookup so the round screen can show how much patch is left."""
        return self._spread_cap(plot_list, i)

    def _creep_from(self, plot_list, i, cellar, chance=1.0):
        """Roll plot `i`'s chance to push into one empty orthogonal neighbour.

        The new plot starts a fresh mycelium of the same species, and the patch
        may only grow `spread_cap` plots this round, so one lucky seed cannot
        take over the garden for free.
        """
        p = plot_list[i]
        if chance <= 0 or self.creep_grown.get(cellar, 0) >= self._spread_cap(plot_list, i):
            return False
        if chance < 1.0 and self.rng.random() >= chance:
            return False
        empties = [n for n in self.neighbours(i, cellar) if plot_list[n].species is None]
        if not empties:
            return False
        target = self.rng.choice(empties)
        plot_list[target] = Plot(p.species)
        # The parent's creep meter pays for the new plot and starts filling again.
        p.creep_cd = 0.0
        self.creep_grown[cellar] = self.creep_grown.get(cellar, 0) + 1
        self._emit(
            "spread", plot=target, cellar=cellar,
            source=i, size=len(self.mycelium_network(target, cellar)),
        )
        return True

    def _spread_mycelium(self, i, cellar=False):
        """Harvest-spread: harvesting any mycelium rolls for the patch to grow.

        `spread` in `data.PLANTS` scales the chance on each harvest, tempered by
        MYCELIUM_CREEP_SHARE so a fast mycelium does not outrun its guaranteed
        creep. The roll is the patch's, not the harvested plot's, so a mycelium
        that has already surrounded itself still pushes the fungus outward.
        """
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)):
            return False
        sp = data.PLANTS[plot_list[i].species]
        chance = sp.get("spread", 0.0) * MYCELIUM_CREEP_SHARE
        if chance <= 0 or self.rng.random() >= chance:
            return False
        front = self._patch_front(plot_list, cellar, i)
        if front is None:
            return False
        return self._creep_from(plot_list, front, cellar, 1.0)

    def _patch_front(self, plot_list, cellar, near=None):
        """The mycelium plot that should grow next: the patch's outer edge.

        Growth stems from whichever member has the most room around it, which
        makes the fungus expand as a blob instead of backfilling gaps behind
        the front. Ties go to the plot nearest `near`, then to the lower index.
        """
        ready = [j for j in range(len(plot_list)) if self._can_creep(plot_list, j, cellar)]
        if not ready:
            return None
        anchor = None
        if near is not None and 0 <= near < len(plot_list):
            anchor = divmod(near, COLS)
        def key(j):
            r, c = divmod(j, COLS)
            dist = 0 if anchor is None else abs(r - anchor[0]) + abs(c - anchor[1])
            room = sum(1 for n in self.neighbours(j, cellar) if plot_list[n].species is None)
            return (room, -dist, j)
        return max(ready, key=key)

    def _creep_patches(self, plot_list, cellar, dt):
        """Fill every mycelium's creep meter and book the guaranteed spreads.

        MYCELIUM_CREEP_TIME seconds of round per new plot, so a lone seed always
        becomes a patch you can watch grow; harvest rolls in `_spread_mycelium`
        make the good rounds much faster. A meter only fills while its plot has
        an empty neighbour, so a walled-in mycelium never banks free expansions.
        """
        for i, p in enumerate(plot_list):
            if not self._can_creep(plot_list, i, cellar):
                continue
            cap = self._spread_cap(plot_list, i)
            if self.creep_grown.get(cellar, 0) >= cap:
                continue
            p.creep_cd = min(MYCELIUM_CREEP_TIME, p.creep_cd + dt)
        while True:
            front = self._patch_front(plot_list, cellar)
            if front is None or plot_list[front].creep_cd < MYCELIUM_CREEP_TIME:
                break
            if not self._creep_from(plot_list, front, cellar, 1.0):
                break

    def _maybe_mutate(self, i, cellar=False):
        """Roll for mid-round species mutation once a plot clears its harvest threshold."""
        plot_list = self.cellar_plots if cellar else self.plots
        plot = plot_list[i]
        if plot.species not in data.PLANTS or plot.harvests < data.mutation_threshold(plot.species):
            return
        options = data.mutants_for(plot.species)
        if not options or self.rng.random() >= MUTATION_CHANCE:
            return
        mid = self.rng.choice(options)
        plot.species = mid
        plot.harvests = 0
        self._emit("mutate", plot=i, cellar=cellar, name=data.PLANTS[mid]["name"])

    def end_round(self):
        """Liquidate planted crops proportionally, deduct cursed upkeep, pay interest, and stage any bill."""
        in_compost = self.compost_active()
        sale_mult = self.compost_mult() if in_compost else 1.0

        upkeep = 0
        sale = 0
        for group in (self.plots, self.cellar_plots):
            for p in group:
                if p.species:
                    sp = data.PLANTS[p.species]
                    upkeep += sp.get("upkeep", 0)
                    frac = min(1.0, p.progress / sp["grow"])
                    sale += int(sp["sell"] * frac * sale_mult)
                p.clear()

        self.money += sale
        self.total_earned += sale
        self.money = max(0, self.money - upkeep)

        rate = self.interest_rate()
        interest = max(1, int(round(self.money * rate, 9))) if (self.money > 0 and rate > 0) else 0
        self.money += interest
        self.total_earned += interest
        self.counters["rounds"] = self.counters.get("rounds", 0) + 1
        self.refresh_relic_levels()

        bill = self.bill_for_round(self.round)
        self.pending_bill = bill

        self.last_summary = {
            "round": self.round,
            "harvest": self.round_income,
            "earned": self.round_income + sale + interest,
            "net": self.round_income + sale + interest - upkeep,
            "sale": sale,
            "interest": interest,
            "interest_rate": rate,
            "bill": bill,
            "paid": None,
            "money": self.money,
            "upkeep": upkeep,
            "victory": False,
            "twist": self.twist_id(self.round),
            "pending_bill": bool(bill),
            "can_afford": (self.money >= bill) if bill else True,
            "shortfall": max(0, bill - self.money) if bill else 0,
        }
        self.phase = "summary"
        return self.last_summary

    def pay_pending_bill(self):
        bill = self.pending_bill
        if not bill:
            return True, "No bill due."
        if self.money < bill:
            return False, "Not enough money for the bill."
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
        """Meta-currency earned at run end: +1 per completed round, +3 per bill paid, +10 on victory."""
        earned = max(0, self.round - 1) + 3 * self.quotas_paid
        return earned + 10 if self.won else earned

    def enter_shop(self):
        self.phase = "shop"
        self.rerolls = 0
        self.roll_offers()

    def relic_slots(self):
        return RELIC_SLOTS + (1 if self.perk("relics") >= 2 else 0)

    def relic_offer_slots(self):
        return 3 + (1 if self.perk("relics") >= 3 else 0)

    def roll_offers(self):
        self.shop_offers = []
        self._fill_relic_offers()

    def _fill_relic_offers(self):
        offers = self.shop_offers
        pool = [r for r in data.RELIC_ORDER if r not in self.relics and r not in offers]
        for _ in range(max(0, self.relic_offer_slots() - len(offers))):
            if not pool:
                break
            weights = [data.RARITY_WEIGHT[data.RELICS[r]["rarity"]] for r in pool]
            pick = self.rng.choices(pool, weights)[0]
            pool.remove(pick)
            offers.append(pick)
        self.shop_offers = offers

    def relic_price(self, rid):
        """Price of relic `rid` for the current round; rare relics scale slightly steeper."""
        rarity = data.RELICS[rid]["rarity"]
        rarity_mult = {"common": 1.0, "uncommon": 1.2, "rare": 1.45, "legendary": 1.6, "exquisite": 1.8}[rarity]
        growth = RARE_RELIC_PRICE_GROWTH if rarity in ("rare", "exquisite") else RELIC_PRICE_GROWTH
        return int(data.RELICS[rid]["cost"] * rarity_mult * growth ** (self.round - 1) * (0.85 if self.perk("relics") >= 1 else 1.0))

    def reroll_price(self):
        return int(REROLL_BASE_PRICE * 2.0 ** self.rerolls * RELIC_PRICE_GROWTH ** (self.round - 1))

    def reroll(self):
        price = self.reroll_price()
        if self.money < price:
            return False
        self.money -= price
        self.rerolls += 1
        self.roll_offers()
        return True

    def buy_relic(self, index):
        if not (0 <= index < len(self.shop_offers)) or self.shop_offers[index] is None:
            return False, "Nothing there."
        if len(self.relics) >= self.relic_slots():
            return False, "Relic slots are full."
        rid = self.shop_offers[index]
        price = self.relic_price(rid)
        if self.money < price:
            return False, "Not enough money."
        self.money -= price
        self.relics.append(rid)
        self._relic_lvls[rid] = self.relic_level(rid)
        self.shop_offers[index] = None
        return True, "Bought %s!" % data.RELICS[rid]["name"]

    def sell_relic(self, index):
        if not 0 <= index < len(self.relics):
            return False, "No relic there.", 0
        rid = self.relics.pop(index)
        self._relic_lvls.pop(rid, None)
        refund = max(1, int(self.relic_price(rid) * 0.5))
        self.money += refund
        return True, "Sold %s for $%d!" % (data.RELICS[rid]["name"], refund), refund

    def seed_price(self, species):
        """Cash one unplanted seed fetches: a slice of the grown plant's sale value.

        End-of-round sales pay `sell` for a fully grown plant, so a seed is worth
        SEED_SELL_SHARE of that - never less than $1, so even a Daisy seed has a
        price on its head.
        """
        sp = data.PLANTS.get(species)
        if not sp:
            return 0
        return max(1, int(sp["sell"] * SEED_SELL_SHARE))

    def sell_seed(self, species, count=1):
        """Sell `count` seeds of one species; returns `(ok, message, refund)`."""
        owned = self.seeds.get(species, 0)
        if species not in data.PLANTS or owned <= 0:
            return False, "No seeds to sell.", 0
        count = max(1, min(int(count), owned))
        unit = self.seed_price(species)
        refund = unit * count
        left = owned - count
        if left > 0:
            self.seeds[species] = left
        else:
            self.seeds.pop(species, None)
        self.money += refund
        name = data.PLANTS[species]["name"]
        return True, "Sold %d %s seed%s for $%d!" % (count, name, "" if count == 1 else "s", refund), refund

    def plot_price(self):
        return int(PLOT_BASE_PRICE * PLOT_PRICE_GROWTH ** self.plots_bought)

    def can_buy_plot(self):
        return len(self.plots) < MAX_PLOTS or len(self.cellar_plots) < MAX_PLOTS

    def next_plot_is_cellar(self):
        return len(self.plots) >= MAX_PLOTS and len(self.cellar_plots) < MAX_PLOTS

    def buy_plot(self):
        price = self.plot_price()
        if not self.can_buy_plot() or self.money < price:
            return False
        self.money -= price
        self.plots_bought += 1
        if len(self.plots) < MAX_PLOTS:
            self.plots.append(Plot())
        else:
            self.cellar_unlocked = True
            self.cellar_plots.append(Plot())
        return True

    def start_next_round(self):
        self.weather_cleared = False
        self.round += 1
        self.phase = "packs"
        self.grant_round_packs()

    def to_dict(self):
        version, internal, gauss = self.rng.getstate()
        return {
            "v": 1, "seed": self.seed, "rng": [version, list(internal), gauss],
            "perks": self.perks, "round": self.round, "phase": self.phase,
            "money": self.money, "seeds": self.seeds, "packs": self.packs,
            "plots": [p.to_dict() for p in self.plots], "plots_bought": self.plots_bought,
            "cellar_plots": [p.to_dict() for p in self.cellar_plots],
            "cellar_unlocked": self.cellar_unlocked,
            "relics": self.relics, "mastery": self.mastery, "counters": self.counters,
            "shop_offers": self.shop_offers, "rerolls": self.rerolls,
            "quotas_paid": self.quotas_paid, "total_earned": self.total_earned,
            "won": self.won, "dead": self.dead, "pending_bill": self.pending_bill,
            "heirlooms_spent": self.heirlooms_spent, "last_summary": self.last_summary,
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
        cellar = [Plot.from_dict(p) for p in d.get("cellar_plots", [])]
        if cellar:
            run.cellar_plots = cellar[:MAX_PLOTS]
        run.cellar_unlocked = bool(d.get("cellar_unlocked", False))
        run.relics = [r for r in d.get("relics", []) if r in data.RELICS][:run.relic_slots()]
        run.mastery = {k: int(v) for k, v in d.get("mastery", {}).items() if k in data.PLANTS}
        run.counters = {k: int(v) for k, v in d.get("counters", {}).items()}
        run.shop_offers = [r if r in data.RELICS else None for r in d.get("shop_offers", [])]
        run.rerolls = int(d.get("rerolls", 0))
        run.quotas_paid = int(d.get("quotas_paid", 0))
        run.total_earned = int(d.get("total_earned", 0))
        run.won = bool(d.get("won", False))
        run.dead = bool(d.get("dead", False))
        run.pending_bill = int(d.get("pending_bill", 0))
        run.heirlooms_spent = int(d.get("heirlooms_spent", 0))
        saved_summary = d.get("last_summary")
        if isinstance(saved_summary, dict):
            run.last_summary = dict(saved_summary)
        else:
            run.last_summary = {
                "round": run.round, "bill": run.pending_bill, "paid": None,
                "money": run.money, "pending_bill": bool(run.pending_bill),
            }
        if run.phase == "shop" and not run.shop_offers:
            run.roll_offers()
        run._relic_lvls = {rid: run.relic_level(rid) for rid in run.relics}
        for group in (run.plots, run.cellar_plots):
            for p in group:
                p.clear()
        return run
