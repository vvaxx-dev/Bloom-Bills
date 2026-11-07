
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
    "brown_mushroom": {"name": "Brown Mushroom", "tags": ["nocturnal", "mushroom"], "grow": 5,  "yield": 3,   "sell": 6,   "rarity": "common",   "color": (170, 130, 90)},
    "red_mushroom":   {"name": "Red Mushroom",   "tags": ["nocturnal", "mushroom"], "grow": 9,  "yield": 15,  "sell": 28,  "rarity": "uncommon", "color": (220, 70, 60)},
    "moonflower":     {"name": "Moonflower",     "tags": ["nocturnal", "flower"],   "grow": 14, "yield": 42,  "sell": 75,  "rarity": "rare",     "color": (150, 190, 250)},
    "queen_night":    {"name": "Queen of the Night", "tags": ["nocturnal", "flower"], "grow": 30, "yield": 340, "sell": 540, "rarity": "legendary", "color": (180, 120, 240)},
     "devil_ivy":  {"name": "Devil's Ivy",  "tags": ["nocturnal", "cursed", "flower"], "grow": 6,  "yield": 60,  "sell": 95,  "rarity": "rare",     "color": (120, 220, 110), "upkeep": 60},
    "widow_bloom": {"name": "Widow's Bloom", "tags": ["nocturnal", "cursed", "flower"], "grow": 18, "yield": 260, "sell": 420, "rarity": "legendary", "color": (230, 60, 90), "aura": "jealous"},
}
SURFACE_PLANTS = ["daisy", "tomato", "sunflower", "cactus", "pumpkin", "orchid"]
NOCTURNAL_PLANTS = ["brown_mushroom", "red_mushroom", "moonflower", "queen_night", "devil_ivy", "widow_bloom"]
PLANT_ORDER = SURFACE_PLANTS + NOCTURNAL_PLANTS

# --- mutations ---------------------------------------------------------
# A plant that survives enough harvests can turn into one of these.
# The *mults* scale the base plant's "grow" / "yield" / "sell" stats,
# "yield_add" adds flat harvest money, and "tags_add" gives the mutant
# extra tags so relic effects (e.g. Desert Rose) can key off it.
# "subs" recolors the base sprite so it looks different in the garden.
MUTANTS = {
    "daisy_shiny":    {"base": "daisy",     "name": "Shiny Daisy",
                       "desc": "x2 value, grows 20% faster.",
                       "grow_mult": 0.8, "yield_mult": 2.0, "sell_mult": 2.0,
                       "color": (180, 240, 255), "subs": {"w": (200, 245, 255), "y": (255, 220, 120)}},
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
    """Harvests a plant needs before each extra harvest can roll for a
    mutation. Fast plants need many harvests, slow plants only a couple,
    so every species stays realistically mutatable within one round."""
    grow = PLANTS[species]["grow"]
    return max(2, min(5, round(20 / grow)))

for _mid, _mut in MUTANTS.items():
    _base = PLANTS[_mut["base"]]
    PLANTS[_mid] = {
        "name": _mut["name"],
        "tags": list(_base["tags"]) + list(_mut.get("tags_add", [])),
        "grow": round(_base["grow"] * _mut["grow_mult"], 2),
        "yield": int(round(_base["yield"] * _mut["yield_mult"] + _mut.get("yield_add", 0))),
        "sell": int(round(_base["sell"] * _mut["sell_mult"])),
        "rarity": "mutant",
        "color": _mut["color"],
        "mutant": True,
        "base": _mut["base"],
        "desc": _mut["desc"],
        "subs": _mut.get("subs"),
    }

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
    "garden":  {"name": "Garden Pack",  "short": "GARDEN",    "cost": 30,  "unlock": 1,  "color": (88, 170, 72),  "dark": (46, 120, 62),
                "pool": {"daisy": 50, "tomato": 35, "sunflower": 12, "cactus": 3}},
    "harvest": {"name": "Harvest Pack", "short": "HARVEST",   "cost": 100,  "unlock": 3,  "color": (240, 140, 50), "dark": (190, 100, 40),
                "pool": {"tomato": 30, "sunflower": 40, "cactus": 22, "pumpkin": 8}},
    "desert":  {"name": "Desert Pack",  "short": "DESERT",    "cost": 250,  "unlock": 6,  "color": (214, 120, 70), "dark": (150, 80, 50),
                "pool": {"cactus": 50, "pumpkin": 30, "sunflower": 15, "orchid": 5}},
    "golden":  {"name": "Golden Pack",  "short": "GOLDEN",    "cost": 750, "unlock": 9,  "color": (250, 210, 70), "dark": (214, 150, 40),
                "pool": {"pumpkin": 50, "cactus": 30, "orchid": 20}},
    "nocturnal": {"name": "Nocturnal Pack", "short": "NOCTURNAL", "cost": 120, "unlock": 2, "color": (110, 80, 60), "dark": (70, 50, 40),
                  "pool": {"brown_mushroom": 40, "red_mushroom": 35, "moonflower": 20, "queen_night": 5}},
    "rare":    {"name": "Rare Pack",    "short": "RARE",      "cost": 400, "unlock": 4,  "color": (150, 90, 200), "dark": (96, 56, 140),
                "luck": 2.5, "pool": {"sunflower": 30, "cactus": 30, "pumpkin": 25, "orchid": 15}},
    "cursed":  {"name": "Cursed Pack",  "short": "CURSED",    "cost": 600, "unlock": 6,  "color": (120, 40, 60), "dark": (70, 24, 40),
                "pool": {"devil_ivy": 35, "widow_bloom": 20, "moonflower": 25, "queen_night": 20}},
}
PACK_ORDER = ["garden", "harvest", "desert", "golden", "nocturnal", "rare", "cursed"]


def free_pack_weight(kind, rnd):
    if rnd < PACKS[kind]["unlock"]:
        return 0
    if kind == "garden":
        return max(10, 100 - 8 * (rnd - 1))
    return {"harvest": 60, "desert": 40, "golden": 15, "nocturnal": 30, "rare": 12, "cursed": 6}[kind]


RELICS = {
    "green_thumb": {"name": "Green Thumb",    "rarity": "common",   "cost": 8,
                    "desc": "Flowers harvest +3.",
                     "effects": {"yield_add": [("flower", 3)]},
                    "levels": [{"stat": "flower", "goal": 150, "effects": {"yield_add": [("flower", 3)]},
                                "desc": "Flowers harvest +6 total."}]},
    "big_can":     {"name": "Big Can",        "rarity": "common",   "cost": 10,
                    "desc": "Watering lasts 2s longer.",
                    "effects": {"water_time": 2},
                    "levels": [{"stat": "water", "goal": 150, "effects": {"water_time": 1},
                                "desc": "Watering lasts 3s longer total."}]},
    "compost":     {"name": "Compost Heap",   "rarity": "common",   "cost": 12,
                    "desc": "Plants sell for double at round end.",
                    "effects": {"sell_mult": 1.0}},
    "fertilizer":  {"name": "Fertilizer",     "rarity": "common",   "cost": 14,
                    "desc": "All plants grow 20% faster.",
                    "effects": {"growth": 0.2},
                    "levels": [{"stat": "harvest", "goal": 250, "effects": {"growth": 0.2},
                                "desc": "All plants grow 40% faster total."}]},
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
                    "effects": {"yield_mult": [("all", 1.5)]},
                    "levels": [{"stat": "harvest", "goal": 400, "effects": {"yield_mult": [("all", 0.5)]},
                                "desc": "All harvests x2.25 total."}]},
    "clover":      {"name": "Lucky Clover",   "rarity": "rare",     "cost": 26,
                    "desc": "Rare seeds are twice as likely in packs.",
                    "effects": {"pack_luck": 2.0}},
    "gardener":    {"name": "Hired Gardener", "rarity": "rare",     "cost": 30,
                    "desc": "Plots water themselves, non-stop.",
                    "effects": {"auto_water": True}},
    "spore_lantern": {"name": "Spore Lantern", "rarity": "uncommon", "cost": 20,
                      "desc": "Mushroom harvests x2.",
                      "effects": {"yield_mult": [("mushroom", 2.0)]},
                      "levels": [
                          {"stat": "mushroom", "goal": 100, "effects": {"growth": 0.25},
                           "desc": "Mushrooms also grow 25% faster."},
                          {"stat": "mushroom", "goal": 300, "effects": {"yield_mult": [("mushroom", 1.0)]},
                           "desc": "Mushroom harvests x4 total."},
                      ]},
    "catalog":     {"name": "Seed Catalog",   "rarity": "rare",     "cost": 35,
                    "desc": "One extra free pack each round.",
                    "effects": {"free_packs": 1}},
    "greenhouse":  {"name": "Greenhouse",     "rarity": "rare",     "cost": 40,
                    "desc": "All harvests x2. Plants grow 10% faster.",
                    "effects": {"yield_mult": [("all", 2.0)], "growth": 0.1}},
}
RELIC_ORDER = list(RELICS)

TWISTS = {
    "none":       {"name": "Fair Weather", "desc": "No weather. Smooth sailing.",            "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "tone": "neutral"},
    "still":      {"name": "Dead Calm",    "desc": "Nothing stirs. A quiet day.",           "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "tone": "neutral"},
    "sunny":      {"name": "Sunny Day",    "desc": "All plants grow 25% faster.",           "growth": 1.25, "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "tone": "good"},
    "rain":       {"name": "Rain",         "desc": "Crops water themselves all round.",     "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "rain": True, "tone": "good"},
    "market":     {"name": "Market Day",   "desc": "Harvests are worth 25% more.",          "growth": 1.0,  "yield": 1.25, "time": 0,  "ban": None,     "blight": False, "tone": "good"},
    "eclipse":    {"name": "Eclipse",      "desc": "Dark at noon: nocturnal seeds grow on the surface. Sun-lovers grow 20% slower.", "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "eclipse": True, "tone": "neutral"},
    "drought":    {"name": "Drought",      "desc": "Plants grow 35% slower.",               "growth": 0.65, "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "tone": "bad"},
    "locusts":    {"name": "Locusts",      "desc": "Harvests are worth 40% less.",          "growth": 1.0,  "yield": 0.6, "time": 0,   "ban": None,     "blight": False, "tone": "bad"},
    "short":      {"name": "Short Days",   "desc": "The round is 20 seconds shorter.",      "growth": 1.0,  "yield": 1.0, "time": -20, "ban": None,     "blight": False, "tone": "bad"},
    "frost":      {"name": "Frost",        "desc": "Desert plants cannot be planted.",      "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": "desert", "blight": False, "tone": "bad"},
    "blight":     {"name": "Blight",       "desc": "A random plant withers halfway.",       "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": True,  "tone": "bad"},
    "crow_swarm": {"name": "Crow Swarm",   "desc": "Every 10s a crow eats a random plant.", "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "boss": True, "crow": 10, "tone": "bad"},
}
RANDOM_TWISTS = ["drought", "locusts", "short", "frost", "blight", "sunny", "rain", "market", "eclipse"]
MINOR_TWISTS = ["sunny", "rain", "market", "eclipse", "still"]     # rolled between quota rounds
BOSS_TWISTS = ["crow_swarm"]  


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
