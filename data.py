"""Static game content and balance tables: plants, mutants, packs, relics, weather, and perks."""

try:
    from .settings import (
        APHID_PERIOD, COMPOST_WINDOW, CONTAGION_PERIOD, DISEASE_PERIOD, METEOR_PERIOD,
        SEASON_LENGTH, WEED_PERIOD,
    )
except ImportError:
    from settings import (
        APHID_PERIOD, COMPOST_WINDOW, CONTAGION_PERIOD, DISEASE_PERIOD, METEOR_PERIOD,
        SEASON_LENGTH, WEED_PERIOD,
    )

RARITY_COLORS = {
    "common": (200, 196, 210),
    "uncommon": (120, 210, 110),
    "rare": (110, 170, 250),
    "legendary": (250, 190, 60),
    "mutant": (255, 110, 230),
    "exquisite": (100, 235, 225),
}
RARITY_WEIGHT = {"common": 60, "uncommon": 28, "rare": 10, "legendary": 3, "exquisite": 2}

# Canonical rarity ladder, lowest to highest. Every plant/relic catalogue in
# the game (Garden Index, seed shelf, round tray, shop, pack tooltips) is
# ordered by this ladder first, then alphabetically by display name, so a
# common never sits below a legendary just because it was added later.
# Mutants share the dedicated "mutant" rarity and always sort after the
# ordinary ladder in mixed lists.
RARITY_ORDER = ["common", "uncommon", "rare", "legendary", "exquisite"]
RARITY_RANK = {name: rank for rank, name in enumerate(RARITY_ORDER)}


def rarity_rank(rarity):
    """Sort rank for a rarity string; unknown/mutant rarities sort last."""
    return RARITY_RANK.get(rarity, len(RARITY_ORDER))


def sort_by_rarity(ids, table=None):
    """Return `ids` ordered by (rarity, display name) using `table` metadata.

    `table` defaults to the global PLANTS table at call time, so this helper
    can be defined before the plant table itself exists.
    """
    if table is None:
        table = PLANTS
    return sorted(
        ids,
        key=lambda sid: (
            rarity_rank(table[sid].get("rarity", "")),
            str(table[sid].get("name", sid)).lower(),
            str(sid),
        ),
    )

PLANTS = {
    "crystal_bloom": {"name": "Crystal Bloom", "tags": ["flower"], "grow": 25, "yield": 200, "sell": 350,
                      "rarity": "legendary", "color": (100, 210, 250), "mature_bonus": 20, "no_mutations": True,
                      "note": "+$20 base harvest per full second spent mature. Auto-harvest collects immediately.",
                      "lore": "Sits ripe and pays more the longer you let it stare at you. Patience, it turns out, is a crop."},
    "daisy":          {"name": "Daisy",              "tags": ["flower"],                      "grow": 5,  "yield": 2,   "sell": 4,   "rarity": "common",    "color": (245, 240, 230),
                       "lore": "The first thing she planted and the last thing she sold. Two dollars is two dollars with a letter on the table."},
    "tomato":         {"name": "Tomato",             "tags": ["veg", "fruit"],                "grow": 8,  "yield": 6,   "sell": 10,  "rarity": "common",    "color": (214, 64, 56),
                       "lore": "Grew under the kitchen window so she could shout at it while the kettle boiled."},
    "sunflower":      {"name": "Sunflower",          "tags": ["flower"],                      "grow": 11, "yield": 14,  "sell": 24,  "rarity": "uncommon",  "color": (250, 210, 70),
                       "lore": "Tall enough to shade the deed box. She called these the interest payments."},
    "cactus":         {"name": "Cactus",             "tags": ["desert"],                      "grow": 15, "yield": 36,  "sell": 60,  "rarity": "uncommon",  "color": (88, 170, 72),
                       "lore": "Plant it, forget it. Her description of half her marriages."},
    "pumpkin":        {"name": "Pumpkin",            "tags": ["veg", "fruit"],                "grow": 20, "yield": 90,  "sell": 150, "rarity": "rare",      "color": (240, 140, 50),
                       "lore": "The whole valley grew pumpkins the year the mill closed."},
    "orchid":         {"name": "Golden Orchid",      "tags": ["flower", "rare"],              "grow": 28, "yield": 300, "sell": 500, "rarity": "legendary", "color": (250, 190, 60),
                       "lore": "The only crop that ever cleared a bill on its own. She kept two plants and no illusions."},
    "brown_mushroom": {"name": "Brown Mushroom",     "tags": ["nocturnal", "mushroom"],       "grow": 5,  "yield": 3,   "sell": 6,   "rarity": "common",    "color": (170, 130, 90),
                       "lore": "Cellar money: small, quick, and unbothered by anything the sky does."},
    "red_mushroom":   {"name": "Red Mushroom",       "tags": ["nocturnal", "mushroom"],       "grow": 9,  "yield": 15,  "sell": 28,  "rarity": "uncommon",  "color": (220, 70, 60),
                       "lore": "Bright enough to read by. Moss swears the cellar lights itself on a good year."},
    "moonflower":     {"name": "Moonflower",         "tags": ["nocturnal", "flower"],         "grow": 14, "yield": 42,  "sell": 75,  "rarity": "rare",      "color": (150, 190, 250),
                       "lore": "Opens for the dark. Her best idea, and she never explained it twice."},
    "queen_night":    {"name": "Queen of the Night", "tags": ["nocturnal", "flower"],         "grow": 30, "yield": 340, "sell": 540, "rarity": "legendary", "color": (180, 120, 240),
                       "lore": "Thirty seconds, then a fortune, then the neighbours wake up."},
    "devil_ivy":      {"name": "Devil's Ivy",        "tags": ["nocturnal", "cursed", "flower"], "grow": 6, "yield": 60,  "sell": 95,  "rarity": "rare",      "color": (120, 220, 110), "upkeep": 60,
                       "lore": "Charges rent. She called it a tenant plant and gave it the corner bed."},
    "widow_bloom":    {"name": "Widow's Bloom",      "tags": ["nocturnal", "cursed", "flower"], "grow": 18, "yield": 260, "sell": 420, "rarity": "legendary", "color": (230, 60, 90),  "aura": "jealous",
                       "lore": "Gorgeous, jealous, and it will halve everything around it. There is a lesson in the will."},
    "potato":         {"name": "Potato",             "tags": ["veg", "root"],                 "grow": 6,  "yield": 5,   "sell": 9,   "rarity": "common",    "color": (196, 158, 104),
                       "lore": "Keeps in the ground. Keeps in the cellar. Keeps in a will."},
    "wheat":          {"name": "Wheat",              "tags": ["grain"],                       "grow": 9,  "yield": 13,  "sell": 22,  "rarity": "common",    "color": (230, 200, 110),
                       "lore": "Cheap, fast, and the reason the south fence leaned."},
    "corn":           {"name": "Corn",               "tags": ["veg", "grain"],                "grow": 12, "yield": 26,  "sell": 44,  "rarity": "uncommon",  "color": (250, 220, 80),
                       "lore": "Tall enough to hide in, which is how you and your cousins spent one entire summer."},
    "carrot":         {"name": "Carrot",             "tags": ["veg", "root"],                 "grow": 10, "yield": 19,  "sell": 32,  "rarity": "uncommon",  "color": (236, 122, 48),
                       "lore": "Pulls early, sells late. A good trick to learn from a root."},
    "cranberries":    {"name": "Cranberries",        "tags": ["fruit", "berry"],              "grow": 18, "yield": 72,  "sell": 125, "rarity": "rare",      "color": (198, 44, 74),
                       "lore": "Bogs on the north edge. Nobody else wanted that corner."},
    "saffron":        {"name": "Saffron",            "tags": ["flower", "spice"],             "grow": 26, "yield": 285, "sell": 490, "rarity": "legendary", "color": (226, 128, 68),
                       "lore": "Twenty-six seconds for a fortune, if you can sit still that long."},
    "aloe_vera":      {"name": "Aloe Vera",          "tags": ["desert", "succulent"],         "grow": 13, "yield": 30,  "sell": 52,  "rarity": "uncommon",  "color": (120, 200, 130),
                       "note": "Thick leaves hold water: a steady desert earner.",
                       "lore": "It holds water the way she held grudges: slowly, and for years."},
    "prickly_pear":   {"name": "Prickly Pear",       "tags": ["desert", "fruit"],             "grow": 17, "yield": 55,  "sell": 95,  "rarity": "rare",      "color": (202, 92, 148),
                       "note": "Slow and spiny, with fruit worth the wait.",
                       "lore": "Slow and spiny, and worth the wait, like this whole family."},
    "agave":          {"name": "Agave",              "tags": ["desert", "flower"],            "grow": 24, "yield": 180, "sell": 300, "rarity": "legendary", "color": (150, 195, 170),
                       "note": "The twin flower: one tall bloom and a huge payday.",
                       "lore": "One flower, once, then a huge payday. She approved of the economics."},
    "four_leaf_clover": {"name": "Four-Leaf Clover", "tags": ["flower", "lucky"],             "grow": 11, "yield": 3,   "sell": 12,  "rarity": "uncommon",  "color": (110, 200, 110),
                       "pays": False, "bloom_chance": 0.25, "bloom_mult": 1.5,
                       "note": "Pays nothing itself. Each harvest has a 25% chance to x1.5 a neighbour's base harvest for the round.",
                         "lore": "Pays nothing itself and makes the neighbours rich. She had a few friends like that."},
    "venus_flytrap":  {"name": "Venus Flytrap",      "tags": ["carnivore"],                   "grow": 12, "yield": 4,   "sell": 16,  "rarity": "rare",      "color": (200, 70, 100),
                       "feed": 2,
                       "note": "A poor payer alone, but every harvest anywhere feeds it $2 toward its next bite.",
                       "lore": "It eats what eats her beans. She considered that a partnership, not a pet."},
    "mycelium":       {"name": "Mycelium",           "tags": ["mushroom", "fungus"],          "grow": 8,  "yield": 6,   "sell": 12,  "rarity": "uncommon",  "color": (222, 204, 168),
                       "network": 0.12, "spread": 0.10, "spread_cap": 3, "no_mutations": True,
                       "note": "Creeps into empty plots to its left, right, up or down: roughly one harvest in twenty spreads the patch, and the patch grows one free plot every 20s. Each connected mycelium adds +12% to the whole patch, and one seed grows at most 3 extra plots a round.",
                       "lore": "The network under the shed floor. She watered it once, in 1991, and never again."},
}
FARMER_PLANTS = ["potato", "wheat", "corn", "carrot", "cranberries", "saffron"]
DESERT_PLANTS = ["cactus", "aloe_vera", "prickly_pear", "agave"]
FUNGUS_PLANTS = ["mycelium"]
SURFACE_PLANTS = [
    "daisy", "tomato", "sunflower", "cactus", "pumpkin", "orchid",
    "aloe_vera", "prickly_pear", "agave", "crystal_bloom", "four_leaf_clover", "venus_flytrap", "mycelium",
] + FARMER_PLANTS
NOCTURNAL_PLANTS = ["brown_mushroom", "red_mushroom", "moonflower", "queen_night", "devil_ivy", "widow_bloom"]
CELLAR_PLANTS = NOCTURNAL_PLANTS + FUNGUS_PLANTS
PLANT_ORDER = SURFACE_PLANTS + NOCTURNAL_PLANTS
GARDEN_PLANTS = [sid for sid in SURFACE_PLANTS if sid not in FARMER_PLANTS]

MUTANTS = {
    "daisy_shiny": {
        "base": "daisy", "name": "Shiny Daisy",
        "desc": "2x value, grows 20% faster.",
        "grow_mult": 0.8, "yield_mult": 2.0, "sell_mult": 2.0,
        "color": (180, 240, 255), "subs": {"w": (255, 220, 120), "y": (255, 255, 200)},
    },
    "tomato_prickly": {
        "base": "tomato", "name": "Prickly Tomato",
        "desc": "x2 value and counts as desert.",
        "grow_mult": 1.2, "yield_mult": 2.0, "sell_mult": 2.0, "tags_add": ["desert"],
        "color": (255, 120, 90), "subs": {"r": (255, 120, 90), "R": (190, 70, 60)},
    },
    "sunflower_gold": {
        "base": "sunflower", "name": "Golden Sunflower",
        "desc": "x3 value, grows 50% slower.",
        "grow_mult": 1.5, "yield_mult": 3.0, "sell_mult": 3.0,
        "color": (255, 240, 130), "subs": {"y": (255, 240, 130), "Y": (255, 200, 60)},
    },
    "cactus_saguaro": {
        "base": "cactus", "name": "Saguaro",
        "desc": "x2 value, +$4 per harvest, grows 25% slower.",
        "grow_mult": 1.25, "yield_mult": 2.0, "sell_mult": 2.0, "yield_add": 4,
        "color": (140, 220, 100), "subs": {"m": (230, 80, 80), "g": (140, 220, 100), "G": (70, 150, 70)},
    },
    "pumpkin_giant": {
        "base": "pumpkin", "name": "Giant Pumpkin",
        "desc": "x2.5 value, grows 60% slower.",
        "grow_mult": 1.6, "yield_mult": 2.5, "sell_mult": 2.5,
        "color": (255, 140, 40), "subs": {"o": (255, 140, 40), "Y": (200, 100, 30)},
    },
    "orchid_moon": {
        "base": "orchid", "name": "Moonlight Orchid",
        "desc": "x2 value, grows 10% faster.",
        "grow_mult": 0.9, "yield_mult": 2.0, "sell_mult": 2.0,
        "color": (190, 170, 255), "subs": {"y": (190, 170, 255), "Y": (120, 95, 210), "m": (240, 240, 255)},
    },
    "daisy_frost": {
        "base": "daisy", "name": "Frost Daisy",
        "desc": "x1.8 value, grows 30% faster.",
        "grow_mult": 0.7, "yield_mult": 1.8, "sell_mult": 1.8,
        "color": (200, 235, 255), "subs": {"w": (215, 245, 255), "y": (140, 205, 250)},
    },
    "tomato_heirloom": {
        "base": "tomato", "name": "Heirloom Tomato",
        "desc": "x2.4 value, +$2 a harvest, grows 15% slower.",
        "grow_mult": 1.15, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 2,
        "color": (250, 130, 70), "subs": {"g": (70, 155, 60), "r": (250, 130, 70), "R": (175, 60, 40)},
    },
    "sunflower_twin": {
        "base": "sunflower", "name": "Twin Sunflower",
        "desc": "x2.2 value, +$3 a harvest, grows 25% faster.",
        "grow_mult": 0.75, "yield_mult": 2.2, "sell_mult": 2.2, "yield_add": 3,
        "color": (255, 235, 140), "subs": {"y": (255, 235, 140), "Y": (255, 190, 50), "b": (150, 110, 50)},
    },
    "cactus_crown": {
        "base": "cactus", "name": "Crowned Cactus",
        "desc": "x2.6 value, grows 20% slower, counts as desert.",
        "grow_mult": 1.2, "yield_mult": 2.6, "sell_mult": 2.6, "tags_add": ["desert"],
        "color": (160, 225, 120), "subs": {"g": (160, 225, 120), "G": (85, 165, 80), "m": (255, 180, 90)},
    },
    "pumpkin_ghost": {
        "base": "pumpkin", "name": "Ghost Pumpkin",
        "desc": "x2.2 value, grows 30% faster.",
        "grow_mult": 0.7, "yield_mult": 2.2, "sell_mult": 2.2,
        "color": (200, 220, 245),
        "subs": {"o": (200, 220, 245), "Y": (140, 170, 215), "g": (150, 190, 220), "G": (110, 150, 180)},
    },
    "orchid_royal": {
        "base": "orchid", "name": "Royal Orchid",
        "desc": "x4 value, grows 70% slower.",
        "grow_mult": 1.7, "yield_mult": 4.0, "sell_mult": 4.0,
        "color": (255, 235, 140), "subs": {"y": (255, 245, 180), "Y": (235, 190, 70), "m": (255, 225, 130)},
    },
    "potato_gold": {
        "base": "potato", "name": "Golden Potato",
        "desc": "x2.2 value, +$2 a harvest, grows 35% slower.",
        "grow_mult": 1.35, "yield_mult": 2.2, "sell_mult": 2.2, "yield_add": 2,
        "color": (250, 210, 90),
        "subs": {"l": (255, 235, 140), "g": (245, 205, 95), "G": (200, 155, 55),
                 "s": (250, 220, 140), "b": (205, 165, 85)},
    },
    "wheat_ancient": {
        "base": "wheat", "name": "Ancient Wheat",
        "desc": "x2.4 value, +$3 a harvest, grows 15% faster.",
        "grow_mult": 0.85, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 3,
        "color": (255, 235, 155), "subs": {"y": (255, 235, 155), "Y": (225, 175, 60), "g": (115, 195, 90)},
    },
    "corn_caramel": {
        "base": "corn", "name": "Caramel Corn",
        "desc": "x2.5 value, +$4 a harvest, grows 25% slower.",
        "grow_mult": 1.25, "yield_mult": 2.5, "sell_mult": 2.5, "yield_add": 4,
        "color": (250, 190, 110), "subs": {"y": (250, 190, 110), "Y": (190, 110, 50), "g": (150, 185, 80)},
    },
    "carrot_giant": {
        "base": "carrot", "name": "Giant Carrot",
        "desc": "x2.6 value, +$4 a harvest, grows 40% slower.",
        "grow_mult": 1.4, "yield_mult": 2.6, "sell_mult": 2.6, "yield_add": 4,
        "color": (255, 150, 60), "subs": {"o": (255, 150, 60), "Y": (215, 95, 25), "g": (120, 200, 90)},
    },
    "cranberries_frost": {
        "base": "cranberries", "name": "Frost Cranberries",
        "desc": "x3 value, +$5 a harvest, grows 20% slower.",
        "grow_mult": 1.2, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 5,
        "color": (250, 145, 170),
        "subs": {"r": (245, 125, 160), "R": (175, 65, 105), "w": (235, 250, 255),
                 "l": (190, 235, 245), "g": (120, 185, 205), "G": (75, 130, 155)},
    },
    "saffron_sunset": {
        "base": "saffron", "name": "Sunset Saffron",
        "desc": "x3 value, +$6 a harvest, grows 30% slower.",
        "grow_mult": 1.3, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 6,
        "color": (255, 200, 110),
        "subs": {"p": (255, 185, 95), "P": (215, 115, 55), "m": (255, 230, 150),
                 "r": (255, 80, 65), "o": (255, 120, 50), "y": (255, 250, 200), "l": (185, 225, 115)},
    },
    "brown_mushroom_glow": {
        "base": "brown_mushroom", "name": "Glowing Mushroom",
        "desc": "x2 value, +$2 a harvest, grows 30% faster.",
        "grow_mult": 0.7, "yield_mult": 2.0, "sell_mult": 2.0, "yield_add": 2,
        "color": (150, 240, 185), "subs": {"b": (145, 235, 185), "s": (215, 255, 235)},
    },
    "red_mushroom_spotted": {
        "base": "red_mushroom", "name": "Spotted Mushroom",
        "desc": "x2.6 value, +$3 a harvest, grows 10% slower.",
        "grow_mult": 1.1, "yield_mult": 2.6, "sell_mult": 2.6, "yield_add": 3,
        "color": (255, 135, 70), "subs": {"r": (255, 135, 70), "w": (255, 245, 205)},
    },
    "moonflower_blood": {
        "base": "moonflower", "name": "Blood Moonflower",
        "desc": "x2.8 value, +$4 a harvest, grows 20% slower.",
        "grow_mult": 1.2, "yield_mult": 2.8, "sell_mult": 2.8, "yield_add": 4,
        "color": (245, 125, 155), "subs": {"c": (245, 125, 155), "w": (255, 220, 230), "p": (190, 60, 100)},
    },
    "queen_night_twilight": {
        "base": "queen_night", "name": "Twilight Queen",
        "desc": "x3 value, +$5 a harvest, grows 15% slower.",
        "grow_mult": 1.15, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 5,
        "color": (155, 150, 255), "subs": {"p": (155, 150, 255), "P": (95, 85, 200), "w": (235, 240, 255)},
    },
    "devil_ivy_crown": {
        "base": "devil_ivy", "name": "Devil's Crown",
        "desc": "x2.5 value, grows 10% faster, upkeep doubles.",
        "grow_mult": 0.9, "yield_mult": 2.5, "sell_mult": 2.5, "upkeep_mult": 2.0,
        "color": (245, 80, 80), "subs": {"g": (245, 80, 80), "G": (165, 30, 45), "p": (255, 200, 60)},
    },
    "devil_ivy_gilded": {
        "base": "devil_ivy", "name": "Gilded Ivy",
        "desc": "x3.2 value, grows 30% slower, upkeep x1.5.",
        "grow_mult": 1.3, "yield_mult": 3.2, "sell_mult": 3.2, "upkeep_mult": 1.5,
        "color": (255, 215, 90), "subs": {"g": (250, 210, 90), "G": (190, 140, 50), "p": (255, 255, 220)},
    },
    "widow_bloom_black": {
        "base": "widow_bloom", "name": "Black Widow",
        "desc": "x3 value, grows 20% faster, still jealous of its neighbours.",
        "grow_mult": 0.8, "yield_mult": 3.0, "sell_mult": 3.0,
        "color": (80, 80, 110), "subs": {"r": (80, 80, 110), "R": (40, 40, 60), "g": (95, 95, 125), "G": (65, 65, 90)},
    },
    "widow_bloom_wail": {
        "base": "widow_bloom", "name": "Wailing Widow",
        "desc": "x4 value, grows 40% slower, costs $40 upkeep.",
        "grow_mult": 1.4, "yield_mult": 4.0, "sell_mult": 4.0, "upkeep_add": 40,
        "color": (240, 95, 130), "subs": {"r": (240, 95, 130), "R": (145, 30, 65)},
    },
    "aloe_vera_bloom": {
        "base": "aloe_vera", "name": "Aloe Bloom",
        "desc": "x2.2 value, +$3 a harvest, grows 20% faster.",
        "grow_mult": 0.8, "yield_mult": 2.2, "sell_mult": 2.2, "yield_add": 3,
        "color": (155, 230, 165), "subs": {"g": (155, 230, 165), "G": (90, 165, 100), "l": (205, 245, 190)},
    },
    "aloe_vera_royal": {
        "base": "aloe_vera", "name": "Royal Aloe",
        "desc": "x2.8 value, +$5 a harvest, grows 25% slower.",
        "grow_mult": 1.25, "yield_mult": 2.8, "sell_mult": 2.8, "yield_add": 5,
        "color": (225, 200, 110), "subs": {"g": (225, 200, 110), "G": (170, 140, 60), "l": (250, 235, 170)},
    },
    "prickly_pear_gold": {
        "base": "prickly_pear", "name": "Golden Pear",
        "desc": "x2.4 value, +$5 a harvest, grows 20% slower.",
        "grow_mult": 1.2, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 5,
        "color": (250, 190, 80), "subs": {"m": (255, 215, 90), "g": (185, 200, 105), "G": (110, 145, 70)},
    },
    "prickly_pear_blood": {
        "base": "prickly_pear", "name": "Crimson Pear",
        "desc": "x3 value, +$7 a harvest, grows 35% slower.",
        "grow_mult": 1.35, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 7,
        "color": (225, 45, 70), "subs": {"m": (235, 50, 70), "g": (150, 175, 90), "G": (90, 120, 60)},
    },
    "agave_century": {
        "base": "agave", "name": "Century Plant",
        "desc": "x2.6 value, +$8 a harvest, grows 50% slower.",
        "grow_mult": 1.5, "yield_mult": 2.6, "sell_mult": 2.6, "yield_add": 8,
        "color": (175, 210, 190), "subs": {"g": (175, 210, 190), "G": (105, 150, 125), "l": (215, 235, 215), "y": (240, 225, 150), "Y": (195, 170, 90)},
    },
    "agave_twin": {
        "base": "agave", "name": "Twin Bloom Agave",
        "desc": "x3.2 value, +$10 a harvest, grows 10% faster.",
        "grow_mult": 0.9, "yield_mult": 3.2, "sell_mult": 3.2, "yield_add": 10,
        "color": (170, 230, 200), "subs": {"g": (170, 230, 200), "G": (90, 175, 145), "l": (215, 250, 230), "y": (255, 235, 130), "Y": (225, 175, 70)},
    },
    "five_leaf_clover": {
        "base": "four_leaf_clover", "name": "Five-Leaf Clover",
        "desc": "Still pays nothing. 50% chance to x2 a neighbour's base harvest.",
        "grow_mult": 1.0, "yield_mult": 3.0, "sell_mult": 3.0,
        "art": "five_leaf_clover", "bloom_chance": 0.5, "bloom_mult": 2.0,
        "color": (255, 225, 110),
        "subs": {"g": (255, 225, 110), "G": (205, 165, 45), "l": (255, 245, 175)},
    },
    "venus_flytrap_maneater": {
        "base": "venus_flytrap", "name": "Man-Eater",
        "desc": "Every harvest it eats a neighbouring plant and gains half that plant's base harvest.",
        "grow_mult": 1.1, "yield_mult": 2.0, "sell_mult": 2.5, "consume": True,
        "color": (245, 60, 85), "subs": {"r": (245, 60, 85), "R": (165, 20, 45), "w": (255, 200, 200)},
    },
    "venus_flytrap_gilded": {
        "base": "venus_flytrap", "name": "Gilded Trap",
        "desc": "x2.4 value, +$2 a harvest, grows 20% faster.",
        "grow_mult": 0.8, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 2,
        "color": (250, 205, 80), "subs": {"r": (250, 215, 100), "R": (185, 140, 40), "w": (255, 250, 215)},
    },
}


def mutants_for(species):
    """Return mutant ids that `species` can evolve into."""
    return [mid for mid, m in MUTANTS.items() if m["base"] == species]


def mutation_threshold(species):
    """Harvests required before each subsequent harvest rolls for mutation.

    Scales inversely with grow time (clamped to 2..5) so slow legendaries and
    fast commons both have realistic mutation odds within a single round.
    """
    grow = PLANTS[species]["grow"]
    return max(2, min(5, round(20 / grow)))


# Materialize mutant entries directly into PLANTS so harvest/sell/tag queries
# treat base species and mutants uniformly while preserving cursed penalties.
# Mechanics on a base plant are inherited by its mutants unless overridden.
_MECHANIC_KEYS = ("spread", "spread_cap", "network", "feed", "consume", "bloom_chance", "bloom_mult",
                  "pays", "no_mutations")
for _mid, _mutant in MUTANTS.items():
    _base = PLANTS[_mutant["base"]]
    _upkeep = int(round(_base.get("upkeep", 0) * _mutant.get("upkeep_mult", 1.0))) + _mutant.get("upkeep_add", 0)
    _entry = {
        "name": _mutant["name"],
        "tags": list(_base["tags"]) + list(_mutant.get("tags_add", [])),
        "grow": round(_base["grow"] * _mutant["grow_mult"], 2),
        "yield": int(round(_base["yield"] * _mutant["yield_mult"] + _mutant.get("yield_add", 0))),
        "sell": int(round(_base["sell"] * _mutant["sell_mult"])),
        "rarity": "mutant",
        "color": _mutant["color"],
        "mutant": True,
        "cursed_mutant": "cursed" in _base["tags"],
        "base": _mutant["base"],
        "desc": _mutant["desc"],
        "subs": _mutant.get("subs"),
    }
    if _mutant.get("art"):
        _entry["art"] = _mutant["art"]
    for _key in _MECHANIC_KEYS:
        if _key in _mutant:
            _entry[_key] = _mutant[_key]
        elif _key in _base:
            _entry[_key] = _base[_key]
    if _upkeep:
        _entry["upkeep"] = _upkeep
    if _base.get("aura") or _mutant.get("aura"):
        _entry["aura"] = _mutant.get("aura", _base.get("aura"))
    PLANTS[_mid] = _entry

# ---------------------------------------------------------------------------
# Crossbreeds: seeds that no pack sells. Two parent plants growing in
# orthogonally adjacent plots (above, below, left or right, on the same
# board — or one in the cellar plot directly below the other) can
# cross-pollinate: harvesting either parent rolls the recipe's
# `chance`, and a success drops one child seed straight into the seed shelf.
# There is no per-round cap, so a well-kept pair can be harvested again and
# again while its weather/season condition holds.
#
# Ordinary recipes accept a parent in any form: a Golden Sunflower still
# counts as a Sunflower. The Eclipse Sovereign is the exception — it demands
# the two exact mutant forms, and that exact match always takes precedence
# over the ordinary Eclipse Bloom recipe for the same pair of lineages.
# Crossbreeds never mutate further and appear in no pack pool.
CROSSBREEDS = {
    "eclipse_bloom": {
        "name": "Eclipse Bloom", "tags": ["flower", "nocturnal"],
        "grow": 15, "yield": 150, "sell": 260, "rarity": "legendary",
        "color": (205, 180, 245),
        "parents": ("sunflower", "moonflower"), "condition": "eclipse", "chance": 0.20,
        "hint": "WHEN DAY AND NIGHT BLOOM SIDE BY SIDE AND THE SUN GOES DARK, ONE FLOWER TRIES TO BE BOTH.",
        "note": "Sun and moon in one flower. Cellar or eclipse-top; races in the dark.",
    },
    "rainbow_daisy": {
        "name": "Rainbow Daisy", "tags": ["flower", "lucky"],
        "grow": 9, "yield": 45, "sell": 78, "rarity": "rare",
        "color": (250, 160, 200), "bloom_chance": 0.25, "bloom_mult": 1.5,
        "parents": ("daisy", "four_leaf_clover"), "condition": "rain", "chance": 0.20,
        "hint": "A LUCKY LITTLE DAISY, KISSED BY RAIN. AFTER A SHOWER, LUCK LEAVES COLOURS BEHIND.",
        "note": "Pays properly, and 25% of harvests x1.5 a neighbour for the round.",
    },
    "solar_saffron": {
        "name": "Solar Saffron", "tags": ["flower", "spice"],
        "grow": 24, "yield": 320, "sell": 550, "rarity": "legendary",
        "color": (250, 175, 60), "twist_growth": {"sunny": 1.25},
        "parents": ("saffron", "sunflower"), "condition": "sunny", "chance": 0.20,
        "hint": "SPICE THAT DREAMS OF THE SUN. BESIDE A SUNFLOWER ON A BRIGHT DAY, SAFFRON LEARNS TO DRINK LIGHT.",
        "note": "Grows a further 25% faster on Sunny Days.",
    },
    "spiny_pumpkin": {
        "name": "Spiny Pumpkin", "tags": ["desert", "veg", "fruit"],
        "grow": 22, "yield": 220, "sell": 380, "rarity": "rare",
        "color": (235, 145, 60), "hardy_twists": ("drought", "heatwave"), "hardy_growth": 1.25,
        "parents": ("cactus", "pumpkin"), "condition": "drought_heatwave", "chance": 0.20,
        "hint": "A PUMPKIN THAT TOOK LESSONS FROM A CACTUS. WHEN THE GROUND CRACKS, IT JUST GRINS WITH ITS SPINES.",
        "note": "Treats Drought and Heatwave as fair sun: x1.25 growth in both.",
    },
    "frost_tomato": {
        "name": "Frost Tomato", "tags": ["fruit", "berry"],
        "grow": 16, "yield": 110, "sell": 190, "rarity": "rare",
        "color": (240, 100, 85), "frost_hardy": True,
        "parents": ("tomato", "cranberries"), "condition": "frost", "chance": 0.20,
        "hint": "A TOMATO WITH CRANBERRY BLOOD, COLD AT HEART. SET IT BY CRANBERRIES WHEN THE FROST BITES AND SOMETHING HARDIER WAKES.",
        "note": "Winter-hardy: plantable during Frost.",
    },
    "ghost_bloom": {
        "name": "Ghost Bloom", "tags": ["nocturnal", "veg"],
        "grow": 18, "yield": 200, "sell": 345, "rarity": "legendary",
        "color": (215, 225, 240), "season_growth": {"Autumn": 1.25},
        "parents": ("pumpkin", "moonflower"), "condition": "autumn", "chance": 0.20,
        "hint": "IN AUTUMN, WHEN A MOONFLOWER LEANS TOO CLOSE TO A RIPENING PUMPKIN, SOMETHING PALE COMES TO HAUNT THE PATCH.",
        "note": "Grows 25% faster in Autumn. Quite at home in the dark.",
    },
    "maneater_tomato": {
        "name": "Man-Eater Tomato", "tags": ["carnivore", "fruit"],
        "grow": 14, "yield": 90, "sell": 155, "rarity": "rare",
        "color": (225, 75, 65), "consume": True, "feed": 2,
        "parents": ("venus_flytrap", "tomato"), "condition": "any", "chance": 0.15,
        "hint": "NEVER PLANT A TOMATO WITHIN SNAPPING DISTANCE OF A FLYTRAP UNLESS YOU MEAN IT. SOMETIMES THE TOMATO LEARNS.",
        "note": "Eats a neighbour per harvest for half its base. Fed $2 by harvests; eats critters.",
    },
    "lucky_orchid": {
        "name": "Lucky Orchid", "tags": ["flower", "rare", "lucky"],
        "grow": 28, "yield": 380, "sell": 650, "rarity": "legendary",
        "color": (250, 205, 85), "bloom_chance": 0.25, "bloom_mult": 1.5,
        "parents": ("four_leaf_clover", "orchid"), "condition": "any", "chance": 0.15,
        "hint": "AN ORCHID WITH A CLOVER AT ITS FEET, COUNTING ITS PETALS AND FINDING THEM LUCKY.",
        "note": "25% of its harvests x1.5 a neighbour's base harvest for the round.",
    },
    "prism_bloom": {
        "name": "Prism Bloom", "tags": ["flower", "rare"],
        "grow": 30, "yield": 450, "sell": 780, "rarity": "exquisite",
        "color": (175, 220, 250), "mature_bonus": 30,
        "parents": ("crystal_bloom", "orchid"), "condition": "any", "chance": 0.12,
        "hint": "WHERE CRYSTAL AND ORCHID SHARE THE LIGHT, THE LIGHT ITSELF TAKES ROOT AND REFUSES TO BE PICKED.",
        "note": "+$30 per full second mature. Auto-harvest starves it.",
    },
    "snap_aloe": {
        "name": "Snap Aloe", "tags": ["desert", "succulent", "carnivore"],
        "grow": 15, "yield": 70, "sell": 120, "rarity": "rare",
        "color": (120, 205, 125), "feed": 2,
        "parents": ("aloe_vera", "venus_flytrap"), "condition": "any", "chance": 0.15,
        "hint": "ALOE LEARNED PATIENCE FROM THE DESERT AND APPETITE FROM ITS NEIGHBOUR. MINCE NO WORDS: IT BITES.",
        "note": "Fed $2 by every harvest anywhere, critters included.",
    },
    "desert_bloom": {
        "name": "Desert Bloom", "tags": ["desert", "fruit", "flower"],
        "grow": 26, "yield": 350, "sell": 600, "rarity": "legendary",
        "color": (245, 155, 175),
        "parents": ("prickly_pear", "agave"), "condition": "any", "chance": 0.15,
        "hint": "ONCE IN A LONG DRY SPELL, THE PEAR AND THE AGAVE FLOWER AT THE SAME MOMENT, SIDE BY SIDE.",
        "note": "Desert, fruit and flower at once: feeds both pairing families.",
    },
    "eclipse_sovereign": {
        "name": "Eclipse Sovereign", "tags": ["flower", "nocturnal", "rare"],
        "grow": 18, "yield": 600, "sell": 1030, "rarity": "exquisite",
        "color": (255, 220, 130), "exact_parents": True,
        "parents": ("sunflower_gold", "moonflower_blood"), "condition": "eclipse", "chance": 0.08,
        "hint": "GOLD MUST WED BLOOD WHILE THE SKY IS SWALLOWED. TWO CROWNS, ONE DARKENED SUN, NO SECOND CHANCES PROMISED.",
        "note": "The garden's crowned chase seed. Handle with awe.",
    },
}
for _cid, _entry in CROSSBREEDS.items():
    _entry["crossbreed"] = True
    _entry["no_mutations"] = True
    PLANTS[_cid] = _entry

CROSSBREED_ORDER = sort_by_rarity(list(CROSSBREEDS))

# Board membership for crossbreeds: nocturnal crosses live in the cellar and
# join the surface tray during an eclipse, exactly like ordinary nocturnal
# plants; the rest are surface plants. Every catalogue list is then kept in
# rarity order (see RARITY_ORDER above) from here on.
_NOCTURNAL_CROSSBREEDS = [cid for cid in CROSSBREED_ORDER if "nocturnal" in CROSSBREEDS[cid]["tags"]]
_SURFACE_CROSSBREEDS = [cid for cid in CROSSBREED_ORDER if cid not in _NOCTURNAL_CROSSBREEDS]
SURFACE_PLANTS = sort_by_rarity(list(SURFACE_PLANTS) + _SURFACE_CROSSBREEDS)
NOCTURNAL_PLANTS = sort_by_rarity(list(NOCTURNAL_PLANTS) + _NOCTURNAL_CROSSBREEDS)
CELLAR_PLANTS = sort_by_rarity(list(NOCTURNAL_PLANTS) + list(FUNGUS_PLANTS))
PLANT_ORDER = sort_by_rarity(list(SURFACE_PLANTS) + list(NOCTURNAL_PLANTS))
FARMER_PLANTS = sort_by_rarity(list(FARMER_PLANTS))
DESERT_PLANTS = sort_by_rarity(
    [sid for sid in SURFACE_PLANTS if "desert" in PLANTS[sid]["tags"]]
)
GARDEN_PLANTS = [sid for sid in SURFACE_PLANTS if sid not in FARMER_PLANTS]

CROSSBREED_CONDITION_LABELS = {
    "eclipse": "ECLIPSE / ETERNAL NIGHT",
    "rain": "RAIN",
    "sunny": "SUNNY DAY",
    "drought_heatwave": "DROUGHT OR HEATWAVE",
    "frost": "FROST",
    "autumn": "AUTUMN",
    "any": "ANY WEATHER",
}


def crossbreed_condition_label(entry):
    """Short human label for the weather/season a crossbreed recipe needs."""
    return CROSSBREED_CONDITION_LABELS.get(entry.get("condition", "any"), "ANY WEATHER")


def crossbreed_recipe_text(entry):
    """One-line recipe for a discovered crossbreed, e.g. for the Garden Index."""
    parents = " + ".join(PLANTS[pid]["name"] for pid in entry["parents"])
    return "%s BESIDE EACH OTHER / %s" % (parents, crossbreed_condition_label(entry))


def crossbreed_condition_met(entry, twist_id, twist, season_name):
    """Whether the round's effective weather/season satisfies a recipe."""
    condition = entry.get("condition", "any")
    if condition == "any":
        return True
    if condition == "eclipse":
        return bool(twist and twist.get("eclipse"))
    if condition == "autumn":
        return season_name == "Autumn"
    if condition == "drought_heatwave":
        return twist_id in ("drought", "heatwave")
    return twist_id == condition


def _crossbreed_parent_key(species, entry):
    """How `species` counts toward a recipe: exact form, or its base lineage."""
    if entry.get("exact_parents"):
        return species
    return PLANTS[species].get("base", species)


def crossbreed_match(species_a, species_b, twist_id, twist, season_name):
    """Crossbreed id two adjacent plants can produce right now, or None.

    Exact-mutant recipes (the Eclipse Sovereign) outrank ordinary lineage
    recipes, so a crowned pair is never spent on the lesser child.
    """
    if species_a not in PLANTS or species_b not in PLANTS or species_a == species_b:
        return None
    matches = []
    for cid in CROSSBREED_ORDER:
        entry = PLANTS[cid]
        wanted = set(entry["parents"])
        got = {_crossbreed_parent_key(species_a, entry), _crossbreed_parent_key(species_b, entry)}
        if got != wanted:
            continue
        if not crossbreed_condition_met(entry, twist_id, twist, season_name):
            continue
        matches.append(cid)
    if not matches:
        return None
    matches.sort(key=lambda cid: 0 if PLANTS[cid].get("exact_parents") else 1)
    return matches[0]


def sort_mutants(ids):
    """Order mutant ids by their base plant's rarity, then by mutant name."""
    return sorted(
        ids,
        key=lambda mid: (
            rarity_rank(PLANTS[PLANTS[mid].get("base", mid)].get("rarity", "")),
            str(PLANTS[mid].get("name", mid)).lower(),
            str(mid),
        ),
    )


MILESTONES = [10, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000]

PACKS = {
    "garden":    {"name": "Garden Pack",    "short": "GARDEN",    "cost": 30,  "unlock": 1, "color": (88, 170, 72),  "dark": (46, 120, 62),
                  "pool": {"daisy": 50, "tomato": 32, "sunflower": 14, "venus_flytrap": 2, "mycelium": 2, "orchid": 1}},
    "farmer":    {"name": "Farmer Pack",    "short": "FARMER",    "cost": 120, "unlock": 2, "color": (190, 150, 70), "dark": (120, 88, 44),
                  "pool": {"potato": 40, "wheat": 30, "carrot": 16, "corn": 10, "cranberries": 3, "saffron": 1}},
    "harvest":   {"name": "Harvest Pack",   "short": "HARVEST",   "cost": 100, "unlock": 3, "color": (240, 140, 50), "dark": (190, 100, 40),
                  "pool": {"pumpkin": 30, "corn": 25, "cranberries": 20, "wheat": 15, "potato": 7, "carrot": 3}},
    "desert":    {"name": "Desert Pack",    "short": "DESERT",    "cost": 250, "unlock": 6, "color": (214, 120, 70), "dark": (150, 80, 50),
                  "pool": {"cactus": 40, "aloe_vera": 28, "prickly_pear": 22, "agave": 10}},
    "golden":    {"name": "Golden Pack",    "short": "GOLDEN",    "cost": 750, "unlock": 9, "color": (250, 210, 70), "dark": (214, 150, 40),
                  "pool": {"pumpkin": 50, "cactus": 30, "orchid": 20}},
    "nocturnal": {"name": "Nocturnal Pack", "short": "NOCTURNAL", "cost": 120, "unlock": 2, "color": (110, 80, 60), "dark": (70, 50, 40),
                  "pool": {"brown_mushroom": 34, "red_mushroom": 30, "mycelium": 18, "moonflower": 15, "queen_night": 3}},
    "rare":      {"name": "Rare Pack",      "short": "RARE",      "cost": 400, "unlock": 4, "color": (150, 90, 200), "dark": (96, 56, 140),
                  "luck": 2.5, "pool": {"sunflower": 28, "cactus": 24, "pumpkin": 20, "four_leaf_clover": 16, "orchid": 12, "crystal_bloom": 5}},
    "cursed":    {"name": "Cursed Pack",    "short": "CURSED",    "cost": 600, "unlock": 6, "color": (120, 40, 60), "dark": (70, 24, 40),
                  "pool": {"devil_ivy": 35, "widow_bloom": 20, "moonflower": 25, "queen_night": 20}},
}
PACK_ORDER = ["garden", "harvest", "farmer", "desert", "golden", "nocturnal", "rare", "cursed"]
_FREE_PACK_WEIGHTS = {
    "farmer": 70, "harvest": 60, "desert": 40, "golden": 15,
    "nocturnal": 30, "rare": 12, "cursed": 6,
}


# Pack pools are catalogues too: keep each pool's contents in rarity order so
# pack tooltips list commons before legendaries wherever they are shown.
for _pack in PACKS.values():
    _pack["pool"] = {sid: _pack["pool"][sid] for sid in sort_by_rarity(list(_pack["pool"]))}


def free_pack_weight(kind, rnd):
    """Selection weight for free round-start packs; Garden tapers off as better packs unlock."""
    if rnd < PACKS[kind]["unlock"]:
        return 0
    if kind == "garden":
        return max(10, 100 - 8 * (rnd - 1))
    return _FREE_PACK_WEIGHTS[kind]


RELICS = {
    "clear_skies": {"name": "Clear Skies", "rarity": "exquisite", "cost": 1000,
                    "desc": "50% chance at halfway to clear any weather or boss for the rest of the round.",
                    "effects": {"clear_weather": True},
                    "lore": "Half the valley swears she could talk a storm round. Moss swears the other half."},
    "chosen_bloom": {"name": "Chosen Bloom", "rarity": "exquisite", "cost": 1000,
                     "desc": "Click this relic, then choose one plant per round: grows 50% faster, harvests x2.",
                     "effects": {"choose_plant": True}},
    "green_thumb":   {"name": "Green Thumb",    "rarity": "common",   "cost": 90,
                      "desc": "Flowers harvest +3.",
                      "effects": {"yield_add": [("flower", 3)]},
                      "levels": [{"stat": "flower", "goal": 150, "effects": {"yield_add": [("flower", 3)]},
                                  "desc": "Flowers harvest +6 total."}]},
    "big_can":       {"name": "Big Can",        "rarity": "common",   "cost": 115,
                      "desc": "Watering lasts 2s longer.",
                      "effects": {"water_time": 2},
                      "levels": [{"stat": "water", "goal": 150, "effects": {"water_time": 1},
                                  "desc": "Watering lasts 3s longer total."}],
                      "lore": "Two extra seconds of soak per plot. She measured a good watering in curses, not litres."},
    "compost":       {"name": "Compost Heap",   "rarity": "common",   "cost": 130,
                      "desc": "In the last %ds of each round, harvests and plant sales pay x2." % int(COMPOST_WINDOW),
                      "effects": {"compost_window": COMPOST_WINDOW, "compost_mult": 2.0},
                      "lore": "Everything the garden could not use became the thing that made it grow. Moss explains this one slowly."},
    "fertilizer":    {"name": "Fertilizer",     "rarity": "common",   "cost": 145,
                      "desc": "All plants grow 20% faster.",
                      "effects": {"growth": 0.2},
                      "levels": [{"stat": "harvest", "goal": 250, "effects": {"growth": 0.2},
                                  "desc": "All plants grow 40% faster total."}]},
    "almanac":       {"name": "Almanac",        "rarity": "common",   "cost": 165,
                      "desc": "Rounds last 10s longer.",
                      "effects": {"round_time": 10},
                      "lore": "Ten more seconds of day, in her handwriting, with the useful pages dog-eared."},
    "piggy_bank":    {"name": "Piggy Bank",     "rarity": "uncommon", "cost": 475,
                      "desc": "Earn 5% interest on your cash after each round.",
                      "effects": {"interest": 0.05},
                      "lore": "Found in the coal scuttle with your name scratched in it. It was already cracked."},
    "monoculture":   {"name": "Monoculture",    "rarity": "uncommon", "cost": 500,
                      "desc": "x2.5 harvests if every plant is the same kind.",
                      "effects": {"mono_mult": 2.5}},
    "biodiversity":  {"name": "Biodiversity",   "rarity": "uncommon", "cost": 500,
                      "desc": "+20% harvests per different kind planted.",
                      "effects": {"distinct_bonus": 0.2}},
    "beehive":       {"name": "Beehive",        "rarity": "uncommon", "cost": 550,
                      "desc": "Flowers harvest +3 for each flower touching them.",
                      "effects": {"adjacent": [("flower", "flower", 3)]}},
    "desert_rose":   {"name": "Desert Rose",    "rarity": "uncommon", "cost": 580,
                      "desc": "Desert plants harvest x2.5.",
                      "effects": {"yield_mult": [("desert", 2.5)]}},
    "scarecrow":     {"name": "Scarecrow",      "rarity": "uncommon", "cost": 600,
                      "desc": "All harvests x1.5.",
                      "effects": {"yield_mult": [("all", 1.5)]},
                      "levels": [{"stat": "harvest", "goal": 400, "effects": {"yield_mult": [("all", 0.5)]},
                                  "desc": "All harvests x2.25 total."}],
                      "lore": "Her first defence against the flock and her last defence against company."},
    "clover":        {"name": "Lucky Clover",   "rarity": "rare",     "cost": 650,
                      "desc": "Rare seeds are twice as likely in packs.",
                      "effects": {"pack_luck": 2.0}},
    "gardener":      {"name": "Hired Gardener", "rarity": "rare",     "cost": 760,
                      "desc": "Plots water themselves, non-stop.",
                      "effects": {"auto_water": True},
                      "lore": "Hired once, in a bad October, and never fired. The can has not been dry since."},
    "spore_lantern": {"name": "Spore Lantern",  "rarity": "uncommon", "cost": 600,
                      "desc": "Mushroom harvests x2.",
                      "effects": {"yield_mult": [("mushroom", 2.0)]},
                      "levels": [
                          {"stat": "mushroom", "goal": 100, "effects": {"growth": 0.25},
                           "desc": "Mushrooms also grow 25% faster."},
                          {"stat": "mushroom", "goal": 300, "effects": {"yield_mult": [("mushroom", 1.0)]},
                           "desc": "Mushroom harvests x4 total."},
                      ]},
    "catalog":       {"name": "Seed Catalog",   "rarity": "rare",     "cost": 700,
                      "desc": "One extra free pack each round.",
                      "effects": {"free_packs": 1},
                      "lore": "Order what you do not have. She had the last page torn out, on purpose."},
    "greenhouse":    {"name": "Greenhouse",     "rarity": "rare",     "cost": 850,
                      "desc": "All harvests x2. Plants grow 10% faster.",
                      "effects": {"yield_mult": [("all", 2.0)], "growth": 0.1},
                      "lore": "Built from the parlour windows of the house next door, which she insisted was a loan."},
    "mutagen":       {"name": "Mutagen",        "rarity": "rare",     "cost": 800,
                      "desc": "25% chance a seed sprouts already mutated. Mutants are 1.2x better.",
                      "effects": {"mutate_on_plant": 0.25, "mutant_bonus": 0.2},
                      "levels": [{"stat": "harvest", "goal": 200, "effects": {"mutate_on_plant": 0.15},
                                  "desc": "40% chance to sprout mutated. Mutants are 1.2x better."}],
                      "lore": "Kept in a lemonade bottle under the bench. Do not ask what was in it, ask what it did."},
    "time_capsule":  {"name": "Time Capsule", "rarity": "rare", "cost": 780,
                      "desc": "Every 10s, bank 25% of the harvest money earned in the previous 10s.",
                      "effects": {"capsule_period": 10.0, "capsule_share": 0.25},
                      "lore": "A jam jar of coins buried for every round. 'Money waits better than people do.'"},
    "stock_market":  {"name": "Stock Market", "rarity": "rare", "cost": 720,
                      "desc": "Each round one species you own sells for 2x when the round ends.",
                      "effects": {"stock_market": 2.0},
                      "lore": "She never left this valley, and somehow always knew what the market was doing."},
    "collector":     {"name": "The Collector", "rarity": "rare", "cost": 820,
                      "desc": "Every different species planted makes all relic effects 2% stronger.",
                      "effects": {"relic_power": 0.02}},
    "emergency_generator": {"name": "Emergency Generator", "rarity": "rare", "cost": 690,
                      "desc": "During bad weather, all plants grow 20% faster.",
                      "effects": {"bad_weather_growth": 0.20}},
    "friendly_owl":  {"name": "The Friendly Owl", "rarity": "uncommon", "cost": 590,
                      "desc": "Scares off every crow and drops a bonus seed every 12s.",
                      "effects": {"scare_crows": True, "owl_seed_period": 12.0},
                      "lore": "A working bird, not a pet. She paid him in mice; he paid her in crows that were not there."},
    "sulphur_duster": {"name": "Sulphur Duster", "rarity": "uncommon", "cost": 420,
                       "desc": "Halves every Disease penalty, and neighbours catch it half as often.",
                       "effects": {"disease_resist": 0.5, "sick_relief": 0.5},
                       "lore": "Moss keeps a tin of sulphur by the shed door. 'Dust first,' he says. 'Ask your aunt about the low corner later.'"},
    "lightning_rod":  {"name": "Lightning Rod", "rarity": "rare", "cost": 760,
                       "desc": "Under this rod a meteor never destroys a crop - every strike only rewrites it into a starlit one.",
                       "effects": {"rod_protects": True},
                       "lore": "The barn lost its roof the summer the sky came down. Your aunt bolted this to the doorframe and never paid for repairs."},
    "eternal_snail": {"name": "Eternal Snail", "rarity": "exquisite", "cost": 1000,
                      "desc": "All plants grow 30% faster. A cursed snail follows your cursor: if it catches you, the run ends.",
                      "effects": {"growth": 0.30, "cursor_snail": True},
                      "lore": "Everything grows faster here, and something slow is always behind you. That is the whole deal."},
}
RELIC_ORDER = sort_by_rarity(list(RELICS), RELICS)

RELIC_SYNERGIES = {
    "green_thumb": {"tag": "flower", "min": 4, "growth": 0.05, "power": 0.10,
                    "desc": "4+ FLOWERS: +5% GROWTH, GREEN THUMB +10% POWER."},
    "beehive": {"tag": "flower", "min": 5, "growth": 0.05, "harvest": 0.05, "power": 0.10,
                "desc": "5+ FLOWERS: +5% GROWTH/+5% VALUE, BEEHIVE +10% POWER."},
    "desert_rose": {"tag": "desert", "min": 4, "growth": 0.08, "power": 0.10,
                    "desc": "4+ DESERT CROPS: +8% GROWTH, ROSE +10% POWER."},
    "spore_lantern": {"tag": "mushroom", "min": 4, "growth": 0.08, "harvest": 0.05, "power": 0.10,
                      "desc": "4+ MUSHROOMS: +8% GROWTH/+5% VALUE, LANTERN +10% POWER."},
    "scarecrow": {"tag": "veg", "min": 4, "growth": 0.05, "power": 0.10,
                  "desc": "4+ VEGETABLES: +5% GROWTH, SCARECROW +10% POWER."},
    "monoculture": {"mono": True, "min": 4, "growth": 0.06, "power": 0.10,
                    "desc": "4+ PLOTS OF ONE SPECIES: +6% GROWTH, MONOCULTURE +10% POWER."},
    "biodiversity": {"distinct": True, "min": 6, "growth": 0.04, "harvest": 0.03,
                     "power": 0.10, "all": True,
                     "desc": "6+ SPECIES: ALL +4% GROWTH/+3% VALUE, BIO +10% POWER."},
    "mutagen": {"mutant": True, "min": 2, "growth": 0.08, "power": 0.10,
                "desc": "2+ MUTANTS: +8% GROWTH, MUTAGEN +10% POWER."},
    "clear_skies": {"tag": "nocturnal", "min": 3, "weather": "eclipse",
                    "growth": 0.10,
                    "desc": "ECLIPSE/ETERNAL NIGHT + 3 NIGHT CROPS: +10% GROWTH."},
    "friendly_owl": {"tag": "carnivore", "min": 2, "harvest": 0.08,
                     "desc": "2+ CARNIVORES: +8% VALUE, OWL DROPS DOUBLE SEEDS."},
    "collector": {"distinct": True, "min": 5, "growth": 0.03, "power": 0.05, "all": True,
                  "desc": "5+ SPECIES: ALL +3% GROWTH, ALL RELICS +5% POWER."},
    "stock_market": {"rarity": ("rare", "legendary"), "min": 3, "power": 0.10,
                     "desc": "3+ RARE/LEGENDARY CROPS: RARE PICKS WEIGH +10%."},
}

def synergy_text(rid):
    """One-line description of a relic's plant pairing, or an empty string."""
    syn = RELIC_SYNERGIES.get(rid)
    return syn["desc"] if syn else ""

TWISTS = {
    # `short` is the one-line HUD version of `desc`. The forecast and the round
    # banner are a single 320px row, so every twist needs a line that fits; the
    # full `desc` stays in tooltips and the Garden Index where it can wrap.
    "none":          {"name": "Fair Weather",  "desc": "No weather. Smooth sailing.",        "growth": 1.0,  "yield": 1.0,  "time": 0,   "ban": None,     "blight": False, "tone": "neutral",
                      "short": "NO WEATHER. SMOOTH SAILING.",
                      "lore": "Your aunt called a still day 'the garden catching its breath'. It is the forecast you get least."},
    "still":         {"name": "Dead Calm",     "desc": "Nothing stirs. A quiet day.",        "growth": 1.0,  "yield": 1.0,  "time": 0,   "ban": None,     "blight": False, "tone": "neutral",
                      "short": "NOTHING STIRS. A QUIET DAY.",
                      "lore": "Nothing moves. Moss says that is either a blessing or the valley holding its breath."},
    "sunny":         {"name": "Sunny Day",     "desc": "All plants grow 25% faster.",        "growth": 1.25, "yield": 1.0,  "time": 0,   "ban": None,     "blight": False, "tone": "good",
                      "short": "ALL PLANTS GROW 25% FASTER.",
                      "lore": "Sunlight is the one thing on this place that was never mortgaged."},
    "rain":          {"name": "Rain",          "desc": "Crops water themselves all round.",  "growth": 1.0,  "yield": 1.0,  "time": 0,   "ban": None,     "blight": False, "rain": True, "tone": "good",
                      "short": "CROPS WATER THEMSELVES ALL ROUND.",
                      "lore": "'Let the sky do the chores,' says the shed door, in her handwriting."},
    "market":        {"name": "Market Day",    "desc": "Harvests are worth 25% more.",       "growth": 1.0,  "yield": 1.25, "time": 0,   "ban": None,     "blight": False, "tone": "good",
                      "short": "HARVESTS ARE WORTH 25% MORE.",
                      "lore": "The cart road fills at dawn. Everything you grow is worth a quarter more and the whole valley knows it."},
    "eclipse":       {"name": "Eclipse",       "desc": "Dark at noon: nocturnal seeds grow on the surface. Sun-lovers grow 20% slower.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "eclipse": True, "tone": "neutral",
                      "short": "NOCTURNAL SEEDS UP TOP. SUN-LOVERS -20%.",
                      "lore": "The day the birds roost: the dark came down from the sky instead of up from the cellar."},
    "drought":       {"name": "Drought",       "desc": "Plants grow 35% slower.",            "growth": 0.65, "yield": 1.0,  "time": 0,   "ban": None,     "blight": False, "tone": "bad",
                      "short": "PLANTS GROW 35% SLOWER.",
                      "lore": "Dust to the ankle. She swore timing the watering mattered more than what you planted."},
    "locusts":       {"name": "Locusts",       "desc": "Harvests are worth 40% less.",       "growth": 1.0,  "yield": 0.6,  "time": 0,   "ban": None,     "blight": False, "tone": "bad",
                      "short": "HARVESTS ARE WORTH 40% LESS.",
                      "lore": "They never eat a leaf. They just make everything you sell worth less, which she called the better trick."},
    "short":         {"name": "Short Days",    "desc": "The round is 20 seconds shorter.",   "growth": 1.0,  "yield": 1.0,  "time": -20, "ban": None,     "blight": False, "tone": "bad",
                      "short": "THE ROUND IS 20 SECONDS SHORTER.",
                      "lore": "That month the light closes the books for you, ready or not."},
    "frost":         {"name": "Frost",         "desc": "Desert plants cannot be planted.",   "growth": 1.0,  "yield": 1.0,  "time": 0,   "ban": "desert", "blight": False, "tone": "bad",
                      "short": "DESERT PLANTS CANNOT BE PLANTED.",
                      "lore": "Frost turns desert crops to glass. Anything that can go downstairs, send it down."},
    "blight":        {"name": "Blight",        "desc": "A random plant withers halfway.",    "growth": 1.0,  "yield": 1.0,  "time": 0,   "ban": None,     "blight": True,  "tone": "bad",
                      "short": "A RANDOM PLANT WITHERS AT HALFWAY.",
                      "lore": "One plant quits at exactly midday. She called it the tax on standing still."},
    "weeds":         {"name": "Weeds",         "desc": "Every 12s an empty plot sprouts weeds you cannot plant in, and each one left standing costs $6 at the buzzer.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "weed": WEED_PERIOD, "tone": "bad",
                      "short": "EMPTY PLOTS WEED EVERY 12S - DIG THEM OR PAY.",
                      "lore": "Weeds are not malicious, only patient, and patient costs six dollars a head at the buzzer."},
    "aphids":        {"name": "Aphids",        "desc": "Every 7s a colony settles on one crop and halves its harvest. Water that plot and they wash off.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "aphid": APHID_PERIOD, "tone": "bad",
                      "short": "APHIDS SETTLE EVERY 7S: WATER TO WASH THEM OFF.",
                      "lore": "Aphids hate two things: water, and a gardener with somewhere to be. Soak the plot and they are gone."},
    "crow_swarm":    {"name": "Crazy Crows!",  "desc": "Every 6s the flock eats a random plant - one at a time, all round. Mutants are 20% less likely to be picked.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "crow": 6, "crow_count": 1,
                      "crow_mutant_weight": 0.8, "tone": "bad",
                      "short": "THE FLOCK EATS A PLANT EVERY 6S.",
                      "lore": "Six seconds is all the flock needs. An owl works. Pride does not."},
    "hailstorm":     {"name": "Hailstorm",     "desc": "Every 7s hail batters the farm, knocking half of every plant's growth off.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "hail": 7, "tone": "bad",
                      "short": "HAIL EVERY 7S: EVERY PLANT LOSES HALF ITS GROWTH.",
                      "lore": "Hail only punishes what is still growing, which is her argument for letting a crop ripen early."},
    "root_rot":      {"name": "Root Rot",      "desc": "Every 8s rot takes a random plant out of the ground.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "rot": 8, "tone": "bad",
                      "short": "ROT TAKES A PLANT EVERY 8S.",
                      "lore": "Rot is disease with no manners: no warning, no spread, just one plant fewer."},
    "disease":       {"name": "Disease",       "desc": "Every 15s a crop catches the rot. Sick plants grow at 55% speed and pay 60%, and each one can infect a planted neighbour every 6s. Shovelling is the only cure, and it leaves clean soil.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True,
                      "disease": DISEASE_PERIOD, "contagion": CONTAGION_PERIOD, "tone": "bad",
                      "short": "A CROP SICKENS EVERY 15S, THEN SPREADS. SHOVEL IT.",
                      "lore": "She always lost the low corner first. Do not nurse a sick crop - dig it out. Half the garden is saved by quitting the other half early."},
    "meteor_shower": {"name": "Meteor Shower", "desc": "Every 10s a meteor picks a plot at random: 45% chance it flattens whatever grows there, otherwise the crop comes back starlit and worth x1.5. A strike on bare soil leaves stardust for your next seed.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True,
                      "meteor": METEOR_PERIOD, "tone": "bad",
                      "short": "EVERY 10S: A PLOT BURNS OR A CROP GOES STARLIT.",
                      "lore": "The sky comes down this way about once a generation. Bet on the mutation only with a plot you can afford to lose."},
    "heatwave":      {"name": "Heatwave",      "desc": "Water evaporates twice as fast and plants grow 15% slower.",
                      "growth": 0.85, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "dry": 2.0, "tone": "bad",
                      "short": "GROWTH -15%, WATER DRIES 2X FASTER.",
                      "lore": "Water dries in half the time. Moss's rule: soak what you are unsure about first."},
    "eternal_night": {"name": "Eternal Night", "desc": "The sun never comes up: nocturnal plants grow up top, sun-lovers sulk.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "eclipse": True, "tone": "bad",
                      "short": "NOCTURNAL SEEDS UP TOP, SUN-LOVERS SULK.",
                      "lore": "The sun forgets to come up and everything she kept downstairs runs the farm."},
    "gale":          {"name": "Gale",          "desc": "The wind strips 10s off the round and slows every plant 20%.",
                      "growth": 0.8, "yield": 1.0, "time": -10, "ban": None, "blight": False, "boss": True, "tone": "bad",
                      "short": "ROUND -10S, GROWTH -20%.",
                      "lore": "Ten seconds gone, a fifth of the growth gone. Tie the seed shelf down and plant short."},
    "ghost":         {"name": "The Garden Ghost", "desc": "Every 5s the ghost swaps two plants and restarts both from seed.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "ghost": 5, "autumn_only": True, "tone": "bad",
                      "short": "EVERY 5S TWO PLANTS SWAP AND RESTART.",
                      "lore": "She is still walking the rows in October. Do not chase her. Note which two plots she swapped, and replant."},
    "queen_bee":     {"name": "Queen Bee",     "desc": "Only flowering plants make honey for the Queen; every other surface plant is dormant.",
                      "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "honey_only": True, "tone": "bad",
                      "short": "ONLY FLOWERING PLANTS CAN GROW OR HARVEST.",
                      "lore": "The Queen pays for honey only. Every other crop stands in the bed doing nothing at all."},
}
RANDOM_TWISTS = ["drought", "locusts", "short", "frost", "blight", "weeds", "aphids",
                 "sunny", "rain", "market", "eclipse"]
MINOR_TWISTS = ["sunny", "rain", "market", "eclipse", "still"]
BOSS_TWISTS = [
    "crow_swarm", "hailstorm", "ghost", "queen_bee",
    "root_rot", "heatwave", "eternal_night", "gale",
    # The soil-and-sky hazards are appended rather than inserted, so the boss
    # each round number lands on never shifts: round 9 is still the crows.
    "disease", "meteor_shower",
]

# `bar` and `trim` tint the run topbar for the season: a dark, legible
# background plus the one-pixel rule under it. They deliberately stay close in
# brightness so the cash / timer / bill text keeps its contrast all year.
SEASONS = [
    {"name": "Spring", "short": "SPR", "art": "season_spring", "color": (130, 210, 120), "desc": "THE GARDEN WAKES UP.",
     "bar": (34, 52, 40), "trim": (96, 170, 96)},
    {"name": "Summer", "short": "SUM", "art": "season_summer", "color": (250, 210, 70),  "desc": "LONG DAYS, THIRSTY SOIL.",
     "bar": (56, 46, 26), "trim": (232, 176, 56)},
    {"name": "Autumn", "short": "AUT", "art": "season_autumn", "color": (240, 140, 50),  "desc": "THE LAST BIG HARVEST.",
     "bar": (56, 38, 28), "trim": (222, 116, 54)},
    {"name": "Winter", "short": "WIN", "art": "season_winter", "color": (150, 190, 250), "desc": "SHORT DAYS, COLD GROUND.",
     "bar": (30, 40, 56), "trim": (140, 180, 240)},
]

PERKS = {
    "cash":  {"name": "Deep Pockets", "max": 10, "costs": [3, 4, 5, 6, 7, 8, 10, 12, 14, 16],
              "desc": "+2% CASH INTEREST A LEVEL (25% AT MAX)", "now": "+{n}% INTEREST",
              "art": "heirloom_cash", "lore": "A well-guarded purse makes every banked coin earn a little more."},
    "plots": {"name": "Spare Plot",   "max": 4,  "costs": [8, 12, 18, 26],
              "desc": "ONE MORE STARTING PLOT PER LEVEL", "now": "+{n} PLOT{s}",
              "art": "heirloom_plots", "lore": "More ground means more chances to make the harvest count."},
    "packs": {"name": "Seed Stash",   "max": 2,  "costs": [10, 18],
              "desc": "ONE MORE FREE PACK A ROUND PER LEVEL", "now": "+{n} PACK{s}",
              "art": "heirloom_packs", "lore": "A family seed box keeps the next season stocked."},
    "yield": {"name": "Green Thumbs", "max": 10, "costs": [5, 6, 8, 10, 12, 14, 16, 18, 20, 24],
              "desc": "+10% TO EVERY HARVEST PER LEVEL", "now": "+{n}%",
              "art": "heirloom_yield", "lore": "A green thumb coaxes more value from every harvest."},
}
PERKS["relics"] = {"name": "Relic Cabinet", "max": 3, "costs": [35, 60, 100],
                   "desc": "RELIC DISCOUNT, THEN EXTRA SLOTS", "now": "{n}",
                   "art": "heirloom_relics", "lore": "A cabinet of old relics makes room for greater wonders."}
PERKS["penny"] = {"name": "Lucky Penny", "max": 3, "costs": [7, 11, 16],
                  "desc": "CHANCE OF A FREE RELIC AFTER A BILL", "now": "+{n}% FREE RELIC CHANCE",
                  "art": "heirloom_penny",
                  "lore": "A penny found the morning after every bill. Reroll the shop and the free offer vanishes."}
PERKS["clock"] = {"name": "Antique Clock", "max": 3, "costs": [9, 14, 20],
                  "desc": "2S OF FREE GROWTH PER LEVEL EACH ROUND", "now": "+{n}S FREE GROWTH",
                  "art": "heirloom_clock",
                  "lore": "Its hands jump forward when the round begins, so every seed wakes up a little older."}
PERKS["insurance"] = {"name": "Old Insurance Card", "max": 1, "costs": [24],
                      "desc": "ONE FREE BILL WAIVER PER RUN", "now": "1 FREE BILL WAIVER",
                      "art": "heirloom_insurance",
                      "lore": "Faded, stamped, and good for exactly one bill the collector would rather not discuss."}
PERK_ORDER = ["cash", "plots", "packs", "yield", "relics", "penny", "clock", "insurance"]
PERK_STEP = {"cash": 2, "plots": 1, "packs": 1, "yield": 10,
             "penny": 8, "clock": 2, "insurance": 1}
PERK_COST_GROWTH = 1.15


def deep_pockets_pct(level):
    """Interest percentage for Deep Pockets (+2% per level from 1..9, jumping to 25% at level 10)."""
    level = max(0, int(level))
    if level == 0:
        return 0
    if level >= PERKS["cash"]["max"]:
        return 25
    return 2 * level


def deep_pockets_rate(level):
    return deep_pockets_pct(level) / 100.0


def packs_for_plant(species):
    """Return pack ids whose seed pool contains `species`."""
    return [kind for kind in PACK_ORDER if species in PACKS[kind]["pool"]]


# ---------------------------------------------------------------------------
# Garden lore: the story side of the tables.
#
# Bloom & Bills tells its story in the margins rather than in cutscenes, so the
# `lore` keys sit inside `PLANTS`, `TWISTS`, and `RELICS` on the text the player
# already reads: the forecast tooltip, the seed shelf, the relic card. Half of
# them are also honest mechanical hints - "aphids hate water", "a strike on bare
# soil leaves stardust" - because Moss would never hand over a rule without
# wrapping it in something Aunt Marigold once said to him. His dialogue in
# `tutorial.py` speaks these same lines, and never rewrites them.


def plant_lore(species):
    """The line of house history on a plant card; mutants inherit their base crop's."""
    sp = PLANTS.get(species) or {}
    if sp.get("lore"):
        return sp["lore"]
    if sp.get("mutant"):
        return (PLANTS.get(sp.get("base")) or {}).get("lore", "")
    return ""


def twist_lore(twist_id):
    """The line of garden folklore under a forecast, or an empty string."""
    return (TWISTS.get(twist_id) or {}).get("lore", "")


def produces_honey(species):
    """Whether a plant can keep working during the Queen Bee boss round.

    Honey production is deliberately tag based, so flower mutations and future
    flower species inherit the behaviour without needing another lookup table.
    """
    return species in PLANTS and "flower" in PLANTS[species].get("tags", ())


def perk_cost(key, level):
    """Heirloom cost to upgrade `key` from `level` to `level + 1` (0 once maxed)."""
    perk = PERKS[key]
    if level >= perk["max"]:
        return 0
    return int(round(perk["costs"][level] * PERK_COST_GROWTH ** level))


def perk_text(key, level):
    """Format the cumulative bonus label for `key` at `level`."""
    if key == "relics":
        return ["NO BONUS", "RELICS 15% OFF", "15% OFF, 6 OWNED", "15% OFF, 6 OWNED, 4 OFFERS"][max(0, min(3, level))]
    if key == "insurance":
        return "1 FREE BILL WAIVER" if level else "NO BONUS"
    n = deep_pockets_pct(level) if key == "cash" else PERK_STEP[key] * level
    if not n:
        return "NO BONUS"
    return PERKS[key]["now"].format(n=n, s="" if n == 1 else "S")


def bill_for_quota(k):
    """Target cash owed on the k-th bill (5x through quota 8, then 6x in endless play)."""
    if k <= 8:
        return int(round(300 * 5.0 ** (k - 1)))
    return int(round(300 * 5.0 ** 7 * 6.0 ** (k - 8)))


def season_index(rnd):
    return ((max(1, int(rnd)) - 1) // SEASON_LENGTH) % len(SEASONS)


def season_number(rnd):
    """1-based count of seasons elapsed so far in the run."""
    return (max(1, int(rnd)) - 1) // SEASON_LENGTH + 1


def season(rnd):
    return SEASONS[season_index(rnd)]


def is_new_season(rnd):
    return (int(rnd) - 1) % SEASON_LENGTH == 0
