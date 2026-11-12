"""Central configuration for display geometry, economy tuning, and UI colors."""

TITLE = "Bloom & Bills"

CANVAS_W, CANVAS_H = 320, 180
START_SCALE = 6
FPS = 60
BORDERLESS = True

COLS = 4
MAX_PLOTS = 12
START_PLOTS = 4
RELIC_SLOTS = 5

ROUND_TIME = 45
LATE_ROUND_TIME_DROP = 2
LATE_ROUND_TIME_FLOOR = 30
QUOTA_EVERY = 3
WIN_QUOTAS = 8
BASE_FREE_PACKS = 2
SEEDS_PER_PACK = 3
START_MONEY = 15

WATER_BOOST = 2.0
WATER_TIME = 4.5
WATER_REST = 3.0

PRICE_GROWTH = 1.5
PLOT_BASE_PRICE = 200
PLOT_PRICE_GROWTH = 3.0
REROLL_BASE_PRICE = 50
RELIC_PRICE_GROWTH = 1.3
RARE_RELIC_PRICE_GROWTH = 1.35

COMPOST_WINDOW = 15.0
MUTATION_CHANCE = 0.1

# Mycelium: every harvest rolls `spread` for the patch to push into an empty
# orthogonal neighbour, and each mycelium also fills a creep meter that books
# one guaranteed expansion every MYCELIUM_CREEP_TIME seconds of round. The
# guaranteed creep is what makes a patch visibly grow across a round instead of
# depending on a coin flip you might never win. MYCELIUM_MAX_SPREAD caps how
# many plots ONE seed can take over, so mycelium cannot fill the garden free.
MYCELIUM_CREEP_TIME = 14.0
MYCELIUM_MAX_SPREAD = 6
MYCELIUM_CREEP_SHARE = 0.5    # of a plant's `spread`, rolled per harvest

# Underground cellar: grows nocturnal plants automatically at reduced speed,
# insulated from surface weather and boss hazards.
CELLAR_PLOTS = 4
CELLAR_SPEED = 0.75
CELLAR_PRICE = 250

BOSS_EVERY = 9
SEASON_LENGTH = 9

BG = (30, 26, 46)
PANEL = (44, 38, 66)
PANEL_LIGHT = (64, 56, 92)
PANEL_DARK = (32, 27, 50)
TEXT = (238, 232, 220)
DIM = (150, 142, 170)
ACCENT = (250, 210, 70)
GOOD = (120, 210, 110)
BAD = (230, 90, 80)
WATER = (120, 200, 210)
SOIL = (110, 76, 52)
SOIL_DARK = (84, 56, 40)
BLACK = (0, 0, 0)
