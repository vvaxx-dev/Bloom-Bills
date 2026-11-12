"""Ambient garden life: round-scaling critters, seasonal border foliage, and simple weather effects."""

import math
import random

import pygame

from . import data, gfx
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


def target_critter_count(rnd, cellar=False):
    rnd = max(1, int(rnd))
    base = 5 if cellar else 6
    extra = min(5, rnd // 18)
    return base + extra


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
        while aliens and len(roster) < max(4, count // 2):
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
    """Single ambient garden visitor moving along lanes, hopping, or fluttering."""

    def __init__(self, species, rng):
        self.species = species
        self.meta = CRITTER_SPECIES[species]
        self.motion = self.meta["motion"]
        self.anim_t = rng.random() * 10.0
        self.pause = 0.0
        self.hop_phase = 0.0
        self.hop_z = 0.0
        self.facing_left = rng.random() < 0.5

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

    def update(self, dt, rng):
        self.anim_t += dt
        spd = self.meta["speed"]

        if self.motion == "crawl":
            if self.pause > 0:
                self.pause -= dt
                return
            if rng.random() < dt * 0.35:
                self.pause = rng.uniform(0.2, 0.65)
                return
            if self.axis == "x":
                prev_x = self.x
                self.x += self.dir * spd * dt
                self.facing_left = self.dir < 0
                if self.x <= BOARD_LEFT:
                    self.x, self.dir, self.facing_left = float(BOARD_LEFT), 1.0, False
                elif self.x >= BOARD_RIGHT - 8:
                    self.x, self.dir, self.facing_left = float(BOARD_RIGHT - 8), -1.0, True
                else:
                    for lx in LANE_XS:
                        if (prev_x - lx) * (self.x - lx) <= 0 and rng.random() < 0.28:
                            self.x = float(lx)
                            self.axis = "y"
                            self.dir = rng.choice((-1.0, 1.0))
                            break
            else:
                prev_y = self.y
                self.y += self.dir * spd * dt
                if self.y <= BOARD_TOP:
                    self.y, self.dir = float(BOARD_TOP), 1.0
                elif self.y >= BOARD_BOTTOM - 6:
                    self.y, self.dir = float(BOARD_BOTTOM - 6), -1.0
                else:
                    for ly in LANE_YS:
                        if (prev_y - ly) * (self.y - ly) <= 0 and rng.random() < 0.35:
                            self.y = float(ly)
                            self.axis = "x"
                            self.dir = rng.choice((-1.0, 1.0))
                            self.facing_left = self.dir < 0
                            break

        elif self.motion == "hop":
            if self.pause > 0:
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
                self.pause = rng.uniform(0.35, 1.1)
                return
            self.hop_z = math.sin(self.hop_phase * math.pi) * 4.5
            self.x += self.dir * spd * dt
            if self.x <= BOARD_LEFT + 2:
                self.x, self.dir, self.facing_left = float(BOARD_LEFT + 2), 1.0, False
            elif self.x >= BOARD_RIGHT - 10:
                self.x, self.dir, self.facing_left = float(BOARD_RIGHT - 10), -1.0, True

        else:
            wobble = math.sin(self.anim_t * 3.1) * 8.0
            self.x += self.vx * dt
            self.y += (self.vy + wobble * 0.35) * dt
            if self.x <= BOARD_LEFT + 2:
                self.x, self.vx = float(BOARD_LEFT + 2), abs(self.vx)
            elif self.x >= BOARD_RIGHT - 11:
                self.x, self.vx = float(BOARD_RIGHT - 11), -abs(self.vx)
            if self.y <= BOARD_TOP + 2:
                self.y, self.vy = float(BOARD_TOP + 2), abs(self.vy)
            elif self.y >= BOARD_BOTTOM - 10:
                self.y, self.vy = float(BOARD_BOTTOM - 10), -abs(self.vy)
            if rng.random() < dt * 0.45:
                ang = rng.uniform(-0.7, 0.7)
                c, s = math.cos(ang), math.sin(ang)
                nvx = self.vx * c - self.vy * s
                nvy = self.vx * s + self.vy * c
                self.vx, self.vy = nvx, max(-14.0, min(14.0, nvy))
            self.facing_left = self.vx < -0.5

    def frame_index(self):
        if self.motion == "hop":
            return 1 if self.hop_z > 0.8 else 0
        if self.pause > 0:
            return 0
        return int(self.anim_t * self.meta["fps"]) % 2

    def draw(self, surf):
        frame = self.frame_index()
        sname = "critter_%s_%d" % (self.species, frame)
        sp = _critter_surface(sname, flip_x=self.facing_left, shadow=False)
        h = sp.get_height()
        px = int(round(self.x))
        py = int(round(self.y - h // 2 - self.hop_z))
        py = max(BOARD_TOP, min(BOARD_BOTTOM - h, py))
        if self.motion == "fly":
            shadow_y = min(BOARD_BOTTOM - 1, py + h + 2)
            surf.fill((20, 16, 28), (px + 2, shadow_y, max(2, sp.get_width() - 4), 1))
        elif self.hop_z > 0.5:
            gy = min(BOARD_BOTTOM - 1, int(round(self.y + h // 2 - 1)))
            surf.fill((20, 16, 28), (px + 2, gy, max(2, sp.get_width() - 4), 1))
        else:
            sh = _critter_surface(sname, flip_x=self.facing_left, shadow=True)
            surf.blit(sh, (px + 1, py + 1))
        surf.blit(sp, (px, py))


class GardenAmbient:
    """Manages round-scaled critters, seasonal border foliage, and simple weather effects."""

    def __init__(self, run):
        self.t = 0.0
        self.rng = random.Random((getattr(run, "seed", 1) or 1) * 65537 + 19)
        self._state_key = None
        self.critters = []
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

    def update(self, dt, run, cellar=False):
        self.t += dt
        self.sync(run, cellar=cellar)
        for c in self.critters:
            c.update(dt, self.rng)

    def draw_foliage(self, surf, run, cellar=False, plot_rects=()):
        """Draw simple seasonal foliage tufts around the garden border and plot corners."""
        if cellar:
            self._draw_cellar_foliage(surf)
            return

        s_idx = data.season_index(getattr(run, "round", 1))
        sway = int(round(math.sin(self.t * 1.8) * 0.7)) if self.t > 0 else 0

        # Anchor positions along the top verge, side paths, and lane intersections (all y >= 33).
        tufts = (
            (10, 34), (36, 34), (60, 34), (88, 34), (120, 34), (150, 34), (180, 34), (210, 34), (234, 34),
            (1, 50), (1, 88), (1, 126),
            (60, 72), (120, 72), (180, 72),
            (60, 110), (120, 110), (180, 110),
        )

        for idx, (tx, ty) in enumerate(tufts):
            dx = sway if idx % 2 == 0 else 0
            if s_idx == 0:
                # Spring: fresh green sprouts and pink/cream blossoms.
                surf.fill((46, 120, 62), (tx, ty + 1, 3, 2))
                surf.fill((88, 170, 72), (tx + dx, ty, 1, 2))
                surf.fill((150, 210, 100), (tx + 2 + dx, ty, 1, 2))
                if idx % 3 == 0:
                    pet = (240, 130, 170) if idx % 2 == 0 else (245, 240, 230)
                    surf.fill(pet, (tx + 1 + dx, ty - 1, 2, 2))
                    surf.fill((250, 210, 70), (tx + 1 + dx, ty, 1, 1))
            elif s_idx == 1:
                # Summer: lush tall emerald blades and golden wildflowers.
                surf.fill((46, 120, 62), (tx, ty + 1, 4, 2))
                surf.fill((88, 170, 72), (tx + dx, ty - 1, 1, 3))
                surf.fill((150, 210, 100), (tx + 2 + dx, ty - 1, 1, 3))
                surf.fill((88, 170, 72), (tx + 3, ty, 1, 2))
                if idx % 3 == 1:
                    surf.fill((250, 210, 70), (tx + 1 + dx, ty - 1, 2, 1))
            elif s_idx == 2:
                # Autumn: warm russet/amber leaf piles, dry gold grass, and tiny toadstools.
                col_a = (214, 150, 40) if idx % 2 == 0 else (240, 140, 50)
                col_b = (150, 40, 52) if idx % 3 == 0 else (130, 84, 52)
                surf.fill(col_b, (tx, ty + 1, 4, 1))
                surf.fill(col_a, (tx + 1 + dx, ty, 3, 1))
                if idx % 5 == 0:
                    surf.fill((245, 240, 230), (tx + 1, ty, 1, 2))
                    surf.fill((214, 64, 56), (tx, ty - 1, 3, 1))
            else:
                # Winter: snow puffs, frost sprigs, and icy needles.
                surf.fill((68, 136, 166), (tx, ty + 1, 4, 1))
                surf.fill((245, 240, 230), (tx, ty, 4, 1))
                if idx % 3 == 0:
                    surf.fill((46, 120, 62), (tx + 1, ty - 1, 2, 1))
                    surf.fill((245, 240, 230), (tx + 2, ty - 1, 1, 1))

        # Subtle seasonal rim accents on unlocked soil plots.
        for idx, (px, py, pw, ph) in enumerate(plot_rects):
            if s_idx == 0 and idx % 2 == 0:
                surf.fill((88, 170, 72), (px + 2, py + ph - 2, 2, 2))
                surf.fill((240, 130, 170), (px + 3, py + ph - 3, 1, 1))
            elif s_idx == 1 and idx % 2 == 1:
                surf.fill((88, 170, 72), (px + pw - 4, py + ph - 3, 2, 3))
                surf.fill((150, 210, 100), (px + pw - 3, py + ph - 4, 1, 2))
            elif s_idx == 2 and idx % 2 == 0:
                surf.fill((240, 140, 50), (px + 2, py + ph - 2, 3, 1))
                surf.fill((214, 64, 56), (px + pw - 5, py + ph - 2, 2, 1))
            elif s_idx == 3:
                surf.fill((225, 236, 248), (px + 2, py, 9, 1))
                surf.fill((225, 236, 248), (px + pw - 11, py, 8, 1))

    def _draw_cellar_foliage(self, surf):
        spikes = (14, 42, 76, 108, 144, 178, 212, 238)
        for idx, sx in enumerate(spikes):
            h = 3 if idx % 2 == 0 else 2
            surf.fill((58, 52, 76), (sx, BOARD_TOP, 3, h))
            surf.fill((84, 78, 106), (sx + 1, BOARD_TOP + h, 1, 1))
            if idx % 3 == 0:
                surf.fill((46, 120, 62), (sx, BOARD_BOTTOM - 1, 3, 2))
                surf.fill((120, 200, 210), (sx + 1, BOARD_BOTTOM - 2, 1, 1))

    def draw_foreground(self, surf, run, cellar=False):
        """Draw crawling/hopping/flying critters plus simple season & weather particles."""
        self.sync(run, cellar=cellar)
        for c in self.critters:
            c.draw(surf)
        self._draw_weather_and_season_fx(surf, run, cellar=cellar)

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

        # Seasonal ambient particles (petals, pollen motes, autumn leaves, snowflakes).
        for i in range(9):
            seed_x = i * 29 + (i % 3) * 11
            seed_y = i * 19 + (i % 4) * 7
            if s_idx == 0:
                px = BOARD_LEFT + 2 + int((seed_x + t * (wind_x + 4) + math.sin(t * 2.0 + i) * 5) % w_span)
                py = BOARD_TOP + 2 + int((seed_y + t * 11.0) % h_span)
                col = (240, 130, 170) if i % 2 == 0 else (245, 240, 230)
                surf.fill(col, (px, py, 2, 1))
            elif s_idx == 1:
                px = BOARD_LEFT + 2 + int((seed_x + t * (wind_x * 0.4) + math.sin(t * 1.6 + i) * 6) % w_span)
                py = BOARD_TOP + 2 + int((seed_y - t * 6.5) % h_span)
                col = (250, 210, 70) if i % 2 == 0 else (150, 210, 100)
                surf.fill(col, (px, py, 1, 1))
            elif s_idx == 2:
                px = BOARD_LEFT + 2 + int((seed_x + t * (wind_x + 7) + math.sin(t * 2.6 + i) * 6) % w_span)
                py = BOARD_TOP + 2 + int((seed_y + t * 14.0) % h_span)
                col = ((240, 140, 50), (214, 150, 40), (214, 64, 56))[i % 3]
                surf.fill(col, (px, py, 2, 1))
                surf.fill(col, (px + (i % 2), py + 1, 1, 1))
            else:
                px = BOARD_LEFT + 2 + int((seed_x + t * (wind_x * 0.6) + math.sin(t * 1.7 + i) * 4) % w_span)
                py = BOARD_TOP + 2 + int((seed_y + t * 10.5) % h_span)
                col = (245, 240, 230) if i % 2 == 0 else (160, 205, 250)
                surf.fill(col, (px, py, 1 + (i % 2), 1 + (i % 2)))

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
