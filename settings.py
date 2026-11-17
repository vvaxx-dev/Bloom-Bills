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

CLEAR_SKIES_CHANCE = 0.5
CRITTER_FEED_VALUE = 3
CRITTER_EAT_RADIUS = 10.0
CRITTER_EAT_COOLDOWN = 3.5
CURSOR_SNAIL_SPEED = 19.0
CURSOR_SNAIL_GRACE = 3.0
CURSOR_SNAIL_CATCH = 3.0

# Selling unplanted seeds: a seed sells for a fraction of the value the grown
# plant would fetch at the end of a round, so dumping a whole shelf is pocket
# money, not a strategy that beats planting.
SEED_SELL_SHARE = 0.25

# Mycelium: every harvest rolls `spread` for the patch to push into an empty
# orthogonal neighbour, and the patch also books ONE guaranteed expansion every
# MYCELIUM_CREEP_TIME seconds of round. The creep meter is shared by the whole
# patch rather than per plot, so a wide patch does not grow several times
# faster than a small one - it just has a bigger edge to grow from. The
# guaranteed creep is what makes a patch visibly grow across a round instead of
# depending on a coin flip you might never win. MYCELIUM_MAX_SPREAD caps how
# many plots ONE seed can take over, so mycelium cannot fill the garden free.
MYCELIUM_CREEP_TIME = 20.0
MYCELIUM_MAX_SPREAD = 3
MYCELIUM_CREEP_SHARE = 0.5    # of a plant's `spread`, rolled per harvest

# Underground cellar: grows nocturnal plants automatically at reduced speed,
# insulated from surface weather and boss hazards.
CELLAR_PLOTS = 4
CELLAR_SPEED = 0.75
CELLAR_PRICE = 250

# --- Garden hazards ---------------------------------------------------------
# Four hazards tick inside the round loop (see `data.TWISTS` and
# `Run._step_round`). They are all surface-only: the cellar stays dry, dark
# and unbothered, which is part of why a player buys it.
#
# Disease: a new case lands every DISEASE_PERIOD, and every sick plant gets a
# CONTAGION_CHANCE roll per CONTAGION_PERIOD to infect one planted neighbour.
# Shovelling is the only cure - the soil it leaves behind is clean.
DISEASE_PERIOD = 15.0
CONTAGION_PERIOD = 6.0
CONTAGION_CHANCE = 0.3
DISEASE_GROWTH = 0.55       # a sick plant grows at 55% speed
DISEASE_YIELD = 0.6         # ...and pays 60% of a healthy harvest
DISEASE_SALE = 0.6          # ...and sells for 60% when the round ends
#
# Meteor Shower: one random plot per METEOR_PERIOD. A planted hit either is
# destroyed (METEOR_DESTROY) or comes back starlit - mutated, and worth
# METEOR_BONUS on harvest and at the final sale. An empty hit leaves stardust
# in the soil for whatever you plant there next.
METEOR_PERIOD = 10.0
METEOR_DESTROY = 0.45
METEOR_BONUS = 1.5
#
# Weeds: an empty plot sprouts one every WEED_PERIOD, and a weedy plot seeds a
# neighbouring empty plot instead `WEED_SEED_CHANCE` of the time. Weedy soil
# cannot be planted, and every weed left standing costs WEED_FEE at the buzzer.
WEED_PERIOD = 12.0
WEED_SEED_CHANCE = 0.45
WEED_FEE = 6
#
# Aphids: a settled colony halves a plant's harvest, and the only way to shift
# it is the watering can - so the pest is really a tax on your watering timing.
APHID_PERIOD = 7.0
APHID_YIELD = 0.5
APHID_SALE = 0.7

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
# Hazard inks. `SICK` is mouldy rather than dead-green so it never competes with
# GOOD's "you can harvest this" green, and the two soil tints are the plot
# background recoloured, which is what makes a hazard readable at a glance.
SICK = (176, 196, 110)
SICK_SOIL = (92, 90, 56)
STARDUST = (214, 176, 96)
STARDUST_SOIL = (124, 100, 56)
APHID = (60, 80, 44)
WEED = (150, 210, 100)
