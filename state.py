"""Headless run simulation: garden plots, weather twists, relics, quotas, and serialization.

Imports no graphics libraries so balance tests and simulations can run without a display.
"""

from __future__ import annotations

import math
import random

try:
    from . import data
    from .settings import (
        APHID_SALE, APHID_YIELD, BASE_FREE_PACKS, BOSS_EVERY, CELLAR_PLOTS, CELLAR_PRICE,
        CELLAR_SPEED, CLEAR_SKIES_CHANCE, COLS, CONTAGION_CHANCE, CRITTER_FEED_VALUE,
        DISEASE_GROWTH, DISEASE_SALE, DISEASE_YIELD,
        LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, MAX_PLOTS,
        METEOR_BONUS, METEOR_DESTROY,
        MUTATION_CHANCE, MYCELIUM_CREEP_SHARE, MYCELIUM_CREEP_TIME, MYCELIUM_MAX_SPREAD,
        PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEED_SELL_SHARE, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WEED_FEE, WEED_SEED_CHANCE, WIN_QUOTAS,
    )
except ImportError:
    import data
    from settings import (
        APHID_SALE, APHID_YIELD, BASE_FREE_PACKS, BOSS_EVERY, CELLAR_PLOTS, CELLAR_PRICE,
        CELLAR_SPEED, CLEAR_SKIES_CHANCE, COLS, CONTAGION_CHANCE, CRITTER_FEED_VALUE,
        DISEASE_GROWTH, DISEASE_SALE, DISEASE_YIELD,
        LATE_ROUND_TIME_DROP, LATE_ROUND_TIME_FLOOR, MAX_PLOTS,
        METEOR_BONUS, METEOR_DESTROY,
        MUTATION_CHANCE, MYCELIUM_CREEP_SHARE, MYCELIUM_CREEP_TIME, MYCELIUM_MAX_SPREAD,
        PLOT_BASE_PRICE, PLOT_PRICE_GROWTH, PRICE_GROWTH,
        QUOTA_EVERY, RARE_RELIC_PRICE_GROWTH, RELIC_PRICE_GROWTH, RELIC_SLOTS,
        REROLL_BASE_PRICE, ROUND_TIME, SEED_SELL_SHARE, SEEDS_PER_PACK, START_MONEY,
        START_PLOTS, WATER_BOOST, WATER_REST, WATER_TIME, WEED_FEE, WEED_SEED_CHANCE, WIN_QUOTAS,
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

    Mycelium adds `creep_cd`: seconds the patch's shared creep meter has banked.
    When it fills, one mycelium grows into an empty orthogonal neighbour and
    the whole patch starts filling again, so a patch keeps advancing round
    after round instead of sitting still.

    Hazard state lives here too, and all four flags are per-plot and per-round,
    so shovelling (which calls `clear()`) is a complete cure:
    `sick` is Disease, `aphids` is a settled colony that watering washes off,
    `starlit` is a meteor's rewrite (or stardust left in bare soil), and `weed`
    marks ground too choked to plant in.
    """

    __slots__ = ("species", "progress", "water_left", "water_cd", "harvests", "fed", "gorged", "bloom",
                 "creep_cd", "mature_time", "sick", "aphids", "starlit", "weed")

    def __init__(self, species=None, progress=0.0, water_left=0.0, water_cd=0.0, harvests=0,
                fed=0, gorged=0.0, bloom=1.0, creep_cd=0.0, mature_time=0.0,
                sick=False, aphids=False, starlit=False, weed=False):
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
        self.sick = bool(sick)
        self.aphids = bool(aphids)
        self.starlit = bool(starlit)
        self.weed = bool(weed)

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
        self.sick = False
        self.aphids = False
        self.starlit = False
        self.weed = False

    def to_dict(self):
        return {
            "species": self.species, "progress": self.progress,
            "water_left": self.water_left, "water_cd": self.water_cd,
            "harvests": self.harvests, "fed": self.fed,
            "gorged": self.gorged, "bloom": self.bloom,
            "creep_cd": self.creep_cd,
            "mature_time": self.mature_time,
            "sick": self.sick, "aphids": self.aphids,
            "starlit": self.starlit, "weed": self.weed,
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
            bool(d.get("sick", False)),
            bool(d.get("aphids", False)),
            bool(d.get("starlit", False)),
            bool(d.get("weed", False)),
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
        # Endless play: after paying the eighth bill the farm is won. The
        # player then chooses to retire (run ends) or keep farming. Kept in
        # the save so a reload cannot skip the choice.
        self.endless = False
        self.retired = False

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
        self.bill_waivers = 1 if self.perks.get("insurance", 0) else 0
        self.insurance_used = False
        self.free_offer = None
        self.stock_species = None
        self.capsule_timer = 0.0
        self.capsule_income = 0
        self.owl_timer = 0.0
        self.snail_bitten = False
        # Crossbreed seeds discovered this run; the app mirrors these into
        # the persistent profile so the Garden Index stays revealed forever.
        self.discovered_crossbreeds = set()
        # Story beats already played this run (see `tutorial.py`). Kept in run.json
        # so reloading a save does not replay a beat the player has seen.
        self.story_beats = []
        # Hazard timers: each only advances while its twist is the forecast,
        # and they are reset by `begin_round` along with the per-plot flags.
        self.disease_timer = 0.0
        self.contagion_timer = 0.0
        self.meteor_timer = 0.0
        self.weed_timer = 0.0
        self.aphid_timer = 0.0
        self.weeds_this_round = 0

    def _emit(self, kind, **payload):
        if len(self.events) < MAX_EVENTS:
            self.events.append({"kind": kind, **payload})

    def story_beat_seen(self, beat_id):
        """Whether Moss has already played this story beat during this run."""
        return beat_id in self.story_beats

    def mark_story_beat(self, beat_id):
        """Record a played story beat so a reload does not repeat the dialogue."""
        if beat_id not in self.story_beats:
            self.story_beats.append(beat_id)

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
        elif key == "insurance" and not self.insurance_used:
            self.bill_waivers = 1

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

    def _planted_species(self):
        return [p.species for group in (self.plots, self.cellar_plots) for p in group if p.species]

    def _synergy_count(self, syn):
        planted = self._planted_species()
        if syn.get("mono"):
            return len(planted) if planted and len(set(planted)) == 1 else 0
        if syn.get("distinct"):
            return len(set(planted))
        if syn.get("mutant"):
            return sum(1 for sid in planted if data.PLANTS[sid].get("mutant"))
        if syn.get("rarity"):
            return sum(1 for sid in planted
                       if data.PLANTS[sid].get("rarity") in syn["rarity"])
        tag = syn.get("tag")
        if tag:
            return sum(1 for sid in planted if tag in data.PLANTS[sid]["tags"])
        species = syn.get("species")
        if species:
            return sum(1 for sid in planted if sid == species or data.PLANTS[sid].get("base") == species)
        return 0

    def _synergy_active(self, syn):
        if syn.get("weather") and not self.twist().get(syn["weather"]):
            return False
        return self._synergy_count(syn) >= syn.get("min", 1)

    def active_synergies(self):
        """Return `(relic_id, synergy)` pairs currently lit up by the garden."""
        out = []
        for rid in self.relics:
            syn = data.RELIC_SYNERGIES.get(rid)
            if syn and self._synergy_active(syn):
                out.append((rid, syn))
        return out

    def active_synergy_ids(self):
        """Set of owned relic ids whose plant pairing is currently active."""
        return {rid for rid, _syn in self.active_synergies()}

    @staticmethod
    def _synergy_matches_plant(syn, species):
        if species not in data.PLANTS:
            return False
        if syn.get("all") or syn.get("mono") or syn.get("distinct"):
            return True
        if syn.get("mutant"):
            return bool(data.PLANTS[species].get("mutant"))
        if syn.get("rarity"):
            return data.PLANTS[species].get("rarity") in syn["rarity"]
        tag = syn.get("tag")
        if tag:
            return tag in data.PLANTS[species]["tags"]
        wanted = syn.get("species")
        if wanted:
            return species == wanted or data.PLANTS[species].get("base") == wanted
        return False

    def relic_power(self):
        """Global multiplier on relic-derived growth from The Collector."""
        power = 1.0 + self._sum("relic_power") * len(set(self._planted_species()))
        syn = data.RELIC_SYNERGIES.get("collector")
        if syn and self._synergy_active(syn):
            # Five or more species make the collection itself stronger.
            power = 1.0 + (power - 1.0) * (1.0 + syn.get("power", 0.0))
        return power

    def _relic_scale(self, rid):
        """How strongly one relic's harvest effects apply this instant."""
        scale = self.relic_power()
        syn = data.RELIC_SYNERGIES.get(rid)
        if syn and self._synergy_active(syn):
            scale *= 1.0 + syn.get("power", 0.0)
        return scale

    def synergy_growth(self, species):
        bonus = 0.0
        for _rid, syn in self.active_synergies():
            if self._synergy_matches_plant(syn, species):
                bonus += syn.get("growth", 0.0)
        return bonus

    def synergy_harvest(self, species):
        bonus = 0.0
        for _rid, syn in self.active_synergies():
            if self._synergy_matches_plant(syn, species):
                bonus += syn.get("harvest", 0.0)
        return bonus

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
        # The Collector scales relic growth bonuses, and the Emergency
        # Generator pushes back against bad-weather slowdowns.
        power = self.relic_power()
        base = 1.0 + self._sum("growth") * power
        weather = self.twist()["growth"]
        backup = self._sum("bad_weather_growth") * power
        if backup and self.twist().get("tone") == "bad":
            weather *= 1.0 + backup
        return base * weather

    def cellar_growth_speed(self):
        """Cellar crops are weatherproof, but the Generator still powers them."""
        power = self.relic_power()
        speed = (1.0 + self._sum("growth") * power) * CELLAR_SPEED
        backup = self._sum("bad_weather_growth") * power
        if backup and self.twist().get("tone") == "bad":
            speed *= 1.0 + backup
        return speed

    def plant_disabled(self, i, cellar=False):
        """Return whether the active boss has made a planted plot dormant."""
        plots = self.cellar_plots if cellar else self.plots
        if cellar or not 0 <= i < len(plots) or not plots[i].species:
            return False
        return bool(self.twist().get("honey_only") and not data.produces_honey(plots[i].species))

    def _effective_twist_id(self):
        """Twist id actually in force (Clear Skies rewrites it to Fair Weather)."""
        return "none" if self.weather_cleared else self.twist_id()

    def _plant_speed_mult(self, species, cellar=False):
        """Per-species weather/season growth multiplier for crossbreed traits.

        Solar Saffron leans into sunshine, the Spiny Pumpkin treats drought
        and heatwaves as fair sun, and the Ghost Bloom hurries in Autumn.
        Weather traits only bite on the surface; the cellar is weatherproof,
        but the season still reaches it.
        """
        if species not in data.PLANTS:
            return 1.0
        sp = data.PLANTS[species]
        mult = 1.0
        season_mult = sp.get("season_growth", {}).get(self.season_name())
        if season_mult:
            mult *= season_mult
        if cellar:
            return mult
        twist_id = self._effective_twist_id()
        twist = self.twist()
        twist_mult = sp.get("twist_growth", {}).get(twist_id)
        if twist_mult:
            mult *= twist_mult
        if twist_id in sp.get("hardy_twists", ()):
            # Undo the weather's slowdown, then grow at the hardy rate
            # (1.25x, as if the day were fair and bright) instead.
            mult *= float(sp.get("hardy_growth", 1.25)) / max(float(twist.get("growth", 1.0)), 0.01)
        return mult

    def plot_growth_speed(self, i, cellar=False):
        """Effective growth rate of plot `i`, including cellar, eclipse, and watering modifiers."""
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list):
            return 0.0
        p = plot_list[i]
        if cellar:
            return (self.cellar_growth_speed()
                    * (1.5 if self.is_chosen(i, cellar) else 1.0)
                    * (self._plant_speed_mult(p.species, cellar=True) if p.species else 1.0)
                    * (1.0 + self.synergy_growth(p.species) if p.species else 1.0))
        if self.plant_disabled(i):
            return 0.0
        speed = self.growth_speed() * (1.5 if self.is_chosen(i, cellar) else 1.0)
        if p.species and self.twist().get("eclipse"):
            speed *= 1.3 if "nocturnal" in data.PLANTS[p.species]["tags"] else 0.8
        if p.water_left > 0:
            speed *= WATER_BOOST
        if p.sick:
            speed *= self.disease_factors()[0]
        if p.species:
            speed *= self._plant_speed_mult(p.species)
            speed *= 1.0 + self.synergy_growth(p.species)
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
        planted = self._planted_species()
        distinct = len(set(planted))
        # A lit-up pairing amplifies its relic's own effects; The Collector
        # amplifies every relic by 2% per species. Scale 1.0 is a no-op.
        scales = [self._relic_scale(rid) for rid in self.relics]

        # Layout mechanics reshape the base harvest before relics multiply it.
        chips += plot.fed + plot.gorged
        if sp.get("network"):
            chips *= self.network_share(len(self.mycelium_network(i, cellar)))
        if plot.bloom != 1.0:
            chips *= plot.bloom
        chips = int(round(chips))

        for e, scale in zip(effects, scales):
            for tag, amount in e.get("yield_add", []):
                if tag == "all" or tag in tags:
                    chips += amount * scale
            for tag, needs, amount in e.get("adjacent", []):
                if tag in tags:
                    for n in self.neighbours(i, cellar):
                        other = plot_list[n].species
                        if other and needs in data.PLANTS[other]["tags"]:
                            chips += amount * scale

        mult = 2.0 ** milestone_level(self.mastery.get(plot.species, 0))
        for e, scale in zip(effects, scales):
            for tag, m in e.get("yield_mult", []):
                if tag == "all" or tag in tags:
                    mult *= 1.0 + (m - 1.0) * scale
            if e.get("distinct_bonus"):
                mult *= 1.0 + e["distinct_bonus"] * distinct * scale
            if e.get("mono_mult") and distinct == 1 and len(planted) >= 2:
                mult *= 1.0 + (e["mono_mult"] - 1.0) * scale

        # The plant side of a pairing: matching crops pay a little more.
        mult *= 1.0 + self.synergy_harvest(plot.species)
        if sp.get("mutant"):
            mult *= 1.0 + self._sum("mutant_bonus")
        if self.compost_active():
            mult *= self.compost_mult()
        mult *= 1.0 + 0.10 * self.perk("yield")
        mult *= self.twist()["yield"]
        if self.is_chosen(i, cellar):
            mult *= 2.0
        # Plot-level hazards reshape the payout last, so Disease and Aphids cut
        # a bonus just as hard as they cut a base crop, and a starlit plot
        # multiplies whatever the garden had already decided it was worth.
        mult *= self.hazard_value_mult(plot)

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
        # Winter-hardy crosses (the Frost Tomato) ignore the Frost ban.
        if sp.get("frost_hardy") and self._effective_twist_id() == "frost":
            return True
        ban = self.twist()["ban"]
        return not (ban and ban in sp["tags"])

    def plant(self, i, species, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)) or plot_list[i].species is not None:
            return False
        if self.seeds.get(species, 0) <= 0 or not self.can_plant(species, cellar):
            return False
        ground = plot_list[i]
        if ground.weed and not cellar:
            # Weedy soil has to be dug out first; the seed stays in the tray.
            return False
        self.seeds[species] -= 1
        planted = self._starting_mutation(species)
        # Stardust left by a meteor survives the planting and carries into the
        # new crop, so a strike on bare ground is an investment, not a miss.
        stardust = bool(ground.starlit) and not cellar
        ground.clear()
        ground.species = planted
        ground.starlit = stardust
        if stardust:
            self._emit("stardust", plot=i, cellar=cellar, name=data.PLANTS[planted]["name"])
        if planted != species:
            self._emit("mutate", plot=i, cellar=cellar, name=data.PLANTS[planted]["name"])
        return True

    def plot_is_weedy(self, i, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        return bool(0 <= i < len(plot_list) and plot_list[i].weed and not cellar)

    def clear_weeds(self, i, cellar=False):
        """Dig out a weed patch, leaving clean soil behind. Returns True if one went."""
        plot_list = self.cellar_plots if cellar else self.plots
        if cellar or not (0 <= i < len(plot_list)) or not plot_list[i].weed:
            return False
        plot_list[i].weed = False
        self._emit("weed_clear", plot=i, cellar=False)
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
        """Uproot the crop in plot `i` without refunding its seed.

        Shovelling is also the cure for every plot-level hazard: `clear()` drops
        the Disease flag, the aphid colony and any stardust along with the crop,
        and digs out a weed patch, so a dug plot is always clean soil again.
        """
        plot_list = self.cellar_plots if cellar else self.plots
        if not (0 <= i < len(plot_list)) or plot_list[i].species is None:
            if self.clear_weeds(i, cellar):
                return True, "Pulled the weeds."
            return False, "Nothing planted there."
        name = data.PLANTS[plot_list[i].species]["name"]
        sick = plot_list[i].sick
        plot_list[i].clear()
        if self.chosen_plant == (bool(cellar), i):
            self.chosen_plant = (None, -1)
        if sick:
            self._emit("cured", plot=i, cellar=False, name=name)
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
        if p.aphids:
            # Aphids hate a soak. The same click that doubles growth also washes
            # the colony off, so an aphid round is really a tax on your watering
            # timing - and a Hired Gardener or a Rain day shifts them for free.
            p.aphids = False
            self._emit("aphid_wash", plot=i, cellar=False)
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
        self.disease_timer = 0.0
        self.contagion_timer = 0.0
        self.meteor_timer = 0.0
        self.weed_timer = 0.0
        self.aphid_timer = 0.0
        self.weeds_this_round = 0
        self.creep_grown = {False: 0, True: 0}
        self.round_income = 0
        self.events = []
        self.capsule_timer = 0.0
        self.capsule_income = 0
        self.owl_timer = 0.0
        self.snail_bitten = False
        self.free_offer = None
        self.stock_species = None
        for group in (self.plots, self.cellar_plots):
            for p in group:
                p.clear()

    def _pick_stock_species(self):
        """Stock Market's species of the round, biased toward rare crops when paired."""
        pool = [sid for sid, count in self.seeds.items() if count > 0 and sid in data.PLANTS]
        pool += [sid for sid in self._planted_species() if sid not in pool]
        if not pool:
            pool = list(data.SURFACE_PLANTS)
        syn = data.RELIC_SYNERGIES["stock_market"]
        boost = self._synergy_active(syn)
        weights = [
            1.0 + syn.get("power", 0.0)
            if boost and data.PLANTS[sid].get("rarity") in syn["rarity"] else 1.0
            for sid in pool
        ]
        return self.rng.choices(pool, weights=weights)[0]

    def start_timer(self):
        if self.started:
            return
        self.started = True
        if self._has("stock_market") and not self.stock_species:
            self.stock_species = self._pick_stock_species()
        # Antique Clock: a couple of seconds of growth before the timer starts.
        free = 2 * self.perk("clock")
        if free > 0:
            self._advance(self.plots, False, self.growth_speed(), False, float(free))
            if self.cellar_unlocked:
                self._advance(self.cellar_plots, True, self.cellar_growth_speed(),
                              False, float(free))

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
            plot_speed *= self._plant_speed_mult(p.species, cellar=cellar)
            plot_speed *= 1.0 + self.synergy_growth(p.species)
            if p.sick:
                plot_speed *= self.disease_factors()[0]
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
            clearing = crosses_half and self._has("clear_weather") and self.rng.random() < CLEAR_SKIES_CHANCE
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

    def disease_factors(self):
        """Return the (growth, harvest, sale) multipliers a diseased crop lives with.

        A Sulphur Duster buys relief: every penalty is pulled halfway back toward
        normal, scaled by the usual relic power. `relief` of 1.0 removes them
        entirely, so the relic is capped at being a complete answer, not a cure
        that makes the hazard profitable.
        """
        relief = min(1.0, max(0.0, self._sum("sick_relief") * self._relic_scale("sulphur_duster")))
        # No relief means the raw penalty; full relief means the crop does not
        # notice the rot at all. Nothing in between is allowed to overshoot.
        return tuple(base + (1.0 - base) * relief
                     for base in (DISEASE_GROWTH, DISEASE_YIELD, DISEASE_SALE))

    def hazard_value_mult(self, plot):
        """Harvest multiplier from plot-level hazards: Disease, Aphids, stardust."""
        mult = 1.0
        if plot.sick:
            mult *= self.disease_factors()[1]
        if plot.aphids:
            mult *= APHID_YIELD
        if plot.starlit:
            mult *= METEOR_BONUS
        return mult

    def hazard_sale_mult(self, plot):
        """The same hazards as an end-of-round sale multiplier."""
        mult = 1.0
        if plot.sick:
            mult *= self.disease_factors()[2]
        if plot.aphids:
            mult *= APHID_SALE
        if plot.starlit:
            mult *= METEOR_BONUS
        return mult

    def diseased_count(self):
        return sum(1 for p in self.plots if p.species and p.sick)

    def weedy_count(self):
        return sum(1 for p in self.plots if p.weed)

    def infect(self, i, source=None):
        """Give plot `i` Disease. Shovelling is the only thing that takes it back off."""
        if not (0 <= i < len(self.plots)):
            return False
        plot = self.plots[i]
        if not plot.species or plot.sick:
            return False
        plot.sick = True
        self._emit("sick", plot=i, cellar=False, source=source,
                   name=data.PLANTS[plot.species]["name"])
        return True

    def _disease_case(self):
        """One new random infection, which is how a Disease round opens."""
        hosts = [i for i, p in enumerate(self.plots) if p.species and not p.sick]
        return self.infect(self.rng.choice(hosts)) if hosts else False

    def _disease_spread(self):
        """Every sick plant rolls once to infect a planted neighbour.

        One roll per sick plot per tick, not one per neighbour, so a ring of
        crops around a casualty is bad luck rather than a guaranteed wipe - and
        the whole hazard stays answerable with a shovel and some spacing.
        """
        resist = min(1.0, max(0.0, self._sum("disease_resist") * self._relic_scale("sulphur_duster")))
        # Snapshot the sick plots first. Without this, a plot infected earlier in
        # the same loop would roll too, and one case would cascade down a whole
        # row in a single tick - the hazard would be unplayable rather than mean.
        sick = [i for i, plot in enumerate(self.plots) if plot.species and plot.sick]
        spread = 0
        for i in sick:
            hosts = [n for n in self.neighbours(i)
                     if self.plots[n].species and not self.plots[n].sick]
            if not hosts:
                continue
            if self.rng.random() < CONTAGION_CHANCE * (1.0 - resist) and self.infect(self.rng.choice(hosts), i):
                spread += 1
        return spread

    def _starlit_mutate(self, plot):
        """A meteor rewrites a crop into one of its mutant forms, when it has any."""
        sp = data.PLANTS[plot.species]
        if sp.get("mutant") or sp.get("crossbreed") or sp.get("no_mutations"):
            return False
        options = data.mutants_for(plot.species)
        if not options:
            return False
        plot.species = self.rng.choice(options)
        plot.harvests = 0
        return True

    def _meteor_strike(self):
        """Meteor Shower: one random plot per tick, flattened or made starlit.

        A strike on a crop is a coin flip between losing it and getting a
        x1.5 mutation; a strike on bare soil leaves stardust there for whatever
        you plant next, which turns the empty corner of your garden into a
        thing to aim at. A Lightning Rod removes the downside entirely.
        """
        if not self.plots:
            return False
        i = self.rng.randrange(len(self.plots))
        plot = self.plots[i]
        if plot.weed and not plot.species:
            plot.weed = False
            self._emit("meteor", plot=i, cellar=False, name="", destroyed=False, weedy=True)
            return True
        if plot.species:
            if not self._has("rod_protects") and self.rng.random() < METEOR_DESTROY:
                name = data.PLANTS[plot.species]["name"]
                plot.clear()
                self._emit("meteor", plot=i, cellar=False, name=name, destroyed=True)
                return True
            mutated = self._starlit_mutate(plot)
            plot.starlit = True
            self._emit("meteor", plot=i, cellar=False, name=data.PLANTS[plot.species]["name"],
                       destroyed=False, mutated=mutated)
            return True
        plot.starlit = True
        self._emit("meteor", plot=i, cellar=False, name="", destroyed=False, stardust=True)
        return True

    def _sprout_weed(self):
        """Weeds: colonise an empty plot, preferring ground beside an existing weed."""
        empty = [i for i, p in enumerate(self.plots) if not p.species and not p.weed]
        if not empty:
            return False
        sown = [i for i, p in enumerate(self.plots) if p.weed]
        if sown and self.rng.random() < WEED_SEED_CHANCE:
            for i in self.rng.sample(sown, len(sown)):
                spots = [n for n in self.neighbours(i)
                         if not self.plots[n].species and not self.plots[n].weed]
                if spots:
                    self._seed_weed(self.rng.choice(spots), i)
                    return True
        self._seed_weed(self.rng.choice(empty))
        return True

    def _seed_weed(self, i, source=None):
        self.plots[i].weed = True
        self.weeds_this_round += 1
        self._emit("weed", plot=i, cellar=False, source=source)
        return True

    def _aphid_colony(self):
        """Aphids settle on one crop and halve it until the next watering."""
        hosts = [i for i, p in enumerate(self.plots) if p.species and not p.aphids]
        if not hosts:
            return False
        i = self.rng.choice(hosts)
        self.plots[i].aphids = True
        self._emit("aphid", plot=i, cellar=False, name=data.PLANTS[self.plots[i].species]["name"])
        return True

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
            self._advance(self.cellar_plots, cellar=True, speed=self.cellar_growth_speed(),
                          auto=False, dt=dt)

        previous = self.time_left
        self.time_left -= dt
        if self.time_left > 1e-9:
            self._announce_compost(w)
        self._tick_capsule(dt)
        self._tick_owl(dt)

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
                if self._has("scare_crows"):
                    self._emit("owl_scare", cellar=False)
                    continue
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

        # Hazards that mark the soil rather than just taking a crop out of it.
        # All four are surface-only: the cellar stays dry, dark and unbothered.
        disease = tw.get("disease")
        if disease:
            self.disease_timer += dt
            while self.disease_timer >= disease:
                self.disease_timer -= disease
                self._disease_case()
            contagion = tw.get("contagion")
            if contagion:
                self.contagion_timer += dt
                while self.contagion_timer >= contagion:
                    self.contagion_timer -= contagion
                    self._disease_spread()

        meteor = tw.get("meteor")
        if meteor:
            self.meteor_timer += dt
            while self.meteor_timer >= meteor:
                self.meteor_timer -= meteor
                self._meteor_strike()

        weed = tw.get("weed")
        if weed:
            self.weed_timer += dt
            while self.weed_timer >= weed:
                self.weed_timer -= weed
                self._sprout_weed()

        aphid = tw.get("aphid")
        if aphid:
            self.aphid_timer += dt
            while self.aphid_timer >= aphid:
                self.aphid_timer -= aphid
                self._aphid_colony()

        if self.time_left <= 1e-9:
            self.time_left = 0.0
            self.finished = True

    def _tick_capsule(self, dt):
        """Time Capsule: every 10s, pay a slice of the last 10s of harvests."""
        period = self._sum("capsule_period")
        if period <= 0:
            return
        self.capsule_timer += dt
        while self.capsule_timer >= period - 1e-9:
            self.capsule_timer -= period
            payout = int(self.capsule_income * self._sum("capsule_share")
                         * self._relic_scale("time_capsule"))
            self.capsule_income = 0
            if payout <= 0:
                continue
            self.money += payout
            self.round_income += payout
            self.total_earned += payout
            self._emit("capsule", amount=payout)

    def _tick_owl(self, dt):
        """The Friendly Owl drops a bonus seed every few seconds."""
        period = self._sum("owl_seed_period")
        if period <= 0:
            return
        self.owl_timer += dt
        while self.owl_timer >= period - 1e-9:
            self.owl_timer -= period
            self._grant_owl_seed()

    def _grant_owl_seed(self):
        pool = [sid for sid, count in self.seeds.items() if count > 0 and sid in data.PLANTS]
        pool += [sid for sid in self._planted_species() if sid not in pool]
        if not pool:
            # Never hand out a crossbreed here: those seeds are earned by
            # cross-pollination alone, not dropped by a passing owl.
            pool = [sid for sid in data.SURFACE_PLANTS if not data.PLANTS[sid].get("crossbreed")]
        sid = self.rng.choice(sorted(set(pool)))
        # A flytrap on the board means the owl is hunting over a full garden.
        count = 2 if self._synergy_active(data.RELIC_SYNERGIES["friendly_owl"]) else 1
        self.seeds[sid] = self.seeds.get(sid, 0) + count
        self._emit("owl_seed", name=data.PLANTS[sid]["name"], count=count, cellar=False)

    def critter_eaten(self, i, species=None, cellar=False):
        """A Venus Flytrap snapped up an ambient critter: feed its next harvest."""
        plot_list = self.cellar_plots if cellar else self.plots
        if self.phase != "round" or self.finished or not 0 <= i < len(plot_list):
            return False
        plot = plot_list[i]
        if not plot.species or not data.PLANTS[plot.species].get("feed") or self.plant_disabled(i, cellar):
            return False
        plot.fed += CRITTER_FEED_VALUE
        self.counters["critter"] = self.counters.get("critter", 0) + 1
        self._emit("critter_eaten", plot=i, cellar=cellar, amount=CRITTER_FEED_VALUE,
                   name=(species or "critter").replace("_", " ").upper())
        return True

    def snail_bite(self):
        """The Eternal Snail caught the cursor. That's the run."""
        if self.phase != "round" or not self.started or self.finished or self.snail_bitten:
            return False
        self.snail_bitten = True
        self.dead = True
        self.finished = True
        self.time_left = 0.0
        self._emit("snail_bite")
        return True

    def _roll_crossbreed(self, i, cellar=False):
        """Roll cross-pollination for the plant about to be harvested.

        Parents must stand in orthogonally adjacent plots on the same board
        (above, below, left or right) under the recipe's weather/season.
        Every eligible neighbour pair rolls independently, and there is no
        per-round cap: each harvest of either parent is a fresh chance.
        Returns the child species id on success, else None.
        """
        plot_list = self.cellar_plots if cellar else self.plots
        if not 0 <= i < len(plot_list) or not plot_list[i].species:
            return None
        species = plot_list[i].species
        twist_id = self._effective_twist_id()
        twist = self.twist()
        season_name = self.season_name()
        candidates = [plot_list[n].species for n in self.neighbours(i, cellar)]
        # The cellar sits directly below the surface, so the plot at the
        # same index on the other board also counts as a neighbour (above
        # or below). That is how a cellar Moonflower can cross with the
        # Pumpkin ripening over its head in Autumn.
        other_board = self.plots if cellar else self.cellar_plots
        if i < len(other_board):
            candidates.append(other_board[i].species)
        for other in candidates:
            if not other:
                continue
            cid = data.crossbreed_match(species, other, twist_id, twist, season_name)
            if cid is None:
                continue
            if self.rng.random() < float(data.PLANTS[cid].get("chance", 0.15)):
                return cid
        return None

    def _grant_crossbreed(self, cid, i, cellar=False):
        """Bank one freshly cross-pollinated seed and announce the discovery."""
        self.seeds[cid] = self.seeds.get(cid, 0) + 1
        first = cid not in self.discovered_crossbreeds
        self.discovered_crossbreeds.add(cid)
        self._emit(
            "crossbreed", plot=i, cellar=cellar, species=cid,
            name=data.PLANTS[cid]["name"], first=first,
        )

    def _harvest(self, i, cellar=False):
        plot_list = self.cellar_plots if cellar else self.plots
        plot = plot_list[i]
        species = plot.species
        sp = data.PLANTS[species]

        # Cross-pollination is judged on the garden as it stands, before a
        # Man-Eater's bite (or any other harvest side effect) can move or
        # remove the neighbouring parent.
        crossbred = self._roll_crossbreed(i, cellar)

        # A Man-Eater feeds before it is paid, so the bite counts this harvest.
        if sp.get("consume"):
            self._devour(i, cellar)
        value = self.harvest_value(i, cellar)

        self.money += value
        self.round_income += value
        self.total_earned += value
        self.capsule_income += value
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
        if crossbred:
            self._grant_crossbreed(crossbred, i, cellar)

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
        take over the garden for free. The creep meter belongs to the patch, not
        to the plot that happened to grow: every member is reset to zero, so a
        wide patch books one guaranteed expansion every MYCELIUM_CREEP_TIME
        instead of one per member.
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
        # The patch's shared creep meter pays for the new plot, so every member
        # starts filling the next expansion from zero together.
        for member in self.mycelium_network(target, cellar) or [target]:
            plot_list[member].creep_cd = 0.0
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
        """Fill the patch creep meter and book the guaranteed spreads.

        Every member banks the same shared meter, which is reset for the whole
        patch every time it grows, so a patch of any width books exactly one
        guaranteed new plot per MYCELIUM_CREEP_TIME seconds of round. A lone
        seed therefore always becomes a patch you can watch grow, while harvest
        rolls in `_spread_mycelium` make the good rounds faster. The meter only
        fills while the patch has an empty neighbour, so a walled-in mycelium
        never banks free expansions.
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
        stock_effect = self._sum("stock_market") if self.stock_species else 1.0
        stock_mult = 1.0 + max(0.0, stock_effect - 1.0) * self._relic_scale("stock_market")
        # Weeds are charged as "lawn rent": every patch still standing when the
        # buzzer goes costs WEED_FEE, which is what makes an ignored corner of
        # the garden a real decision rather than free blocked soil. It is
        # itemised separately from cursed upkeep on the summary.
        weed_count = sum(1 for p in self.plots if p.weed)
        weed_fee = WEED_FEE * weed_count
        for group in (self.plots, self.cellar_plots):
            for p in group:
                if p.species:
                    sp = data.PLANTS[p.species]
                    upkeep += sp.get("upkeep", 0)
                    frac = min(1.0, p.progress / sp["grow"])
                    pick_mult = stock_mult if p.species == self.stock_species else 1.0
                    sale += int(sp["sell"] * frac * sale_mult * pick_mult * self.hazard_sale_mult(p))
                p.clear()

        self.money += sale
        self.total_earned += sale
        self.money = max(0, self.money - upkeep - weed_fee)

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
            "net": self.round_income + sale + interest - upkeep - weed_fee,
            "sale": sale,
            "interest": interest,
            "interest_rate": rate,
            "bill": bill,
            "paid": None,
            "money": self.money,
            "upkeep": upkeep,
            "weed_fee": weed_fee,
            "weeds": weed_count,
            "victory": False,
            "twist": self.twist_id(self.round),
            "stock_species": self.stock_species,
            "pending_bill": bool(bill),
            "can_afford": (self.money >= bill or self.bill_waivers > 0) if bill else True,
            "shortfall": max(0, bill - self.money) if bill else 0,
        }
        self.phase = "summary"
        return self.last_summary

    def pay_pending_bill(self):
        bill = self.pending_bill
        if not bill:
            return True, "No bill due."
        if self.money < bill:
            # Old Insurance Card: one bill per run is waived instead of paid.
            if self.bill_waivers <= 0:
                return False, "Not enough money for the bill."
            self.bill_waivers -= 1
            self.insurance_used = True
            waived = True
        else:
            self.money -= bill
            waived = False
        self.quotas_paid += 1
        self.pending_bill = 0
        if self.last_summary is None:
            self.last_summary = {}
        self.last_summary["paid"] = True
        self.last_summary["waived"] = waived
        self.last_summary["money"] = self.money
        if self.quotas_paid >= WIN_QUOTAS and not self.won:
            self.won = True
            self.last_summary["victory"] = True
        return True, ("Old Insurance Card covered the bill!" if waived else "Bill paid!")

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
        self._roll_free_offer()

    def _roll_free_offer(self):
        """Lucky Penny: after a paid bill, one shop offer may cost nothing."""
        self.free_offer = None
        if self.perk("penny") <= 0 or not (self.last_summary or {}).get("paid"):
            return
        if self.rng.random() >= 0.08 * self.perk("penny"):
            return
        live = [i for i, rid in enumerate(self.shop_offers) if rid is not None]
        if live:
            self.free_offer = self.rng.choice(live)

    def relic_slots(self):
        return RELIC_SLOTS + (1 if self.perk("relics") >= 2 else 0)

    def relic_offer_slots(self):
        return 3 + (1 if self.perk("relics") >= 3 else 0)

    def roll_offers(self):
        # Rerolling (or entering a fresh shop) removes any Lucky Penny freebie.
        self.free_offer = None
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

    def relic_offer_price(self, index):
        """Price of offer `index`, honouring a Lucky Penny free offer."""
        if not 0 <= index < len(self.shop_offers) or self.shop_offers[index] is None:
            return 0
        if index == self.free_offer:
            return 0
        return self.relic_price(self.shop_offers[index])

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
        free = index == self.free_offer
        price = 0 if free else self.relic_price(rid)
        if self.money < price:
            return False, "Not enough money."
        self.money -= price
        self.relics.append(rid)
        self._relic_lvls[rid] = self.relic_level(rid)
        self.shop_offers[index] = None
        if free:
            self.free_offer = None
        return True, ("Took %s for free!" if free else "Bought %s!") % data.RELICS[rid]["name"]

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
            "endless": self.endless, "retired": self.retired,
            "heirlooms_spent": self.heirlooms_spent, "last_summary": self.last_summary,
            "bill_waivers": self.bill_waivers, "insurance_used": self.insurance_used,
            "crossbreeds_found": sorted(self.discovered_crossbreeds),
            "free_offer": self.free_offer, "stock_species": self.stock_species,
            "capsule_timer": self.capsule_timer, "capsule_income": self.capsule_income,
            "owl_timer": self.owl_timer, "snail_bitten": self.snail_bitten,
            "story_beats": list(self.story_beats),
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
        run.free_offer = d.get("free_offer")
        if not isinstance(run.free_offer, int) or not (0 <= run.free_offer < len(run.shop_offers)) \
                or run.shop_offers[run.free_offer] is None:
            run.free_offer = None
        run.bill_waivers = int(d.get("bill_waivers", 1 if run.perk("insurance") else 0))
        run.insurance_used = bool(d.get("insurance_used", False))
        run.stock_species = d.get("stock_species")
        if run.stock_species not in data.PLANTS:
            run.stock_species = None
        run.discovered_crossbreeds = {
            cid for cid in d.get("crossbreeds_found", []) if cid in data.CROSSBREEDS
        }
        run.capsule_timer = float(d.get("capsule_timer", 0.0))
        run.capsule_income = int(d.get("capsule_income", 0))
        run.owl_timer = float(d.get("owl_timer", 0.0))
        run.snail_bitten = bool(d.get("snail_bitten", False))
        # Story beats already played this run, so a reload does not repeat Moss.
        run.story_beats = [str(b) for b in d.get("story_beats", []) if isinstance(b, str)]
        run.rerolls = int(d.get("rerolls", 0))
        run.quotas_paid = int(d.get("quotas_paid", 0))
        run.total_earned = int(d.get("total_earned", 0))
        run.won = bool(d.get("won", False))
        run.dead = bool(d.get("dead", False))
        run.endless = bool(d.get("endless", False))
        run.retired = bool(d.get("retired", False))
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
