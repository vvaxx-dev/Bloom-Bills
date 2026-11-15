"""Sparse garden visitors plus seasonal and weather particle effects."""

import math
import random

import pygame

from . import data, gfx
from .settings import (
    CRITTER_EAT_COOLDOWN, CRITTER_EAT_RADIUS, CURSOR_SNAIL_CATCH,
    CURSOR_SNAIL_GRACE, CURSOR_SNAIL_SPEED,
)
from .sprites_data import PALETTE

# Garden board coordinates (strictly below timebar y=27..32, left of RELICS x=244, above tray y=148).
BOARD_LEFT = 1
BOARD_RIGHT = 242
BOARD_TOP = 33
BOARD_BOTTOM = 147

# Lane centerlines running around and between the 4x3 plot grid (plots at x=4..240, y=36..146).
LANE_XS = (2, 61, 121, 181, 241)
LANE_YS = (34, 72, 110, 146)

_FLIP_CACHE = {}

CRITTER_SPECIES = {
    # Early rounds (Round 1+): garden insects.
    "ant": {
        "tier": "insect", "min_round": 1, "cellar": True, "motion": "crawl",
        "speed": 15.0, "fps": 8.0, "weight": 4,
    },
    "ladybug": {
        "tier": "insect", "min_round": 1, "cellar": False, "motion": "crawl",
        "speed": 10.5, "fps": 6.5, "weight": 3,
    },
    "worm": {
        "tier": "insect", "min_round": 1, "cellar": True, "motion": "crawl",
        "speed": 7.5, "fps": 4.2, "weight": 3,
    },
    "beetle": {
        "tier": "insect", "min_round": 2, "cellar": True, "motion": "crawl",
        "speed": 12.0, "fps": 7.0, "weight": 3,
    },
    "bee": {
        "tier": "insect", "min_round": 3, "cellar": False, "motion": "fly",
        "speed": 21.0, "fps": 12.0, "weight": 2,
    },
    "butterfly": {
        "tier": "insect", "min_round": 1, "cellar": False, "motion": "fly",
        "speed": 16.5, "fps": 6.5, "weight": 2,
    },
    # Mid-early garden visitors (Round 10+).
    "snail": {
        "tier": "garden", "min_round": 10, "cellar": True, "motion": "crawl",
        "speed": 5.5, "fps": 2.8, "weight": 2,
    },
    "frog": {
        "tier": "garden", "min_round": 12, "cellar": False, "motion": "hop",
        "speed": 22.0, "fps": 5.0, "weight": 2,
    },
    # Late campaign obscure woodland visitors (Round 18-24+: mice & rabbits!).
    "mouse": {
        "tier": "woodland", "min_round": 18, "cellar": True, "motion": "crawl",
        "speed": 25.0, "fps": 9.5, "weight": 3,
    },
    "rabbit": {
        "tier": "woodland", "min_round": 22, "cellar": False, "motion": "hop",
        "speed": 26.0, "fps": 5.5, "weight": 3,
    },
    # Deep endless cryptids (Round 45+).
    "mandrake": {
        "tier": "cryptid", "min_round": 45, "cellar": True, "motion": "crawl",
        "speed": 13.5, "fps": 6.0, "weight": 3,
    },
    "wisp": {
        "tier": "cryptid", "min_round": 50, "cellar": True, "motion": "fly",
        "speed": 19.0, "fps": 7.0, "weight": 3,
    },
    # High-round surreal / alien creatures (Round 80-100+!).
    "alien": {
        "tier": "alien", "min_round": 80, "cellar": True, "motion": "crawl",
        "speed": 15.5, "fps": 5.8, "weight": 4,
    },
    "ufo": {
        "tier": "alien", "min_round": 88, "cellar": False, "motion": "fly",
        "speed": 27.0, "fps": 8.0, "weight": 4,
    },
    "void": {
        "tier": "alien", "min_round": 95, "cellar": True, "motion": "fly",
        "speed": 14.0, "fps": 5.2, "weight": 4,
    },
}


def critter_pool_for_round(rnd, cellar=False):
    """Return eligible critter species ids unlocked at round `rnd`."""
    rnd = max(1, int(rnd))
    pool = []
    for cid, meta in CRITTER_SPECIES.items():
        if rnd < meta["min_round"]:
            continue
        if cellar and not meta["cellar"]:
            continue
        pool.append(cid)
    return pool or ["ant"]


MAX_ONSCREEN_CRITTERS = 3


def target_critter_count(rnd, cellar=False):
    """Keep the garden readable: at most three visitors are active at once."""
    rnd = max(1, int(rnd))
    base = 1 if cellar else 2
    if rnd >= 18:
        base += 1
    return min(MAX_ONSCREEN_CRITTERS, base)


def choose_critter_roster(rnd, seed=1, cellar=False):
    """Build a deterministic critter roster for `(rnd, cellar)` with milestone guarantees."""
    rnd = max(1, int(rnd))
    rng = random.Random(int(seed) * 131071 + rnd * 97 + (17 if cellar else 0))
    pool = critter_pool_for_round(rnd, cellar=cellar)
    count = target_critter_count(rnd, cellar=cellar)

    roster = []
    # Guarantee obscure creatures appear prominently as rounds climb.
    if rnd >= 100:
        aliens = [c for c in ("alien", "ufo", "void") if c in pool]
        for a in aliens:
            roster.append(a)
        while aliens and len(roster) < min(count, max(4, count // 2)):
            roster.append(rng.choice(aliens))
    if rnd >= 45:
        cryptids = [c for c in ("mandrake", "wisp") if c in pool]
        if cryptids and len(roster) < count:
            roster.append(rng.choice(cryptids))
    if rnd >= 24:
        for w in ("mouse", "rabbit"):
            if w in pool and len(roster) < count:
                roster.append(w)
    elif rnd >= 18 and "mouse" in pool:
        roster.append("mouse")

    weights = []
    for cid in pool:
        w = CRITTER_SPECIES[cid]["weight"]
        tier = CRITTER_SPECIES[cid]["tier"]
        if rnd >= 100 and tier == "alien":
            w *= 3
        elif rnd >= 24 and tier == "woodland":
            w *= 2
        weights.append(w)

    while len(roster) < count:
        roster.append(rng.choices(pool, weights=weights, k=1)[0])
    rng.shuffle(roster)
    return roster[:count]


def _critter_surface(sprite_name, flip_x=False, shadow=False):
    key = (sprite_name, bool(flip_x), bool(shadow))
    surf = _FLIP_CACHE.get(key)
    if surf is None:
        subs = {k: (20, 16, 28) for k in PALETTE} if shadow else None
        base = gfx.sprite(sprite_name, 1, subs)
        surf = pygame.transform.flip(base, True, False) if flip_x else base
        _FLIP_CACHE[key] = surf
    return surf


class Critter:
    """Single ambient visitor that enters, wanders, leaves, and later returns."""

    OFFSCREEN_PAD = 14

    def __init__(self, species, rng):
        self.species = species
        self.meta = CRITTER_SPECIES[species]
        self.motion = self.meta["motion"]
        self.anim_t = rng.random() * 10.0
        self.pause = 0.0
        self.hop_phase = 0.0
        self.hop_z = 0.0
        self.away = 0.0
        self.leaving = False
        self.visit_left = rng.uniform(6.0, 13.0)
        self.facing_left = rng.random() < 0.5
        self._spawn_inside(rng)

    def _spawn_inside(self, rng):
        """Place a new round's visitor on a lane or in the open air."""
        if self.motion == "crawl":
            if rng.random() < 0.6:
                self.axis = "x"
                self.y = float(rng.choice(LANE_YS))
                self.x = float(rng.uniform(BOARD_LEFT + 2, BOARD_RIGHT - 10))
                self.dir = -1.0 if self.facing_left else 1.0
            else:
                self.axis = "y"
                self.x = float(rng.choice(LANE_XS))
                self.y = float(rng.uniform(BOARD_TOP + 2, BOARD_BOTTOM - 8))
                self.dir = rng.choice((-1.0, 1.0))
        elif self.motion == "hop":
            self.axis = "x"
            self.y = float(rng.choice(LANE_YS))
            self.x = float(rng.uniform(BOARD_LEFT + 6, BOARD_RIGHT - 14))
            self.dir = -1.0 if self.facing_left else 1.0
            self.pause = rng.uniform(0.1, 0.9)
        else:
            self.axis = "free"
            self.x = float(rng.uniform(BOARD_LEFT + 6, BOARD_RIGHT - 14))
            self.y = float(rng.uniform(BOARD_TOP + 4, BOARD_BOTTOM - 12))
            ang = rng.uniform(0.0, math.tau)
            self.vx = math.cos(ang) * self.meta["speed"]
            self.vy = math.sin(ang) * self.meta["speed"] * 0.55
            self.facing_left = self.vx < 0

    @property
    def offscreen(self):
        """True while fully away or still crossing an edge into the garden."""
        return not (
            self.away <= 0
            and self.x < BOARD_RIGHT and self.x + 12 > BOARD_LEFT
            and self.y + 8 > BOARD_TOP and self.y - 8 < BOARD_BOTTOM
        )

    def _begin_departure(self):
        """Aim for a nearby edge instead of bouncing around forever."""
        self.leaving = True
        self.pause = 0.0
        if self.motion in ("crawl", "hop"):
            if self.motion == "hop" or self.axis == "x":
                self.axis = "x"
                self.dir = -1.0 if self.x < (BOARD_LEFT + BOARD_RIGHT) / 2 else 1.0
                self.facing_left = self.dir < 0
            else:
                self.dir = -1.0 if self.y < (BOARD_TOP + BOARD_BOTTOM) / 2 else 1.0
        else:
            spd = self.meta["speed"]
            distances = (
                (self.x - BOARD_LEFT, -spd, 0.0),
                (BOARD_RIGHT - self.x, spd, 0.0),
                (self.y - BOARD_TOP, 0.0, -spd * 0.65),
                (BOARD_BOTTOM - self.y, 0.0, spd * 0.65),
            )
            _distance, self.vx, self.vy = min(distances, key=lambda item: item[0])
            self.facing_left = self.vx < 0

    def _fully_outside(self):
        pad = self.OFFSCREEN_PAD
        return (self.x < BOARD_LEFT - pad or self.x > BOARD_RIGHT + pad
                or self.y < BOARD_TOP - pad or self.y > BOARD_BOTTOM + pad)

    def _leave_for_a_while(self, rng):
        self.away = rng.uniform(1.8, 4.8)
        self.leaving = False
        self.pause = 0.0
        self.hop_phase = self.hop_z = 0.0

    def _reenter(self, rng):
        """Start just beyond a random edge with a velocity pointing inward."""
        pad = self.OFFSCREEN_PAD - 1
        self.away = 0.0
        self.leaving = False
        self.visit_left = rng.uniform(6.0, 13.0)
        spd = self.meta["speed"]

        if self.motion == "hop":
            side = rng.choice((-1.0, 1.0))
            self.axis = "x"
            self.x = float(BOARD_LEFT - pad if side < 0 else BOARD_RIGHT + pad)
            self.y = float(rng.choice(LANE_YS))
            self.dir = 1.0 if side < 0 else -1.0
            self.facing_left = self.dir < 0
            self.pause = 0.0
            return

        if self.motion == "crawl":
            if rng.random() < 0.7:
                side = rng.choice((-1.0, 1.0))
                self.axis = "x"
                self.x = float(BOARD_LEFT - pad if side < 0 else BOARD_RIGHT + pad)
                self.y = float(rng.choice(LANE_YS))
                self.dir = 1.0 if side < 0 else -1.0
                self.facing_left = self.dir < 0
            else:
                side = rng.choice((-1.0, 1.0))
                self.axis = "y"
                self.x = float(rng.choice(LANE_XS))
                self.y = float(BOARD_TOP - pad if side < 0 else BOARD_BOTTOM + pad)
                self.dir = 1.0 if side < 0 else -1.0
            return

        edge = rng.randrange(4)
        if edge == 0:  # left
            self.x, self.y = float(BOARD_LEFT - pad), rng.uniform(BOARD_TOP + 4, BOARD_BOTTOM - 10)
            self.vx, self.vy = spd, rng.uniform(-8.0, 8.0)
        elif edge == 1:  # right
            self.x, self.y = float(BOARD_RIGHT + pad), rng.uniform(BOARD_TOP + 4, BOARD_BOTTOM - 10)
            self.vx, self.vy = -spd, rng.uniform(-8.0, 8.0)
        elif edge == 2:  # top
            self.x, self.y = rng.uniform(BOARD_LEFT + 4, BOARD_RIGHT - 12), float(BOARD_TOP - pad)
            self.vx, self.vy = rng.uniform(-spd, spd), spd * 0.65
        else:  # bottom
            self.x, self.y = rng.uniform(BOARD_LEFT + 4, BOARD_RIGHT - 12), float(BOARD_BOTTOM + pad)
            self.vx, self.vy = rng.uniform(-spd, spd), -spd * 0.65
        self.facing_left = self.vx < 0

    def update(self, dt, rng):
        self.anim_t += dt
        if self.away > 0:
            self.away -= dt
            if self.away <= 0:
                self._reenter(rng)
            return

        self.visit_left -= dt
        if self.visit_left <= 0 and not self.leaving:
            self._begin_departure()

        spd = self.meta["speed"]
        if self.motion == "crawl":
            if self.pause > 0 and not self.leaving:
                self.pause -= dt
                return
            if not self.leaving and rng.random() < dt * 0.35:
                self.pause = rng.uniform(0.2, 0.65)
                return
            if self.axis == "x":
                prev_x = self.x
                self.x += self.dir * spd * dt
                self.facing_left = self.dir < 0
                if not self.leaving:
                    for lx in LANE_XS:
                        if (prev_x - lx) * (self.x - lx) <= 0 and rng.random() < 0.28:
                            self.x = float(lx)
                            self.axis = "y"
                            self.dir = rng.choice((-1.0, 1.0))
                            break
            else:
                prev_y = self.y
                self.y += self.dir * spd * dt
                if not self.leaving:
                    for ly in LANE_YS:
                        if (prev_y - ly) * (self.y - ly) <= 0 and rng.random() < 0.35:
                            self.y = float(ly)
                            self.axis = "x"
                            self.dir = rng.choice((-1.0, 1.0))
                            self.facing_left = self.dir < 0
                            break

        elif self.motion == "hop":
            if self.pause > 0 and not self.leaving:
                self.pause -= dt
                self.hop_z = 0.0
                if self.pause <= 0:
                    self.hop_phase = 0.001
                    if rng.random() < 0.28:
                        self.dir = -self.dir
                    self.facing_left = self.dir < 0
                return
            self.hop_phase += dt * 2.8
            if self.hop_phase >= 1.0:
                self.hop_phase = 0.0
                self.hop_z = 0.0
                self.pause = 0.0 if self.leaving else rng.uniform(0.35, 1.1)
            else:
                self.hop_z = math.sin(self.hop_phase * math.pi) * 4.5
            self.x += self.dir * spd * dt

        else:
            wobble = math.sin(self.anim_t * 3.1) * 8.0
            self.x += self.vx * dt
            self.y += (self.vy + wobble * 0.35) * dt
            if not self.leaving and rng.random() < dt * 0.45:
                ang = rng.uniform(-0.7, 0.7)
                c, s = math.cos(ang), math.sin(ang)
                nvx = self.vx * c - self.vy * s
                nvy = self.vx * s + self.vy * c
                self.vx, self.vy = nvx, max(-14.0, min(14.0, nvy))
            self.facing_left = self.vx < -0.5

        if self._fully_outside():
            self._leave_for_a_while(rng)

    def frame_index(self):
        if self.motion == "hop":
            return 1 if self.hop_z > 0.8 else 0
        if self.pause > 0:
            return 0
        return int(self.anim_t * self.meta["fps"]) % 2

    def draw(self, surf):
        if self.away > 0:
            return
        frame = self.frame_index()
        sname = "critter_%s_%d" % (self.species, frame)
        sp = _critter_surface(sname, flip_x=self.facing_left, shadow=False)
        h = sp.get_height()
        px = int(round(self.x))
        py = int(round(self.y - h // 2 - self.hop_z))
        if self.motion == "fly":
            shadow_y = int(round(self.y + h // 2 + 2))
            surf.fill((20, 16, 28), (px + 2, shadow_y, max(2, sp.get_width() - 4), 1))
        elif self.hop_z > 0.5:
            gy = int(round(self.y + h // 2 - 1))
            surf.fill((20, 16, 28), (px + 2, gy, max(2, sp.get_width() - 4), 1))
        else:
            sh = _critter_surface(sname, flip_x=self.facing_left, shadow=True)
            surf.blit(sh, (px + 1, py + 1))
        surf.blit(sp, (px, py))


class CursorSnail:
    """The Eternal Snail's cursed twin: a slow violet snail that hunts the mouse.

    It only exists while the relic is owned, gives the player a short grace
    period, and ends the run if it ever reaches the cursor. Keeping the mouse
    moving is the whole counterplay.
    """

    def __init__(self, rng, mouse=None):
        mx = float(mouse[0]) if mouse and mouse[0] >= 0 else BOARD_LEFT
        my = float(mouse[1]) if mouse and mouse[1] >= 0 else BOARD_TOP
        self.x = BOARD_LEFT + 2 if mx > (BOARD_LEFT + BOARD_RIGHT) / 2 else BOARD_RIGHT - 10
        self.y = BOARD_TOP + 4 if my > (BOARD_TOP + BOARD_BOTTOM) / 2 else BOARD_BOTTOM - 8
        self.t = rng.random() * 2.0
        self.grace = CURSOR_SNAIL_GRACE
        self.facing_left = True

    def update(self, dt, mouse, run):
        self.t += dt
        if not mouse or mouse[0] < 0 or mouse[1] < 0:
            # No real cursor yet: wait out the grace period instead of killing
            # a player who has not touched the garden.
            self.grace = max(self.grace, 0.5)
            return False
        self.grace -= dt
        mx, my = float(mouse[0]), float(mouse[1])
        dx, dy = mx - self.x, my - self.y
        dist = math.hypot(dx, dy)
        if dist > 0.001:
            step = min(dist, CURSOR_SNAIL_SPEED * dt)
            self.x += dx / dist * step
            self.y += dy / dist * step
            self.facing_left = dx < 0
        self.x = max(float(BOARD_LEFT), min(float(BOARD_RIGHT - 8), self.x))
        self.y = max(float(BOARD_TOP + 4), min(float(BOARD_BOTTOM - 4), self.y))
        if self.grace <= 0 and dist <= CURSOR_SNAIL_CATCH:
            return bool(run.snail_bite())
        return False

    def draw(self, surf):
        frame = int(self.t * 3.0) % 2
        sname = "critter_cursed_snail_%d" % frame
        sp = _critter_surface(sname, flip_x=self.facing_left)
        w, h = sp.get_size()
        px, py = int(round(self.x)), int(round(self.y - h // 2))
        # A thin violet rim makes this chaser distinct from the harmless brown
        # garden snail that already wanders the lanes.
        rim = (150, 90, 200)
        surf.fill(rim, (px - 1, py, 1, h))
        surf.fill(rim, (px + w, py, 1, h))
        surf.fill(rim, (px, py - 1, w, 1))
        surf.fill(rim, (px, py + h, w, 1))
        surf.blit(_critter_surface(sname, flip_x=self.facing_left, shadow=True), (px + 1, py + 1))
        surf.blit(sp, (px, py))


class GardenAmbient:
    """Manages a sparse stream of critters plus seasonal and weather effects."""

    def __init__(self, run):
        self.t = 0.0
        self.rng = random.Random((getattr(run, "seed", 1) or 1) * 65537 + 19)
        self._state_key = None
        self.critters = []
        self.flytrap_cd = {}
        self.eat_sparks = []
        self.cursor_snail = None
        self.sync(run, cellar=False)

    def sync(self, run, cellar=False):
        rnd = max(1, int(getattr(run, "round", 1)))
        seed = getattr(run, "seed", 1) or 1
        key = (rnd, bool(cellar), seed)
        if key == self._state_key:
            return
        self._state_key = key
        spawn_rng = random.Random(seed * 91813 + rnd * 131 + (31 if cellar else 0))
        roster = choose_critter_roster(rnd, seed=seed, cellar=cellar)
        self.critters = [Critter(sp, spawn_rng) for sp in roster]
        self.flytrap_cd.clear()
        self.eat_sparks.clear()
        self.cursor_snail = None

    def update(self, dt, run, cellar=False, plot_rects=(), mouse=None):
        self.t += dt
        self.sync(run, cellar=cellar)
        for c in self.critters:
            c.update(dt, self.rng)
        self._feed_flytraps(dt, run, cellar=cellar, plot_rects=plot_rects)
        self._update_cursor_snail(dt, run, mouse=mouse)
        self.eat_sparks = [[x, y, age + dt] for x, y, age in self.eat_sparks if age + dt < 0.45]

    def _feed_flytraps(self, dt, run, cellar=False, plot_rects=()):
        """A Venus Flytrap snaps up an ambient critter that wanders near its mouth."""
        for key in list(self.flytrap_cd):
            self.flytrap_cd[key] -= dt
            if self.flytrap_cd[key] <= 0:
                del self.flytrap_cd[key]
        if getattr(run, "phase", "") != "round" or getattr(run, "finished", False):
            return
        plots = run.cellar_plots if cellar else run.plots
        traps = []
        for i, plot in enumerate(plots):
            if (plot.species and data.PLANTS[plot.species].get("feed")
                    and i < len(plot_rects)):
                traps.append((i, plot_rects[i]))
        if not traps:
            return
        for critter in self.critters:
            if critter.away > 0 or critter.offscreen:
                continue
            cx, cy = critter.x + 3.0, critter.y
            for i, (x, y, w, h) in traps:
                key = (bool(cellar), i)
                if key in self.flytrap_cd:
                    continue
                dx = max(x - cx, 0.0, cx - (x + w))
                dy = max(y - cy, 0.0, cy - (y + h))
                if dx * dx + dy * dy > CRITTER_EAT_RADIUS ** 2:
                    continue
                if run.critter_eaten(i, species=critter.species, cellar=cellar):
                    critter._leave_for_a_while(self.rng)
                    self.flytrap_cd[key] = CRITTER_EAT_COOLDOWN
                    self.eat_sparks.append([cx, cy, 0.0])
                    break

    def _update_cursor_snail(self, dt, run, mouse=None):
        """Spawn/chase/retire the Eternal Snail's cursed cursor-chaser."""
        active = (getattr(run, "phase", "") == "round"
                  and getattr(run, "started", False)
                  and not getattr(run, "finished", False)
                  and run._has("cursor_snail")
                  and not getattr(run, "snail_bitten", False))
        if not active:
            self.cursor_snail = None
            return
        if self.cursor_snail is None:
            self.cursor_snail = CursorSnail(self.rng, mouse)
        if self.cursor_snail.update(dt, mouse, run):
            self.cursor_snail = None

    def draw_foliage(self, surf, run, cellar=False, plot_rects=()):
        """Keep surface lanes clean; the season is illustrated in the topbar.

        The old implementation scattered grass, flowers, leaves, and snow
        between every plot. That made a busy board harder to read. Cellar rock
        details remain because they frame the underground board rather than
        pretending to be seasonal surface foliage.
        """
        if cellar:
            self._draw_cellar_foliage(surf)

    def _draw_cellar_foliage(self, surf):
        spikes = (14, 42, 76, 108, 144, 178, 212, 238)
        for idx, sx in enumerate(spikes):
            h = 3 if idx % 2 == 0 else 2
            surf.fill((58, 52, 76), (sx, BOARD_TOP, 3, h))
            surf.fill((84, 78, 106), (sx + 1, BOARD_TOP + h, 1, 1))
            if idx % 3 == 0:
                surf.fill((46, 120, 62), (sx, BOARD_BOTTOM - 1, 3, 2))
                surf.fill((120, 200, 210), (sx + 1, BOARD_BOTTOM - 2, 1, 1))

    def draw_foreground(self, surf, run, cellar=False, plot_rects=(), mouse=None):
        """Draw critters, chomp sparks, the cursed snail, and weather particles."""
        self.sync(run, cellar=cellar)
        for c in self.critters:
            c.draw(surf)
        self._draw_eat_sparks(surf)
        self._draw_weather_and_season_fx(surf, run, cellar=cellar)
        if self.cursor_snail is not None:
            self.cursor_snail.draw(surf)

    def _draw_eat_sparks(self, surf):
        for sx, sy, age in self.eat_sparks:
            radius = 1.0 + age * 12.0
            for k in range(4):
                ang = k * math.pi / 2 + age * 2.0
                px = int(round(sx + math.cos(ang) * radius))
                py = int(round(sy + math.sin(ang) * radius - age * 4))
                if BOARD_TOP <= py < BOARD_BOTTOM and BOARD_LEFT <= px < BOARD_RIGHT:
                    surf.fill((250, 210, 70), (px, py, 1, 1))

    def _draw_weather_and_season_fx(self, surf, run, cellar=False):
        w_span = BOARD_RIGHT - BOARD_LEFT - 4
        h_span = BOARD_BOTTOM - BOARD_TOP - 4
        t = self.t

        if cellar:
            for i in range(6):
                px = BOARD_LEFT + 4 + int((i * 41 + t * 4.5) % w_span)
                py = BOARD_TOP + 4 + int((i * 23 - t * 3.0 + math.sin(t + i) * 3) % h_span)
                surf.fill((120, 200, 210) if i % 2 == 0 else (106, 110, 132), (px, py, 1, 1))
            return

        s_idx = data.season_index(getattr(run, "round", 1))
        twist_id = "none" if getattr(run, "weather_cleared", False) else run.twist_id()
        wind_x = 46.0 if twist_id == "gale" else 10.0

        # The clear spring/summer boards need no confetti. Autumn gets a few
        # tumbling leaves and winter a sparse snowfall, each with gaps between
        # waves so the effects feel occasional rather than like visual noise.
        if s_idx == 2:
            leaf_cols = ((240, 140, 50), (214, 150, 40), (214, 64, 56))
            for i in range(4):
                phase = (t + i * 1.7) % 7.2
                if phase > 4.0:
                    continue
                px = BOARD_LEFT + 3 + int((i * 57 + phase * (wind_x + 5)
                                           + math.sin(phase * 3.0 + i) * 7) % w_span)
                py = BOARD_TOP + 1 + int((phase / 4.0) * (h_span - 3))
                col = leaf_cols[i % len(leaf_cols)]
                surf.fill(col, (px, py, 2, 1))
                surf.fill(col, (px + (i % 2), py + 1, 1, 1))
        elif s_idx == 3:
            for i in range(5):
                phase = (t + i * 1.35) % 6.4
                if phase > 4.5:
                    continue
                px = BOARD_LEFT + 3 + int((i * 43 + phase * wind_x * 0.55
                                           + math.sin(phase * 2.1 + i) * 5) % w_span)
                py = BOARD_TOP + 1 + int((phase / 4.5) * (h_span - 3))
                col = (245, 240, 230) if i % 2 == 0 else (160, 205, 250)
                size = 2 if i == 0 else 1
                surf.fill(col, (px, py, size, size))

        # Simple weather-twist overlay particles.
        if twist_id == "rain":
            for i in range(12):
                rx = BOARD_LEFT + 2 + int((i * 23 - t * 22.0) % w_span)
                ry = BOARD_TOP + 2 + int((i * 17 + t * 68.0) % (h_span - 3))
                surf.fill((110, 190, 245), (rx, ry, 1, 3))
        elif twist_id in ("frost", "hailstorm"):
            for i in range(10):
                rx = BOARD_LEFT + 2 + int((i * 27 + t * 18.0) % w_span)
                ry = BOARD_TOP + 2 + int((i * 19 + t * 44.0) % (h_span - 2))
                surf.fill((215, 236, 255), (rx, ry, 2, 2))
        elif twist_id == "gale":
            for i in range(7):
                rx = BOARD_LEFT + 2 + int((i * 37 + t * 92.0) % max(1, w_span - 8))
                ry = BOARD_TOP + 4 + int((i * 17) % h_span)
                surf.fill((198, 212, 226), (rx, ry, 6, 1))
        elif twist_id in ("drought", "heatwave"):
            for i in range(8):
                rx = BOARD_LEFT + 4 + int((i * 31 + math.sin(t * 3.0 + i) * 3) % w_span)
                ry = BOARD_TOP + 2 + int((i * 21 - t * 16.0) % h_span)
                surf.fill((246, 168, 72), (rx, ry, 1, 2))
        elif twist_id in ("eclipse", "eternal_night"):
            for i in range(8):
                rx = BOARD_LEFT + 4 + int((i * 29) % w_span)
                ry = BOARD_TOP + 4 + int((i * 15) % h_span)
                if math.sin(t * 3.2 + i * 1.4) > 0.1:
                    surf.fill((186, 134, 244), (rx, ry, 1, 1))
