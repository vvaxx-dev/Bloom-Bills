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
        MUTATION_CHANCE, PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WIN_QUOTAS,
    )
except ImportError:
    import data
    from settings import (
        BASE_FREE_PACKS, BOSS_EVERY, CELLAR_PLOTS, CELLAR_PRICE, CELLAR_SPEED,
        COLS, LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, MAX_PLOTS,
        MUTATION_CHANCE, PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WIN_QUOTAS,
    )

MAX_EVENTS = 300


def milestone_level(count):
    """Number of harvest-mastery thresholds reached; each level doubles species yield."""
    return sum(1 for t in data.MILESTONES if count >= t)


class Plot:
    """State of a single soil plot on either the surface garden or underground cellar."""

    __slots__ = ("species", "progress", "water_left", "water_cd", "harvests")

    def __init__(self, species=None, progress=0.0, water_left=0.0, water_cd=0.0, harvests=0):
        self.species = species
        self.progress = progress
        self.water_left = water_left
        self.water_cd = water_cd
        self.harvests = harvests

    def clear(self):
        self.species = None
        self.progress = 0.0
        self.water_left = 0.0
        self.water_cd = 0.0
        self.harvests = 0

    def to_dict(self):
        return {
            "species": self.species, "progress": self.progress,
            "water_left": self.water_left, "water_cd": self.water_cd,
            "harvests": self.harvests,
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
        self.started = False
        self.finished = False
        self.round_income = 0
        self.blight_done = False
        self.compost_announced = False
        self.crow_timer = 0.0
        self.hail_timer = 0.0
        self.rot_timer = 0.0
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
                        if isinstance(val, list):
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
        if self.is_boss_round(rnd):
            return data.BOSS_TWISTS[((rnd // BOSS_EVERY) - 1) % len(data.BOSS_TWISTS)]
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
        return data.TWISTS[self.twist_id(self.round if rnd is None else rnd)]

    def season(self, rnd=None):
        return data.season(self.round if rnd is None else rnd)

    def season_number(self, rnd=None):
        return data.season_number(self.round if rnd is None else rnd)

    def season_name(self, rnd=None):
        return self.season(rnd)["name"]

    def growth_speed(self):
        return (1.0 + self._sum("growth")) * self.twist()["growth"]

    def plot_growth_speed(self, i, cellar=False):
        """Effective growth rate of plot `i`, including cellar, eclipse, and watering modifiers."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return 0.0
        p = plot_list[i]
        if cellar:
            return (1.0 + self._sum("growth")) * CELLAR_SPEED
        speed = self.growth_speed()
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
        chips = sp["yield"]
        effects = self._effects()

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
            return nocturnal
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

    def remove_plant(self, i, cellar=False):
        """Uproot the crop in plot `i` without refunding its seed."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)) or plot_list[i].species is None:
            return False, "Nothing planted there."
        name = data.PLANTS[plot_list[i].species]["name"]
        plot_list[i].clear()
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
        return self.started and not self.finished and p.species is not None and p.water_cd <= 0

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
            if auto and not cellar and p.water_cd <= 0:
                self.water(i)
            boosted = 0.0 if cellar else min(dt, max(p.water_left, 0.0))
            plot_speed = speed
            if eclipse and not cellar:
                plot_speed *= 1.3 if "nocturnal" in data.PLANTS[p.species]["tags"] else 0.8
            p.progress += plot_speed * (dt + (WATER_BOOST - 1.0) * boosted)
            if not cellar:
                p.water_left = max(0.0, p.water_left - dt * dry)
                p.water_cd = max(0.0, p.water_cd - dt)
            grow = data.PLANTS[p.species]["grow"]
            guard = 0
            while p.progress >= grow and guard < 1000:
                p.progress -= grow
                self._harvest(i, cellar)
                guard += 1
            if guard >= 1000:
                p.progress = 0.0

    def update(self, dt):
        """Step the active round forward by `dt`, splitting across the Compost Heap boundary."""
        if self.phase != "round" or not self.started or self.finished or dt <= 0:
            return
        dt = min(dt, self.time_left)
        w = self.compost_window()
        if w > 0 and self.time_left > w > self.time_left - dt:
            first_dt = self.time_left - w
            self._step_round(first_dt)
            if not self.finished and dt - first_dt > 0:
                self._step_round(dt - first_dt)
        else:
            self._step_round(dt)

    def _announce_compost(self, window):
        if window > 0 and not self.compost_announced and self.time_left <= window + 1e-9:
            self.compost_announced = True
            self._emit("compost", window=int(window))

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
        if tw["blight"] and not self.blight_done and previous > half >= self.time_left:
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
                    victim = self.rng.choice(alive)
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

        if self.time_left <= 1e-9:
            self.time_left = 0.0
            self.finished = True

    def _harvest(self, i, cellar=False):
        value = self.harvest_value(i, cellar)
        plot_list = self.cellar_plots if cellar else self.plots
        species = plot_list[i].species
        self.money += value
        self.round_income += value
        self.total_earned += value
        self.mastery[species] = self.mastery.get(species, 0) + 1
        self.counters["harvest"] = self.counters.get("harvest", 0) + 1
        for tag in data.PLANTS[species]["tags"]:
            self.counters[tag] = self.counters.get(tag, 0) + 1
        plot_list[i].harvests += 1
        self._emit("harvest", plot=i, amount=value, cellar=cellar)
        self.refresh_relic_levels()
        self._maybe_mutate(i, cellar)

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
        """Price of relic `rid` for the current round; rare relics scale slightly steeper."""
        rarity = data.RELICS[rid]["rarity"]
        rarity_mult = {"common": 1.0, "uncommon": 1.2, "rare": 1.45, "legendary": 1.6}[rarity]
        growth = RARE_RELIC_PRICE_GROWTH if rarity == "rare" else RELIC_PRICE_GROWTH
        return int(data.RELICS[rid]["cost"] * rarity_mult * growth ** (self.round - 1))

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
        if len(self.relics) >= RELIC_SLOTS:
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

    def plot_price(self):
        return int(PLOT_BASE_PRICE * PLOT_PRICE_GROWTH ** self.plots_bought)

    def buy_plot(self):
        price = self.plot_price()
        if len(self.plots) >= MAX_PLOTS or self.money < price:
            return False
        self.money -= price
        self.plots_bought += 1
        self.plots.append(Plot())
        return True

    def start_next_round(self):
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
            run.cellar_plots = cellar[:CELLAR_PLOTS]
        run.cellar_unlocked = bool(d.get("cellar_unlocked", False))
        run.relics = [r for r in d.get("relics", []) if r in data.RELICS][:RELIC_SLOTS]
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
