
RARITY_COLORS = {
    "common": (200, 196, 210),
    "uncommon": (120, 210, 110),
    "rare": (110, 170, 250),
    "legendary": (250, 190, 60),
    "mutant": (255, 110, 230), 
}
RARITY_WEIGHT = {"common": 60, "uncommon": 28, "rare": 10, "legendary": 3}

PLANTS = {
    "daisy":     {"name": "Daisy",         "tags": ["flower"],          "grow": 5,  "yield": 2,   "sell": 4,   "rarity": "common",   "color": (245, 240, 230)},
    "tomato":    {"name": "Tomato",        "tags": ["veg", "fruit"],    "grow": 8,  "yield": 6,   "sell": 10,  "rarity": "common",   "color": (214, 64, 56)},
    "sunflower": {"name": "Sunflower",     "tags": ["flower"],          "grow": 11, "yield": 14,  "sell": 24,  "rarity": "uncommon", "color": (250, 210, 70)},
    "cactus":    {"name": "Cactus",        "tags": ["desert"],          "grow": 15, "yield": 36,  "sell": 60,  "rarity": "uncommon", "color": (88, 170, 72)},
    "pumpkin":   {"name": "Pumpkin",       "tags": ["veg", "fruit"],    "grow": 20, "yield": 90,  "sell": 150, "rarity": "rare",     "color": (240, 140, 50)},
    "orchid":    {"name": "Golden Orchid", "tags": ["flower", "rare"],  "grow": 28, "yield": 300, "sell": 500, "rarity": "legendary", "color": (250, 190, 60)},
}
PLANT_ORDER = ["daisy", "tomato", "sunflower", "cactus", "pumpkin", "orchid"]

MUTANTS = {
    "daisy_shiny": {"base": "daisy", "name": "Shiny Daisy", 
                    "desc": "2x value, grows 20% faster.",
                    "grow_mult": 0.8, "yield_mult": 2.0, "sell_mult": 2.0,
                    "color": (180, 240, 255), "subs": {"w": (255, 220, 120), "y": (255, 255, 200)}},
    "tomato_prickly": {"base": "tomato",    "name": "Prickly Tomato",
                       "desc": "x2 value and counts as desert.",
                       "grow_mult": 1.2, "yield_mult": 2.0, "sell_mult": 2.0,
                       "tags_add": ["desert"],
                       "color": (255, 120, 90), "subs": {"r": (255, 120, 90), "R": (190, 70, 60)}},
    "sunflower_gold": {"base": "sunflower", "name": "Golden Sunflower",
                       "desc": "x3 value, grows 50% slower.",
                       "grow_mult": 1.5, "yield_mult": 3.0, "sell_mult": 3.0,
                       "color": (255, 240, 130), "subs": {"y": (255, 240, 130), "Y": (255, 200, 60)}},
    "cactus_saguaro": {"base": "cactus",    "name": "Saguaro",
                       "desc": "x2 value, +$4 per harvest, grows 25% slower.",
                       "grow_mult": 1.25, "yield_mult": 2.0, "sell_mult": 2.0,
                       "yield_add": 4,
                       "color": (140, 220, 100), "subs": {"m": (230, 80, 80), "g": (140, 220, 100), "G": (70, 150, 70)}},
    "pumpkin_giant":  {"base": "pumpkin",   "name": "Giant Pumpkin",
                       "desc": "x2.5 value, grows 60% slower.",
                       "grow_mult": 1.6, "yield_mult": 2.5, "sell_mult": 2.5,
                       "color": (255, 140, 40), "subs": {"o": (255, 140, 40), "Y": (200, 100, 30)}},
    "orchid_moon":    {"base": "orchid",    "name": "Moonlight Orchid",
                       "desc": "x2 value, grows 10% faster.",
                       "grow_mult": 0.9, "yield_mult": 2.0, "sell_mult": 2.0,
                       "color": (190, 170, 255), "subs": {"y": (190, 170, 255), "Y": (120, 95, 210), "m": (240, 240, 255)}},
}

def mutants_for(species):
    """Mutant ids a planted species can randomly turn into."""
    return [mid for mid, m in MUTANTS.items() if m["base"] == species]

def mutation_threshold(species):
    """Harvests a plant needs before each extra harvest can roll for a mutation. Fast plants need many harvests, slow plants only need a couple, so every specioes stays mutatable in one round."""
    grow = PLANTS[species]["grow"]
    return max(2, min(5, round(20 / grow)))

for _mid, mutant in MUTANTS.items():
    _base = PLANTS[mutant["base"]]
    PLANTS[_mid] = {
        "name": mutant["name"],
        "tags": list(_base["tags"]) + list(mutant.get("tags_add", [])),
        "grow": round(_base["grow"] * mutant["grow_mult"], 2),
        "yield": int(round(_base["yield"] * mutant["yield_mult"] + mutant.get("yield_add", 0))),
        "sell": int(round(_base["sell"] * mutant["sell_mult"])),
        "rarity": "mutant",
        "color": mutant["color"],
        "mutant": True,
        "base": mutant["base"],
        "desc": mutant["desc"],
        "subs": mutant.get("subs"),
    }

MILESTONES = [10, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000]

PACKS = {
    "garden":  {"name": "Garden Pack",  "cost": 30,  "unlock": 1,  "color": (88, 170, 72),  "dark": (46, 120, 62),
                "pool": {"daisy": 50, "tomato": 35, "sunflower": 12, "cactus": 3}},
    "harvest": {"name": "Harvest Pack", "cost": 100,  "unlock": 3,  "color": (240, 140, 50), "dark": (190, 100, 40),
                "pool": {"tomato": 30, "sunflower": 40, "cactus": 22, "pumpkin": 8}},
    "desert":  {"name": "Desert Pack",  "cost": 250,  "unlock": 6,  "color": (214, 120, 70), "dark": (150, 80, 50),
                "pool": {"cactus": 50, "pumpkin": 30, "sunflower": 15, "orchid": 5}},
    "golden":  {"name": "Golden Pack",  "cost": 750, "unlock": 9,  "color": (250, 210, 70), "dark": (214, 150, 40),
                "pool": {"pumpkin": 50, "cactus": 30, "orchid": 20}},
}
PACK_ORDER = ["garden", "harvest", "desert", "golden"]


def free_pack_weight(kind, rnd):
    if rnd < PACKS[kind]["unlock"]:
        return 0
    if kind == "garden":
        return max(10, 100 - 8 * (rnd - 1))
    return {"harvest": 60, "desert": 40, "golden": 15}[kind]


RELICS = {
    "green_thumb": {"name": "Green Thumb",    "rarity": "common",   "cost": 8,
                    "desc": "Flowers harvest +3.",
                    "effects": {"yield_add": [("flower", 3)]}},
    "big_can":     {"name": "Big Can",        "rarity": "common",   "cost": 10,
                    "desc": "Watering lasts 2s longer.",
                    "effects": {"water_time": 2}},
    "compost":     {"name": "Compost Heap",   "rarity": "common",   "cost": 12,
                    "desc": "Plants sell for double at round end.",
                    "effects": {"sell_mult": 1.0}},
    "fertilizer":  {"name": "Fertilizer",     "rarity": "common",   "cost": 14,
                    "desc": "All plants grow 20% faster.",
                    "effects": {"growth": 0.2}},
    "almanac":     {"name": "Almanac",        "rarity": "common",   "cost": 16,
                    "desc": "Rounds last 10s longer.",
                    "effects": {"round_time": 10}},
    "piggy_bank":  {"name": "Piggy Bank",     "rarity": "uncommon", "cost": 18,
                    "desc": "Earn 5% interest on your cash after each round.",
                    "effects": {"interest": 0.05}},
    "monoculture": {"name": "Monoculture",    "rarity": "uncommon", "cost": 20,
                    "desc": "x2.5 harvests if every plant is the same kind.",
                    "effects": {"mono_mult": 2.5}},
    "biodiversity": {"name": "Biodiversity",  "rarity": "uncommon", "cost": 20,
                    "desc": "+20% harvests per different kind planted.",
                    "effects": {"distinct_bonus": 0.2}},
    "beehive":     {"name": "Beehive",        "rarity": "uncommon", "cost": 22,
                    "desc": "Flowers harvest +3 for each flower touching them.",
                    "effects": {"adjacent": [("flower", "flower", 3)]}},
    "desert_rose": {"name": "Desert Rose",    "rarity": "uncommon", "cost": 24,
                    "desc": "Desert plants harvest x2.5.",
                    "effects": {"yield_mult": [("desert", 2.5)]}},
    "scarecrow":   {"name": "Scarecrow",      "rarity": "uncommon", "cost": 25,
                    "desc": "All harvests x1.5.",
                    "effects": {"yield_mult": [("all", 1.5)]}},
    "clover":      {"name": "Lucky Clover",   "rarity": "rare",     "cost": 26,
                    "desc": "Rare seeds are twice as likely in packs.",
                    "effects": {"pack_luck": 2.0}},
    "gardener":    {"name": "Hired Gardener", "rarity": "rare",     "cost": 30,
                    "desc": "Plots water themselves, non-stop.",
                    "effects": {"auto_water": True}},
    "catalog":     {"name": "Seed Catalog",   "rarity": "rare",     "cost": 35,
                    "desc": "One extra free pack each round.",
                    "effects": {"free_packs": 1}},
    "greenhouse":  {"name": "Greenhouse",     "rarity": "rare",     "cost": 40,
                    "desc": "All harvests x2. Plants grow 10% faster.",
                    "effects": {"yield_mult": [("all", 2.0)], "growth": 0.1}},
}
RELIC_ORDER = list(RELICS)

TWISTS = {
    "none":    {"name": "Fair Weather", "desc": "No twist. Enjoy it.",               "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False},
    "drought": {"name": "Drought",      "desc": "Plants grow 35% slower.",           "growth": 0.65, "yield": 1.0, "time": 0,   "ban": None,     "blight": False},
    "locusts": {"name": "Locusts",      "desc": "Harvests are worth 40% less.",      "growth": 1.0,  "yield": 0.6, "time": 0,   "ban": None,     "blight": False},
    "short":   {"name": "Short Days",   "desc": "The round is 20 seconds shorter.",  "growth": 1.0,  "yield": 1.0, "time": -20, "ban": None,     "blight": False},
    "frost":   {"name": "Frost",        "desc": "Desert plants cannot be planted.",  "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": "desert", "blight": False},
    "blight":  {"name": "Blight",       "desc": "A random plant withers halfway.",   "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": True},
}
RANDOM_TWISTS = ["drought", "locusts", "short", "frost", "blight"]


PERKS = {
    "cash":  {"name": "Deep Pockets", "desc": "Start each run with +$10 per level.",   "max": 10, "costs": [2, 2, 3, 3, 4, 4, 5, 5, 6, 6]},
    "plots": {"name": "Spare Plot",   "desc": "Start each run with +1 plot per level.", "max": 4,  "costs": [5, 8, 12, 20]},
    "packs": {"name": "Seed Stash",   "desc": "+1 free pack every round per level.",    "max": 2,  "costs": [10, 25]},
    "yield": {"name": "Green Thumbs", "desc": "+10% to all harvests per level.",        "max": 10, "costs": [3, 4, 5, 6, 7, 8, 9, 10, 12, 15]},
}
PERK_ORDER = ["cash", "plots", "packs", "yield"]


def bill_for_quota(k):
    """Bill amount for the k-th quota (k = 1, 2, 3 ...). Climbs forever."""
    if k <= 8:
        return int(round(300 * 5.0 ** (k - 1)))
    return int(round(300 * 5.0 ** 7 * 6.0 ** (k - 8)))
