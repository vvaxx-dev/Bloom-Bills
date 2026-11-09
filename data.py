
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
     "potato":      {"name": "Potato",      "tags": ["veg", "root"],            "grow": 6,  "yield": 5,   "sell": 9,   "rarity": "common",   "color": (196, 158, 104)},
    "wheat":       {"name": "Wheat",       "tags": ["grain"],                  "grow": 9,  "yield": 13,  "sell": 22,  "rarity": "common",   "color": (230, 200, 110)},
    "corn":        {"name": "Corn",        "tags": ["veg", "grain"],           "grow": 12, "yield": 26,  "sell": 44,  "rarity": "uncommon", "color": (250, 220, 80)},
    "carrot":      {"name": "Carrot",      "tags": ["veg", "root"],            "grow": 10, "yield": 19,  "sell": 32,  "rarity": "uncommon", "color": (236, 122, 48)},
    "cranberries": {"name": "Cranberries", "tags": ["fruit", "berry"],         "grow": 18, "yield": 72,  "sell": 125, "rarity": "rare",     "color": (198, 44, 74)},
    "saffron":     {"name": "Saffron",     "tags": ["flower", "spice"],        "grow": 26, "yield": 285, "sell": 490, "rarity": "legendary", "color": (226, 128, 68)},
}
FARMER_PLANTS = ["potato", "wheat", "corn", "carrot", "cranberries", "saffron"]
SURFACE_PLANTS = ["daisy", "tomato", "sunflower", "cactus", "pumpkin", "orchid"] + FARMER_PLANTS
NOCTURNAL_PLANTS = ["brown_mushroom", "red_mushroom", "moonflower", "queen_night", "devil_ivy", "widow_bloom"]
PLANT_ORDER = SURFACE_PLANTS + NOCTURNAL_PLANTS

# --- mutations ---------------------------------------------------------

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
    # --- a second roll for the garden flowers --------------------------
    "daisy_frost":    {"base": "daisy",     "name": "Frost Daisy",
                       "desc": "x1.8 value, grows 30% faster.",
                       "grow_mult": 0.7, "yield_mult": 1.8, "sell_mult": 1.8,
                       "color": (200, 235, 255), "subs": {"w": (215, 245, 255), "y": (140, 205, 250)}},
    "tomato_heirloom": {"base": "tomato",   "name": "Heirloom Tomato",
                        "desc": "x2.4 value, +$2 a harvest, grows 15% slower.",
                        "grow_mult": 1.15, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 2,
                        "color": (250, 130, 70), "subs": {"g": (70, 155, 60), "r": (250, 130, 70), "R": (175, 60, 40)}},
    "sunflower_twin": {"base": "sunflower", "name": "Twin Sunflower",
                       "desc": "x2.2 value, +$3 a harvest, grows 25% faster.",
                       "grow_mult": 0.75, "yield_mult": 2.2, "sell_mult": 2.2, "yield_add": 3,
                       "color": (255, 235, 140), "subs": {"y": (255, 235, 140), "Y": (255, 190, 50), "b": (150, 110, 50)}},
    "cactus_crown":   {"base": "cactus",    "name": "Crowned Cactus",
                       "desc": "x2.6 value, grows 20% slower, counts as desert.",
                       "grow_mult": 1.2, "yield_mult": 2.6, "sell_mult": 2.6,
                       "tags_add": ["desert"],
                       "color": (160, 225, 120), "subs": {"g": (160, 225, 120), "G": (85, 165, 80), "m": (255, 180, 90)}},
    "pumpkin_ghost":  {"base": "pumpkin",   "name": "Ghost Pumpkin",
                       "desc": "x2.2 value, grows 30% faster.",
                       "grow_mult": 0.7, "yield_mult": 2.2, "sell_mult": 2.2,
                       "color": (200, 220, 245), "subs": {"o": (200, 220, 245), "Y": (140, 170, 215), "g": (150, 190, 220), "G": (110, 150, 180)}},
    "orchid_royal":   {"base": "orchid",    "name": "Royal Orchid",
                       "desc": "x4 value, grows 70% slower.",
                       "grow_mult": 1.7, "yield_mult": 4.0, "sell_mult": 4.0,
                       "color": (255, 235, 140), "subs": {"y": (255, 245, 180), "Y": (235, 190, 70), "m": (255, 225, 130)}},

    # --- the farmer crops ---------------------------------------------
    "potato_gold":    {"base": "potato",    "name": "Golden Potato",
                       "desc": "x2.2 value, +$2 a harvest, grows 35% slower.",
                       "grow_mult": 1.35, "yield_mult": 2.2, "sell_mult": 2.2, "yield_add": 2,
                       "color": (250, 210, 90), "subs": {"l": (255, 235, 140), "g": (245, 205, 95), "G": (200, 155, 55),
                                                          "s": (250, 220, 140), "b": (205, 165, 85)}},
    "wheat_ancient":  {"base": "wheat",     "name": "Ancient Wheat",
                       "desc": "x2.4 value, +$3 a harvest, grows 15% faster.",
                       "grow_mult": 0.85, "yield_mult": 2.4, "sell_mult": 2.4, "yield_add": 3,
                       "color": (255, 235, 155), "subs": {"y": (255, 235, 155), "Y": (225, 175, 60), "g": (115, 195, 90)}},
    "corn_caramel":   {"base": "corn",      "name": "Caramel Corn",
                       "desc": "x2.5 value, +$4 a harvest, grows 25% slower.",
                       "grow_mult": 1.25, "yield_mult": 2.5, "sell_mult": 2.5, "yield_add": 4,
                       "color": (250, 190, 110), "subs": {"y": (250, 190, 110), "Y": (190, 110, 50), "g": (150, 185, 80)}},
    "carrot_giant":   {"base": "carrot",    "name": "Giant Carrot",
                       "desc": "x2.6 value, +$4 a harvest, grows 40% slower.",
                       "grow_mult": 1.4, "yield_mult": 2.6, "sell_mult": 2.6, "yield_add": 4,
                       "color": (255, 150, 60), "subs": {"o": (255, 150, 60), "Y": (215, 95, 25), "g": (120, 200, 90)}},
    "cranberries_frost": {"base": "cranberries", "name": "Frost Cranberries",
                          "desc": "x3 value, +$5 a harvest, grows 20% slower.",
                          "grow_mult": 1.2, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 5,
                          "color": (250, 145, 170), "subs": {"w": (240, 150, 175), "l": (195, 75, 105), "g": (155, 50, 80),
                                                             "G": (100, 30, 55), "b": (195, 75, 105)}},
    "saffron_sunset": {"base": "saffron",   "name": "Sunset Saffron",
                       "desc": "x3 value, +$6 a harvest, grows 30% slower.",
                       "grow_mult": 1.3, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 6,
                       "color": (255, 200, 110), "subs": {"w": (255, 210, 125), "l": (255, 225, 155), "g": (240, 170, 70),
                                                          "G": (190, 120, 45), "b": (240, 170, 70)}},

    # --- the nocturnal shelf ------------------------------------------
    "brown_mushroom_glow": {"base": "brown_mushroom", "name": "Glowing Mushroom",
                            "desc": "x2 value, +$2 a harvest, grows 30% faster.",
                            "grow_mult": 0.7, "yield_mult": 2.0, "sell_mult": 2.0, "yield_add": 2,
                            "color": (150, 240, 185), "subs": {"b": (145, 235, 185), "s": (215, 255, 235)}},
    "red_mushroom_spotted": {"base": "red_mushroom", "name": "Spotted Mushroom",
                             "desc": "x2.6 value, +$3 a harvest, grows 10% slower.",
                             "grow_mult": 1.1, "yield_mult": 2.6, "sell_mult": 2.6, "yield_add": 3,
                             "color": (255, 135, 70), "subs": {"r": (255, 135, 70), "w": (255, 245, 205)}},
    "moonflower_blood": {"base": "moonflower", "name": "Blood Moonflower",
                         "desc": "x2.8 value, +$4 a harvest, grows 20% slower.",
                         "grow_mult": 1.2, "yield_mult": 2.8, "sell_mult": 2.8, "yield_add": 4,
                         "color": (245, 125, 155), "subs": {"c": (245, 125, 155), "w": (255, 220, 230), "p": (190, 60, 100)}},
    "queen_night_twilight": {"base": "queen_night", "name": "Twilight Queen",
                             "desc": "x3 value, +$5 a harvest, grows 15% slower.",
                             "grow_mult": 1.15, "yield_mult": 3.0, "sell_mult": 3.0, "yield_add": 5,
                             "color": (155, 150, 255), "subs": {"p": (155, 150, 255), "P": (95, 85, 200), "w": (235, 240, 255)}},

    # --- cursed pack specials----------------------------------------
    "devil_ivy_crown": {"base": "devil_ivy", "name": "Devil's Crown",
                        "desc": "x2.5 value, grows 10% faster, upkeep doubles.",
                        "grow_mult": 0.9, "yield_mult": 2.5, "sell_mult": 2.5, "upkeep_mult": 2.0,
                        "color": (245, 80, 80), "subs": {"g": (245, 80, 80), "G": (165, 30, 45), "p": (255, 200, 60)}},
    "devil_ivy_gilded": {"base": "devil_ivy", "name": "Gilded Ivy",
                         "desc": "x3.2 value, grows 30% slower, upkeep x1.5.",
                         "grow_mult": 1.3, "yield_mult": 3.2, "sell_mult": 3.2, "upkeep_mult": 1.5,
                         "color": (255, 215, 90), "subs": {"g": (250, 210, 90), "G": (190, 140, 50), "p": (255, 255, 220)}},
    "widow_bloom_black": {"base": "widow_bloom", "name": "Black Widow",
                          "desc": "x3 value, grows 20% faster, still jealous of its neighbours.",
                          "grow_mult": 0.8, "yield_mult": 3.0, "sell_mult": 3.0,
                          "color": (80, 80, 110), "subs": {"r": (80, 80, 110), "R": (40, 40, 60), "g": (95, 95, 125), "G": (65, 65, 90)}},
    "widow_bloom_wail": {"base": "widow_bloom", "name": "Wailing Widow",
                         "desc": "x4 value, grows 40% slower, costs $40 upkeep.",
                         "grow_mult": 1.4, "yield_mult": 4.0, "sell_mult": 4.0, "upkeep_add": 40,
                         "color": (240, 95, 130), "subs": {"r": (240, 95, 130), "R": (145, 30, 65)}},
}

def mutants_for(species):
    """Mutant ids a planted species can randomly turn into."""
    return [mid for mid, m in MUTANTS.items() if m["base"] == species]

def mutation_threshold(species):
    """Harvests a plant needs before each extra harvest can roll for a mutation. Fast plants need many harvests, slow plants only need a couple, so every species stays realistically mutatable within one round."""
    grow = PLANTS[species]["grow"]
    return max(2, min(5, round(20 / grow)))

for _mid, mutant in MUTANTS.items():
    _base = PLANTS[mutant["base"]]
    _upkeep = int(round(_base.get("upkeep", 0) * mutant.get("upkeep_mult", 1.0))) + mutant.get("upkeep_add", 0)
    PLANTS[_mid] = {
        "name": mutant["name"],
        "tags": list(_base["tags"]) + list(mutant.get("tags_add", [])),
        "grow": round(_base["grow"] * mutant["grow_mult"], 2),
        "yield": int(round(_base["yield"] * mutant["yield_mult"] + mutant.get("yield_add", 0))),
        "sell": int(round(_base["sell"] * mutant["sell_mult"])),
        "rarity": "mutant",
        "color": mutant["color"],
        "mutant": True,
        "cursed_mutant": "cursed" in _base["tags"],
        "base": mutant["base"],
        "desc": mutant["desc"],
        "subs": mutant.get("subs"),
    }
    if _upkeep:
        # a cursed plant stays cursed when it mutates - it just bills harder
        PLANTS[_mid]["upkeep"] = _upkeep
    if _base.get("aura") or mutant.get("aura"):
        PLANTS[_mid]["aura"] = mutant.get("aura", _base.get("aura"))

MILESTONES = [10, 25, 50, 100, 150, 200, 300, 400, 500, 750, 1000]

PACKS = {
    "garden":  {"name": "Garden Pack",  "short": "GARDEN",    "cost": 30,  "unlock": 1,  "color": (88, 170, 72),  "dark": (46, 120, 62),
                "pool": {"daisy": 50, "tomato": 35, "sunflower": 12, "cactus": 3}},
    "farmer":  {"name": "Farmer Pack",  "short": "FARMER",    "cost": 120, "unlock": 2,  "color": (190, 150, 70), "dark": (120, 88, 44),
                "pool": {"potato": 40, "wheat": 30, "carrot": 16, "corn": 10, "cranberries": 3, "saffron": 1}},
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
PACK_ORDER = ["garden", "harvest", "farmer", "desert", "golden", "nocturnal", "rare", "cursed"]


def free_pack_weight(kind, rnd):
    if rnd < PACKS[kind]["unlock"]:
        return 0
    if kind == "garden":
        return max(10, 100 - 8 * (rnd - 1))
    return {"farmer": 70, "harvest": 60, "desert": 40, "golden": 15, "nocturnal": 30, "rare": 12, "cursed": 6}[kind]


RELICS = {
    "green_thumb": {"name": "Green Thumb",    "rarity": "common",   "cost": 90,
                    "desc": "Flowers harvest +3.",
                     "effects": {"yield_add": [("flower", 3)]},
                    "levels": [{"stat": "flower", "goal": 150, "effects": {"yield_add": [("flower", 3)]},
                                "desc": "Flowers harvest +6 total."}]},
    "big_can":     {"name": "Big Can",        "rarity": "common",   "cost": 115,
                    "desc": "Watering lasts 2s longer.",
                    "effects": {"water_time": 2},
                    "levels": [{"stat": "water", "goal": 150, "effects": {"water_time": 1},
                                "desc": "Watering lasts 3s longer total."}]},
    "compost":     {"name": "Compost Heap",   "rarity": "common",   "cost": 130,
                    "desc": "Plants sell for double at round end.",
                    "effects": {"sell_mult": 1.0}},
    "fertilizer":  {"name": "Fertilizer",     "rarity": "common",   "cost": 145,
                    "desc": "All plants grow 20% faster.",
                    "effects": {"growth": 0.2},
                    "levels": [{"stat": "harvest", "goal": 250, "effects": {"growth": 0.2},
                                "desc": "All plants grow 40% faster total."}]},
    "almanac":     {"name": "Almanac",        "rarity": "common",   "cost": 165,
                    "desc": "Rounds last 10s longer.",
                    "effects": {"round_time": 10}},
    "piggy_bank":  {"name": "Piggy Bank",     "rarity": "uncommon", "cost": 475,
                    "desc": "Earn 5% interest on your cash after each round.",
                    "effects": {"interest": 0.05}},
    "monoculture": {"name": "Monoculture",    "rarity": "uncommon", "cost": 500,
                    "desc": "x2.5 harvests if every plant is the same kind.",
                    "effects": {"mono_mult": 2.5}},
    "biodiversity": {"name": "Biodiversity",  "rarity": "uncommon", "cost": 500,
                    "desc": "+20% harvests per different kind planted.",
                    "effects": {"distinct_bonus": 0.2}},
    "beehive":     {"name": "Beehive",        "rarity": "uncommon", "cost": 550,
                    "desc": "Flowers harvest +3 for each flower touching them.",
                    "effects": {"adjacent": [("flower", "flower", 3)]}},
    "desert_rose": {"name": "Desert Rose",    "rarity": "uncommon", "cost": 580,
                    "desc": "Desert plants harvest x2.5.",
                    "effects": {"yield_mult": [("desert", 2.5)]}},
    "scarecrow":   {"name": "Scarecrow",      "rarity": "uncommon", "cost": 600,
                    "desc": "All harvests x1.5.",
                    "effects": {"yield_mult": [("all", 1.5)]},
                    "levels": [{"stat": "harvest", "goal": 400, "effects": {"yield_mult": [("all", 0.5)]},
                                "desc": "All harvests x2.25 total."}]},
    "clover":      {"name": "Lucky Clover",   "rarity": "rare",     "cost": 650,
                    "desc": "Rare seeds are twice as likely in packs.",
                    "effects": {"pack_luck": 2.0}},
    "gardener":    {"name": "Hired Gardener", "rarity": "rare",     "cost": 2300,
                    "desc": "Plots water themselves, non-stop.",
                    "effects": {"auto_water": True}},
    "spore_lantern": {"name": "Spore Lantern", "rarity": "uncommon", "cost": 600,
                      "desc": "Mushroom harvests x2.",
                      "effects": {"yield_mult": [("mushroom", 2.0)]},
                      "levels": [
                          {"stat": "mushroom", "goal": 100, "effects": {"growth": 0.25},
                           "desc": "Mushrooms also grow 25% faster."},
                          {"stat": "mushroom", "goal": 300, "effects": {"yield_mult": [("mushroom", 1.0)]},
                           "desc": "Mushroom harvests x4 total."},
                      ]},
    "catalog":     {"name": "Seed Catalog",   "rarity": "rare",     "cost": 700,
                    "desc": "One extra free pack each round.",
                    "effects": {"free_packs": 1}},
    "greenhouse":  {"name": "Greenhouse",     "rarity": "rare",     "cost": 850,
                    "desc": "All harvests x2. Plants grow 10% faster.",
                    "effects": {"yield_mult": [("all", 2.0)], "growth": 0.1}},
     "mutagen":     {"name": "Mutagen",        "rarity": "rare",     "cost": 800,
                    "desc": "25% chance a seed sprouts already mutated. Mutants are 1.2x better.",
                    "effects": {"mutate_on_plant": 0.25, "mutant_bonus": 0.2},
                    "levels": [{"stat": "harvest", "goal": 200, "effects": {"mutate_on_plant": 0.15},
                                "desc": "40% chance to sprout mutated. Mutants are 1.2x better."}]},
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
    "crow_swarm": {"name": "Crazy Crows!",  "desc": "Every 6s the flock eats a random plant - one at a time, all round.", "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "boss": True, "crow": 6, "crow_count": 1, "tone": "bad",
                   "short": "THE FLOCK EATS A PLANT EVERY 6S."},
    "hailstorm":  {"name": "Hailstorm",     "desc": "Every 7s hail batters the farm, knocking half of every plant's growth off.", "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "boss": True, "hail": 7, "tone": "bad",
                   "short": "HAIL EVERY 7S: EVERY PLANT LOSES HALF ITS GROWTH."},
    "root_rot":   {"name": "Root Rot",      "desc": "Every 8s rot takes a random plant out of the ground.", "growth": 1.0,  "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "boss": True, "rot": 8, "tone": "bad",
                   "short": "ROT TAKES A PLANT EVERY 8S."},
    "heatwave":   {"name": "Heatwave",      "desc": "Water evaporates twice as fast and plants grow 15% slower.", "growth": 0.85, "yield": 1.0, "time": 0,   "ban": None,     "blight": False, "boss": True, "dry": 2.0, "tone": "bad",
                   "short": "GROWTH -15%, WATER DRIES 2X FASTER."},
    "eternal_night": {"name": "Eternal Night", "desc": "The sun never comes up: nocturnal plants grow up top, sun-lovers sulk.", "growth": 1.0, "yield": 1.0, "time": 0, "ban": None, "blight": False, "boss": True, "eclipse": True, "tone": "bad",
                      "short": "NOCTURNAL SEEDS UP TOP, SUN-LOVERS SULK."},
    "gale":       {"name": "Gale",          "desc": "The wind strips 10s off the round and slows every plant 20%.", "growth": 0.8,  "yield": 1.0, "time": -10, "ban": None,     "blight": False, "boss": True, "tone": "bad",
                   "short": "ROUND -10S, GROWTH -20%."},
}
RANDOM_TWISTS = ["drought", "locusts", "short", "frost", "blight", "sunny", "rain", "market", "eclipse"]
MINOR_TWISTS = ["sunny", "rain", "market", "eclipse", "still"]     
BOSS_TWISTS = ["crow_swarm", "hailstorm", "root_rot", "heatwave", "eternal_night", "gale"]

SEASONS = [
    {"name": "Spring", "short": "SPR", "color": (130, 210, 120),
     "desc": "THE GARDEN WAKES UP."},
    {"name": "Summer", "short": "SUM", "color": (250, 210, 70),
     "desc": "LONG DAYS, THIRSTY SOIL."},
    {"name": "Autumn", "short": "AUT", "color": (240, 140, 50),
     "desc": "THE LAST BIG HARVEST."},
    {"name": "Winter", "short": "WIN", "color": (150, 190, 250),
     "desc": "SHORT DAYS, COLD GROUND."},
]

PERKS = {
     "cash":  {"name": "Deep Pockets", "max": 10, "costs": [3, 4, 5, 6, 7, 8, 10, 12, 14, 16],
              "desc": "START WITH +$10 A LEVEL", "now": "+${n}"},
    "plots": {"name": "Spare Plot",   "max": 4,  "costs": [8, 12, 18, 26],
              "desc": "ONE MORE STARTING PLOT PER LEVEL", "now": "+{n} PLOT{s}"},
    "packs": {"name": "Seed Stash",   "max": 2,  "costs": [10, 18],
              "desc": "ONE MORE FREE PACK A ROUND PER LEVEL", "now": "+{n} PACK{s}"},
    "yield": {"name": "Green Thumbs", "max": 10, "costs": [5, 6, 8, 10, 12, 14, 16, 18, 20, 24],
              "desc": "+10% TO EVERY HARVEST PER LEVEL", "now": "+{n}%"},
}
PERK_ORDER = ["cash", "plots", "packs", "yield"]
PERK_STEP = {"cash": 10, "plots": 1, "packs": 1, "yield": 10}
PERK_COST_GROWTH = 1.15     


def perk_cost(key, level):
    """Heirloom price of going from `level` to `level + 1` (0 when maxed)."""
    perk = PERKS[key]
    if level >= perk["max"]:
        return 0
    return int(round(perk["costs"][level] * PERK_COST_GROWTH ** level))


def perk_text(key, level):
    """'+$20' / '+2 PLOTS' / '+30%' - the total a level gives you."""
    n = PERK_STEP[key] * level
    return PERKS[key]["now"].format(n=n, s="" if n == 1 else "S")

def bill_for_quota(k):
    """Bill amount for the k-th quota (k = 1, 2, 3 ...). Climbs forever."""
    if k <= 8:
        return int(round(300 * 5.0 ** (k - 1)))
    return int(round(300 * 5.0 ** 7 * 6.0 ** (k - 8)))

try:
    from .settings import SEASON_LENGTH
except ImportError:                       
    from settings import SEASON_LENGTH


def season_index(rnd):
    """0-based index into SEASONS; wraps round forever."""
    return ((max(1, int(rnd)) - 1) // SEASON_LENGTH) % len(SEASONS)


def season_number(rnd):
    """'Season 2' - how many seasons this run has seen, 1-based."""
    return (max(1, int(rnd)) - 1) // SEASON_LENGTH + 1


def season(rnd):
    return SEASONS[season_index(rnd)]


def is_new_season(rnd):
    """True on the first round of a season (round 1 starts season 1)."""
    return (int(rnd) - 1) % SEASON_LENGTH == 0