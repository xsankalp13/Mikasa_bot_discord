"""
pokemon_data.py — Static Kanto Pokémon data for Mikasa Bot.
All 151 Pokémon, moves, type chart, learnsets, and battle helpers.
"""
import random

# ══════════════════════════════════════════════════════════════
#  TYPE EFFECTIVENESS CHART  (attacking_type → defending_type → multiplier)
#  Only non-1.0 entries listed. Missing = 1.0x
# ══════════════════════════════════════════════════════════════
TYPE_CHART = {
    "normal":   {"rock": 0.5, "ghost": 0.0},
    "fire":     {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0, "bug": 2.0, "rock": 0.5, "dragon": 0.5},
    "water":    {"fire": 2.0, "water": 0.5, "grass": 0.5, "ground": 2.0, "rock": 2.0, "dragon": 0.5},
    "electric": {"water": 2.0, "electric": 0.5, "grass": 0.5, "ground": 0.0, "flying": 2.0, "dragon": 0.5},
    "grass":    {"fire": 0.5, "water": 2.0, "grass": 0.5, "poison": 0.5, "ground": 2.0, "flying": 0.5, "bug": 0.5, "rock": 2.0, "dragon": 0.5},
    "ice":      {"fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 0.5, "ground": 2.0, "flying": 2.0, "dragon": 2.0},
    "fighting": {"normal": 2.0, "ice": 2.0, "poison": 0.5, "flying": 0.5, "psychic": 0.5, "bug": 0.5, "rock": 2.0, "ghost": 0.0},
    "poison":   {"grass": 2.0, "poison": 0.5, "ground": 0.5, "rock": 0.5, "ghost": 0.5},
    "ground":   {"fire": 2.0, "electric": 2.0, "grass": 0.5, "poison": 2.0, "flying": 0.0, "bug": 0.5, "rock": 2.0},
    "flying":   {"electric": 0.5, "grass": 2.0, "fighting": 2.0, "bug": 2.0, "rock": 0.5},
    "psychic":  {"fighting": 2.0, "poison": 2.0, "psychic": 0.5},
    "bug":      {"fire": 0.5, "grass": 2.0, "fighting": 0.5, "poison": 0.5, "flying": 0.5, "psychic": 2.0, "ghost": 0.5},
    "rock":     {"fire": 2.0, "ice": 2.0, "fighting": 0.5, "ground": 0.5, "flying": 2.0, "bug": 2.0},
    "ghost":    {"normal": 0.0, "psychic": 2.0, "ghost": 2.0},
    "dragon":   {"dragon": 2.0},
}

# ══════════════════════════════════════════════════════════════
#  MOVES  —  key → {name, type, power, accuracy}
# ══════════════════════════════════════════════════════════════
MOVES = {
    # Normal
    "tackle":       {"name": "Tackle",       "type": "normal",   "power": 40,  "acc": 100},
    "scratch":      {"name": "Scratch",      "type": "normal",   "power": 40,  "acc": 100},
    "pound":        {"name": "Pound",        "type": "normal",   "power": 40,  "acc": 100},
    "quick_attack": {"name": "Quick Attack", "type": "normal",   "power": 40,  "acc": 100},
    "slam":         {"name": "Slam",         "type": "normal",   "power": 80,  "acc": 100},
    "body_slam":    {"name": "Body Slam",    "type": "normal",   "power": 85,  "acc": 100},
    "hyper_beam":   {"name": "Hyper Beam",   "type": "normal",   "power": 150, "acc": 100},
    "bite":         {"name": "Bite",         "type": "normal",   "power": 60,  "acc": 100},
    # Fire
    "ember":        {"name": "Ember",        "type": "fire",     "power": 40,  "acc": 100},
    "fire_punch":   {"name": "Fire Punch",   "type": "fire",     "power": 75,  "acc": 100},
    "flamethrower": {"name": "Flamethrower", "type": "fire",     "power": 90,  "acc": 100},
    "fire_blast":   {"name": "Fire Blast",   "type": "fire",     "power": 110, "acc": 100},
    # Water
    "bubble":       {"name": "Bubble",       "type": "water",    "power": 40,  "acc": 100},
    "water_gun":    {"name": "Water Gun",    "type": "water",    "power": 40,  "acc": 100},
    "surf":         {"name": "Surf",         "type": "water",    "power": 90,  "acc": 100},
    "hydro_pump":   {"name": "Hydro Pump",   "type": "water",    "power": 110, "acc": 100},
    # Grass
    "vine_whip":    {"name": "Vine Whip",    "type": "grass",    "power": 45,  "acc": 100},
    "razor_leaf":   {"name": "Razor Leaf",   "type": "grass",    "power": 55,  "acc": 100},
    "mega_drain":   {"name": "Mega Drain",   "type": "grass",    "power": 40,  "acc": 100},
    "solar_beam":   {"name": "Solar Beam",   "type": "grass",    "power": 120, "acc": 100},
    # Electric
    "thunder_shock":{"name": "Thunder Shock","type": "electric",  "power": 40,  "acc": 100},
    "spark":        {"name": "Spark",        "type": "electric",  "power": 65,  "acc": 100},
    "thunderbolt":  {"name": "Thunderbolt",  "type": "electric",  "power": 90,  "acc": 100},
    "thunder":      {"name": "Thunder",      "type": "electric",  "power": 110, "acc": 100},
    # Ice
    "ice_shard":    {"name": "Ice Shard",    "type": "ice",      "power": 40,  "acc": 100},
    "ice_punch":    {"name": "Ice Punch",    "type": "ice",      "power": 75,  "acc": 100},
    "ice_beam":     {"name": "Ice Beam",     "type": "ice",      "power": 90,  "acc": 100},
    "blizzard":     {"name": "Blizzard",     "type": "ice",      "power": 110, "acc": 100},
    # Fighting
    "karate_chop":  {"name": "Karate Chop",  "type": "fighting",  "power": 50,  "acc": 100},
    "low_kick":     {"name": "Low Kick",     "type": "fighting",  "power": 50,  "acc": 100},
    "brick_break":  {"name": "Brick Break",  "type": "fighting",  "power": 75,  "acc": 100},
    "submission":   {"name": "Submission",   "type": "fighting",  "power": 80,  "acc": 100},
    # Poison
    "poison_sting": {"name": "Poison Sting", "type": "poison",    "power": 15,  "acc": 100},
    "acid":         {"name": "Acid",         "type": "poison",    "power": 40,  "acc": 100},
    "sludge_bomb":  {"name": "Sludge Bomb",  "type": "poison",    "power": 90,  "acc": 100},
    # Ground
    "mud_slap":     {"name": "Mud-Slap",     "type": "ground",    "power": 20,  "acc": 100},
    "dig":          {"name": "Dig",          "type": "ground",    "power": 80,  "acc": 100},
    "earthquake":   {"name": "Earthquake",   "type": "ground",    "power": 100, "acc": 100},
    # Flying
    "gust":         {"name": "Gust",         "type": "flying",    "power": 40,  "acc": 100},
    "wing_attack":  {"name": "Wing Attack",  "type": "flying",    "power": 60,  "acc": 100},
    "aerial_ace":   {"name": "Aerial Ace",   "type": "flying",    "power": 60,  "acc": 100},
    "fly":          {"name": "Fly",          "type": "flying",    "power": 90,  "acc": 100},
    "drill_peck":   {"name": "Drill Peck",   "type": "flying",    "power": 80,  "acc": 100},
    # Psychic
    "confusion":    {"name": "Confusion",    "type": "psychic",   "power": 50,  "acc": 100},
    "psybeam":      {"name": "Psybeam",      "type": "psychic",   "power": 65,  "acc": 100},
    "psychic_m":    {"name": "Psychic",      "type": "psychic",   "power": 90,  "acc": 100},
    # Bug
    "bug_bite":     {"name": "Bug Bite",     "type": "bug",       "power": 60,  "acc": 100},
    "leech_life":   {"name": "Leech Life",   "type": "bug",       "power": 80,  "acc": 100},
    # Rock
    "rock_throw":   {"name": "Rock Throw",   "type": "rock",      "power": 50,  "acc": 100},
    "rock_slide":   {"name": "Rock Slide",   "type": "rock",      "power": 75,  "acc": 100},
    # Ghost
    "lick":         {"name": "Lick",         "type": "ghost",     "power": 30,  "acc": 100},
    "shadow_ball":  {"name": "Shadow Ball",  "type": "ghost",     "power": 80,  "acc": 100},
    # Dragon
    "dragon_rage":  {"name": "Dragon Rage",  "type": "dragon",    "power": 40,  "acc": 100},
    "dragon_claw":  {"name": "Dragon Claw",  "type": "dragon",    "power": 80,  "acc": 100},
}

# ══════════════════════════════════════════════════════════════
#  TYPE → MOVE POOLS   (used to auto-generate learnsets)
# ══════════════════════════════════════════════════════════════
_TYPE_MOVES = {
    "normal":   [("tackle", 1), ("quick_attack", 12), ("slam", 24), ("body_slam", 36)],
    "fire":     [("ember", 1), ("fire_punch", 20), ("flamethrower", 32), ("fire_blast", 44)],
    "water":    [("bubble", 1), ("water_gun", 8), ("surf", 28), ("hydro_pump", 42)],
    "grass":    [("vine_whip", 1), ("razor_leaf", 16), ("mega_drain", 26), ("solar_beam", 42)],
    "electric": [("thunder_shock", 1), ("spark", 16), ("thunderbolt", 30), ("thunder", 44)],
    "ice":      [("ice_shard", 1), ("ice_punch", 20), ("ice_beam", 32), ("blizzard", 44)],
    "fighting": [("karate_chop", 1), ("low_kick", 12), ("brick_break", 24), ("submission", 36)],
    "poison":   [("poison_sting", 1), ("acid", 14), ("sludge_bomb", 32)],
    "ground":   [("mud_slap", 1), ("dig", 22), ("earthquake", 38)],
    "flying":   [("gust", 1), ("wing_attack", 16), ("aerial_ace", 28), ("fly", 40)],
    "psychic":  [("confusion", 1), ("psybeam", 18), ("psychic_m", 34)],
    "bug":      [("bug_bite", 1), ("leech_life", 24)],
    "rock":     [("rock_throw", 1), ("rock_slide", 26)],
    "ghost":    [("lick", 1), ("shadow_ball", 28)],
    "dragon":   [("dragon_rage", 1), ("dragon_claw", 32)],
}

# ══════════════════════════════════════════════════════════════
#  KANTO POKÉMON   id → dict
#  Stats from the official games (simplified: hp, atk, def, spd)
#  evo = (target_id, level) or None
# ══════════════════════════════════════════════════════════════
KANTO_POKEMON = {
    1:   {"name": "Bulbasaur",  "types": ["grass","poison"], "hp": 45, "atk": 49, "def": 49, "spd": 45, "evo": (2, 16)},
    2:   {"name": "Ivysaur",    "types": ["grass","poison"], "hp": 60, "atk": 62, "def": 63, "spd": 60, "evo": (3, 32)},
    3:   {"name": "Venusaur",   "types": ["grass","poison"], "hp": 80, "atk": 82, "def": 83, "spd": 80, "evo": None},
    4:   {"name": "Charmander", "types": ["fire"],           "hp": 39, "atk": 52, "def": 43, "spd": 65, "evo": (5, 16)},
    5:   {"name": "Charmeleon", "types": ["fire"],           "hp": 58, "atk": 64, "def": 58, "spd": 80, "evo": (6, 36)},
    6:   {"name": "Charizard",  "types": ["fire","flying"],  "hp": 78, "atk": 84, "def": 78, "spd": 100,"evo": None},
    7:   {"name": "Squirtle",   "types": ["water"],          "hp": 44, "atk": 48, "def": 65, "spd": 43, "evo": (8, 16)},
    8:   {"name": "Wartortle",  "types": ["water"],          "hp": 59, "atk": 63, "def": 80, "spd": 58, "evo": (9, 36)},
    9:   {"name": "Blastoise",  "types": ["water"],          "hp": 79, "atk": 83, "def": 100,"spd": 78, "evo": None},
    10:  {"name": "Caterpie",   "types": ["bug"],            "hp": 45, "atk": 30, "def": 35, "spd": 45, "evo": (11, 7)},
    11:  {"name": "Metapod",    "types": ["bug"],            "hp": 50, "atk": 20, "def": 55, "spd": 30, "evo": (12, 10)},
    12:  {"name": "Butterfree", "types": ["bug","flying"],   "hp": 60, "atk": 45, "def": 50, "spd": 70, "evo": None},
    13:  {"name": "Weedle",     "types": ["bug","poison"],   "hp": 40, "atk": 35, "def": 30, "spd": 50, "evo": (14, 7)},
    14:  {"name": "Kakuna",     "types": ["bug","poison"],   "hp": 45, "atk": 25, "def": 50, "spd": 35, "evo": (15, 10)},
    15:  {"name": "Beedrill",   "types": ["bug","poison"],   "hp": 65, "atk": 90, "def": 40, "spd": 75, "evo": None},
    16:  {"name": "Pidgey",     "types": ["normal","flying"],"hp": 40, "atk": 45, "def": 40, "spd": 56, "evo": (17, 18)},
    17:  {"name": "Pidgeotto",  "types": ["normal","flying"],"hp": 63, "atk": 60, "def": 55, "spd": 71, "evo": (18, 36)},
    18:  {"name": "Pidgeot",    "types": ["normal","flying"],"hp": 83, "atk": 80, "def": 75, "spd": 101,"evo": None},
    19:  {"name": "Rattata",    "types": ["normal"],         "hp": 30, "atk": 56, "def": 35, "spd": 72, "evo": (20, 20)},
    20:  {"name": "Raticate",   "types": ["normal"],         "hp": 55, "atk": 81, "def": 60, "spd": 97, "evo": None},
    21:  {"name": "Spearow",    "types": ["normal","flying"],"hp": 40, "atk": 60, "def": 30, "spd": 70, "evo": (22, 20)},
    22:  {"name": "Fearow",     "types": ["normal","flying"],"hp": 65, "atk": 90, "def": 65, "spd": 100,"evo": None},
    23:  {"name": "Ekans",      "types": ["poison"],         "hp": 35, "atk": 60, "def": 44, "spd": 55, "evo": (24, 22)},
    24:  {"name": "Arbok",      "types": ["poison"],         "hp": 60, "atk": 85, "def": 69, "spd": 80, "evo": None},
    25:  {"name": "Pikachu",    "types": ["electric"],       "hp": 35, "atk": 55, "def": 40, "spd": 90, "evo": None},
    26:  {"name": "Raichu",     "types": ["electric"],       "hp": 60, "atk": 90, "def": 55, "spd": 110,"evo": None},
    27:  {"name": "Sandshrew",  "types": ["ground"],         "hp": 50, "atk": 75, "def": 85, "spd": 40, "evo": (28, 22)},
    28:  {"name": "Sandslash",  "types": ["ground"],         "hp": 75, "atk": 100,"def": 110,"spd": 65, "evo": None},
    29:  {"name": "Nidoran♀",   "types": ["poison"],         "hp": 55, "atk": 47, "def": 52, "spd": 41, "evo": (30, 16)},
    30:  {"name": "Nidorina",   "types": ["poison"],         "hp": 70, "atk": 62, "def": 67, "spd": 56, "evo": None},
    31:  {"name": "Nidoqueen",  "types": ["poison","ground"],"hp": 90, "atk": 92, "def": 87, "spd": 76, "evo": None},
    32:  {"name": "Nidoran♂",   "types": ["poison"],         "hp": 46, "atk": 57, "def": 40, "spd": 50, "evo": (33, 16)},
    33:  {"name": "Nidorino",   "types": ["poison"],         "hp": 61, "atk": 72, "def": 57, "spd": 65, "evo": None},
    34:  {"name": "Nidoking",   "types": ["poison","ground"],"hp": 81, "atk": 102,"def": 77, "spd": 85, "evo": None},
    35:  {"name": "Clefairy",   "types": ["normal"],         "hp": 70, "atk": 45, "def": 48, "spd": 35, "evo": None},
    36:  {"name": "Clefable",   "types": ["normal"],         "hp": 95, "atk": 70, "def": 73, "spd": 60, "evo": None},
    37:  {"name": "Vulpix",     "types": ["fire"],           "hp": 38, "atk": 41, "def": 40, "spd": 65, "evo": None},
    38:  {"name": "Ninetales",  "types": ["fire"],           "hp": 73, "atk": 76, "def": 75, "spd": 100,"evo": None},
    39:  {"name": "Jigglypuff", "types": ["normal"],         "hp": 115,"atk": 45, "def": 20, "spd": 20, "evo": None},
    40:  {"name": "Wigglytuff", "types": ["normal"],         "hp": 140,"atk": 70, "def": 45, "spd": 45, "evo": None},
    41:  {"name": "Zubat",      "types": ["poison","flying"],"hp": 40, "atk": 45, "def": 35, "spd": 55, "evo": (42, 22)},
    42:  {"name": "Golbat",     "types": ["poison","flying"],"hp": 75, "atk": 80, "def": 70, "spd": 90, "evo": None},
    43:  {"name": "Oddish",     "types": ["grass","poison"], "hp": 45, "atk": 50, "def": 55, "spd": 30, "evo": (44, 21)},
    44:  {"name": "Gloom",      "types": ["grass","poison"], "hp": 60, "atk": 65, "def": 70, "spd": 40, "evo": (45, 36)},
    45:  {"name": "Vileplume",  "types": ["grass","poison"], "hp": 75, "atk": 80, "def": 85, "spd": 50, "evo": None},
    46:  {"name": "Paras",      "types": ["bug","grass"],    "hp": 35, "atk": 70, "def": 55, "spd": 25, "evo": (47, 24)},
    47:  {"name": "Parasect",   "types": ["bug","grass"],    "hp": 60, "atk": 95, "def": 80, "spd": 30, "evo": None},
    48:  {"name": "Venonat",    "types": ["bug","poison"],   "hp": 60, "atk": 55, "def": 50, "spd": 45, "evo": (49, 31)},
    49:  {"name": "Venomoth",   "types": ["bug","poison"],   "hp": 70, "atk": 65, "def": 60, "spd": 90, "evo": None},
    50:  {"name": "Diglett",    "types": ["ground"],         "hp": 10, "atk": 55, "def": 25, "spd": 95, "evo": (51, 26)},
    51:  {"name": "Dugtrio",    "types": ["ground"],         "hp": 35, "atk": 100,"def": 50, "spd": 120,"evo": None},
    52:  {"name": "Meowth",     "types": ["normal"],         "hp": 40, "atk": 45, "def": 35, "spd": 90, "evo": (53, 28)},
    53:  {"name": "Persian",    "types": ["normal"],         "hp": 65, "atk": 70, "def": 60, "spd": 115,"evo": None},
    54:  {"name": "Psyduck",    "types": ["water"],          "hp": 50, "atk": 52, "def": 48, "spd": 55, "evo": (55, 33)},
    55:  {"name": "Golduck",    "types": ["water"],          "hp": 80, "atk": 82, "def": 78, "spd": 85, "evo": None},
    56:  {"name": "Mankey",     "types": ["fighting"],       "hp": 40, "atk": 80, "def": 35, "spd": 70, "evo": (57, 28)},
    57:  {"name": "Primeape",   "types": ["fighting"],       "hp": 65, "atk": 105,"def": 60, "spd": 95, "evo": None},
    58:  {"name": "Growlithe",  "types": ["fire"],           "hp": 55, "atk": 70, "def": 45, "spd": 60, "evo": None},
    59:  {"name": "Arcanine",   "types": ["fire"],           "hp": 90, "atk": 110,"def": 80, "spd": 95, "evo": None},
    60:  {"name": "Poliwag",    "types": ["water"],          "hp": 40, "atk": 50, "def": 40, "spd": 90, "evo": (61, 25)},
    61:  {"name": "Poliwhirl",  "types": ["water"],          "hp": 65, "atk": 65, "def": 65, "spd": 90, "evo": None},
    62:  {"name": "Poliwrath",  "types": ["water","fighting"],"hp": 90,"atk": 95, "def": 95, "spd": 70, "evo": None},
    63:  {"name": "Abra",       "types": ["psychic"],        "hp": 25, "atk": 20, "def": 15, "spd": 90, "evo": (64, 16)},
    64:  {"name": "Kadabra",    "types": ["psychic"],        "hp": 40, "atk": 35, "def": 30, "spd": 105,"evo": None},
    65:  {"name": "Alakazam",   "types": ["psychic"],        "hp": 55, "atk": 50, "def": 45, "spd": 120,"evo": None},
    66:  {"name": "Machop",     "types": ["fighting"],       "hp": 70, "atk": 80, "def": 50, "spd": 35, "evo": (67, 28)},
    67:  {"name": "Machoke",    "types": ["fighting"],       "hp": 80, "atk": 100,"def": 70, "spd": 45, "evo": None},
    68:  {"name": "Machamp",    "types": ["fighting"],       "hp": 90, "atk": 130,"def": 80, "spd": 55, "evo": None},
    69:  {"name": "Bellsprout", "types": ["grass","poison"], "hp": 50, "atk": 75, "def": 35, "spd": 40, "evo": (70, 21)},
    70:  {"name": "Weepinbell", "types": ["grass","poison"], "hp": 65, "atk": 90, "def": 50, "spd": 55, "evo": None},
    71:  {"name": "Victreebel", "types": ["grass","poison"], "hp": 80, "atk": 105,"def": 65, "spd": 70, "evo": None},
    72:  {"name": "Tentacool",  "types": ["water","poison"], "hp": 40, "atk": 40, "def": 35, "spd": 70, "evo": (73, 30)},
    73:  {"name": "Tentacruel", "types": ["water","poison"], "hp": 80, "atk": 70, "def": 65, "spd": 100,"evo": None},
    74:  {"name": "Geodude",    "types": ["rock","ground"],  "hp": 40, "atk": 80, "def": 100,"spd": 20, "evo": (75, 25)},
    75:  {"name": "Graveler",   "types": ["rock","ground"],  "hp": 55, "atk": 95, "def": 115,"spd": 35, "evo": None},
    76:  {"name": "Golem",      "types": ["rock","ground"],  "hp": 80, "atk": 120,"def": 130,"spd": 45, "evo": None},
    77:  {"name": "Ponyta",     "types": ["fire"],           "hp": 50, "atk": 85, "def": 55, "spd": 90, "evo": (78, 40)},
    78:  {"name": "Rapidash",   "types": ["fire"],           "hp": 65, "atk": 100,"def": 70, "spd": 105,"evo": None},
    79:  {"name": "Slowpoke",   "types": ["water","psychic"],"hp": 90, "atk": 65, "def": 65, "spd": 15, "evo": (80, 37)},
    80:  {"name": "Slowbro",    "types": ["water","psychic"],"hp": 95, "atk": 75, "def": 110,"spd": 30, "evo": None},
    81:  {"name": "Magnemite",  "types": ["electric"],       "hp": 25, "atk": 35, "def": 70, "spd": 45, "evo": (82, 30)},
    82:  {"name": "Magneton",   "types": ["electric"],       "hp": 50, "atk": 60, "def": 95, "spd": 70, "evo": None},
    83:  {"name": "Farfetch'd", "types": ["normal","flying"],"hp": 52, "atk": 90, "def": 55, "spd": 60, "evo": None},
    84:  {"name": "Doduo",      "types": ["normal","flying"],"hp": 35, "atk": 85, "def": 45, "spd": 75, "evo": (85, 31)},
    85:  {"name": "Dodrio",     "types": ["normal","flying"],"hp": 60, "atk": 110,"def": 70, "spd": 110,"evo": None},
    86:  {"name": "Seel",       "types": ["water"],          "hp": 65, "atk": 45, "def": 55, "spd": 45, "evo": (87, 34)},
    87:  {"name": "Dewgong",    "types": ["water","ice"],    "hp": 90, "atk": 70, "def": 80, "spd": 70, "evo": None},
    88:  {"name": "Grimer",     "types": ["poison"],         "hp": 80, "atk": 80, "def": 50, "spd": 25, "evo": (89, 38)},
    89:  {"name": "Muk",        "types": ["poison"],         "hp": 105,"atk": 105,"def": 75, "spd": 50, "evo": None},
    90:  {"name": "Shellder",   "types": ["water"],          "hp": 30, "atk": 65, "def": 100,"spd": 40, "evo": None},
    91:  {"name": "Cloyster",   "types": ["water","ice"],    "hp": 50, "atk": 95, "def": 180,"spd": 70, "evo": None},
    92:  {"name": "Gastly",     "types": ["ghost","poison"], "hp": 30, "atk": 35, "def": 30, "spd": 80, "evo": (93, 25)},
    93:  {"name": "Haunter",    "types": ["ghost","poison"], "hp": 45, "atk": 50, "def": 45, "spd": 95, "evo": None},
    94:  {"name": "Gengar",     "types": ["ghost","poison"], "hp": 60, "atk": 65, "def": 60, "spd": 110,"evo": None},
    95:  {"name": "Onix",       "types": ["rock","ground"],  "hp": 35, "atk": 45, "def": 160,"spd": 70, "evo": None},
    96:  {"name": "Drowzee",    "types": ["psychic"],        "hp": 60, "atk": 48, "def": 45, "spd": 42, "evo": (97, 26)},
    97:  {"name": "Hypno",      "types": ["psychic"],        "hp": 85, "atk": 73, "def": 67, "spd": 67, "evo": None},
    98:  {"name": "Krabby",     "types": ["water"],          "hp": 30, "atk": 105,"def": 90, "spd": 50, "evo": (99, 28)},
    99:  {"name": "Kingler",    "types": ["water"],          "hp": 55, "atk": 130,"def": 115,"spd": 75, "evo": None},
    100: {"name": "Voltorb",    "types": ["electric"],       "hp": 40, "atk": 30, "def": 50, "spd": 100,"evo": (101,30)},
    101: {"name": "Electrode",  "types": ["electric"],       "hp": 60, "atk": 50, "def": 70, "spd": 150,"evo": None},
    102: {"name": "Exeggcute",  "types": ["grass","psychic"],"hp": 60, "atk": 40, "def": 80, "spd": 40, "evo": None},
    103: {"name": "Exeggutor",  "types": ["grass","psychic"],"hp": 95, "atk": 95, "def": 85, "spd": 55, "evo": None},
    104: {"name": "Cubone",     "types": ["ground"],         "hp": 50, "atk": 50, "def": 95, "spd": 35, "evo": (105,28)},
    105: {"name": "Marowak",    "types": ["ground"],         "hp": 60, "atk": 80, "def": 110,"spd": 45, "evo": None},
    106: {"name": "Hitmonlee",  "types": ["fighting"],       "hp": 50, "atk": 120,"def": 53, "spd": 87, "evo": None},
    107: {"name": "Hitmonchan", "types": ["fighting"],       "hp": 50, "atk": 105,"def": 79, "spd": 76, "evo": None},
    108: {"name": "Lickitung",  "types": ["normal"],         "hp": 90, "atk": 55, "def": 75, "spd": 30, "evo": None},
    109: {"name": "Koffing",    "types": ["poison"],         "hp": 40, "atk": 65, "def": 95, "spd": 35, "evo": (110,35)},
    110: {"name": "Weezing",    "types": ["poison"],         "hp": 65, "atk": 90, "def": 120,"spd": 60, "evo": None},
    111: {"name": "Rhyhorn",    "types": ["ground","rock"],  "hp": 80, "atk": 85, "def": 95, "spd": 25, "evo": (112,42)},
    112: {"name": "Rhydon",     "types": ["ground","rock"],  "hp": 105,"atk": 130,"def": 120,"spd": 40, "evo": None},
    113: {"name": "Chansey",    "types": ["normal"],         "hp": 250,"atk": 5,  "def": 5,  "spd": 50, "evo": None},
    114: {"name": "Tangela",    "types": ["grass"],          "hp": 65, "atk": 55, "def": 115,"spd": 60, "evo": None},
    115: {"name": "Kangaskhan", "types": ["normal"],         "hp": 105,"atk": 95, "def": 80, "spd": 90, "evo": None},
    116: {"name": "Horsea",     "types": ["water"],          "hp": 30, "atk": 40, "def": 70, "spd": 60, "evo": (117,32)},
    117: {"name": "Seadra",     "types": ["water"],          "hp": 55, "atk": 65, "def": 95, "spd": 85, "evo": None},
    118: {"name": "Goldeen",    "types": ["water"],          "hp": 45, "atk": 67, "def": 60, "spd": 63, "evo": (119,33)},
    119: {"name": "Seaking",    "types": ["water"],          "hp": 80, "atk": 92, "def": 65, "spd": 68, "evo": None},
    120: {"name": "Staryu",     "types": ["water"],          "hp": 30, "atk": 45, "def": 55, "spd": 85, "evo": None},
    121: {"name": "Starmie",    "types": ["water","psychic"],"hp": 60, "atk": 75, "def": 85, "spd": 115,"evo": None},
    122: {"name": "Mr. Mime",   "types": ["psychic"],        "hp": 40, "atk": 45, "def": 65, "spd": 90, "evo": None},
    123: {"name": "Scyther",    "types": ["bug","flying"],   "hp": 70, "atk": 110,"def": 80, "spd": 105,"evo": None},
    124: {"name": "Jynx",       "types": ["ice","psychic"],  "hp": 65, "atk": 50, "def": 35, "spd": 95, "evo": None},
    125: {"name": "Electabuzz", "types": ["electric"],       "hp": 65, "atk": 83, "def": 57, "spd": 105,"evo": None},
    126: {"name": "Magmar",     "types": ["fire"],           "hp": 65, "atk": 95, "def": 57, "spd": 93, "evo": None},
    127: {"name": "Pinsir",     "types": ["bug"],            "hp": 65, "atk": 125,"def": 100,"spd": 85, "evo": None},
    128: {"name": "Tauros",     "types": ["normal"],         "hp": 75, "atk": 100,"def": 95, "spd": 110,"evo": None},
    129: {"name": "Magikarp",   "types": ["water"],          "hp": 20, "atk": 10, "def": 55, "spd": 80, "evo": (130,20)},
    130: {"name": "Gyarados",   "types": ["water","flying"], "hp": 95, "atk": 125,"def": 79, "spd": 81, "evo": None},
    131: {"name": "Lapras",     "types": ["water","ice"],    "hp": 130,"atk": 85, "def": 80, "spd": 60, "evo": None},
    132: {"name": "Ditto",      "types": ["normal"],         "hp": 48, "atk": 48, "def": 48, "spd": 48, "evo": None},
    133: {"name": "Eevee",      "types": ["normal"],         "hp": 55, "atk": 55, "def": 50, "spd": 55, "evo": None},
    134: {"name": "Vaporeon",   "types": ["water"],          "hp": 130,"atk": 65, "def": 60, "spd": 65, "evo": None},
    135: {"name": "Jolteon",    "types": ["electric"],       "hp": 65, "atk": 65, "def": 60, "spd": 130,"evo": None},
    136: {"name": "Flareon",    "types": ["fire"],           "hp": 65, "atk": 130,"def": 60, "spd": 65, "evo": None},
    137: {"name": "Porygon",    "types": ["normal"],         "hp": 65, "atk": 60, "def": 70, "spd": 40, "evo": None},
    138: {"name": "Omanyte",    "types": ["rock","water"],   "hp": 35, "atk": 40, "def": 100,"spd": 35, "evo": (139,40)},
    139: {"name": "Omastar",    "types": ["rock","water"],   "hp": 70, "atk": 60, "def": 125,"spd": 55, "evo": None},
    140: {"name": "Kabuto",     "types": ["rock","water"],   "hp": 30, "atk": 80, "def": 90, "spd": 55, "evo": (141,40)},
    141: {"name": "Kabutops",   "types": ["rock","water"],   "hp": 60, "atk": 115,"def": 105,"spd": 80, "evo": None},
    142: {"name": "Aerodactyl", "types": ["rock","flying"],  "hp": 80, "atk": 105,"def": 65, "spd": 130,"evo": None},
    143: {"name": "Snorlax",    "types": ["normal"],         "hp": 160,"atk": 110,"def": 65, "spd": 30, "evo": None},
    144: {"name": "Articuno",   "types": ["ice","flying"],   "hp": 90, "atk": 85, "def": 100,"spd": 85, "evo": None},
    145: {"name": "Zapdos",     "types": ["electric","flying"],"hp":90,"atk": 90, "def": 85, "spd": 100,"evo": None},
    146: {"name": "Moltres",    "types": ["fire","flying"],  "hp": 90, "atk": 100,"def": 90, "spd": 90, "evo": None},
    147: {"name": "Dratini",    "types": ["dragon"],         "hp": 41, "atk": 64, "def": 45, "spd": 50, "evo": (148,30)},
    148: {"name": "Dragonair",  "types": ["dragon"],         "hp": 61, "atk": 84, "def": 65, "spd": 70, "evo": (149,55)},
    149: {"name": "Dragonite",  "types": ["dragon","flying"],"hp": 91, "atk": 134,"def": 95, "spd": 80, "evo": None},
    150: {"name": "Mewtwo",     "types": ["psychic"],        "hp": 106,"atk": 110,"def": 90, "spd": 130,"evo": None},
    151: {"name": "Mew",        "types": ["psychic"],        "hp": 100,"atk": 100,"def": 100,"spd": 100,"evo": None},
}

# ══════════════════════════════════════════════════════════════
#  CUSTOM LEARNSETS  (pokemon_id → [(level, move_key), ...])
#  Only notable Pokémon listed here. Others auto-generated.
# ══════════════════════════════════════════════════════════════
_CUSTOM_LEARNSETS = {
    # Starters
    1:  [(1,"tackle"),(1,"vine_whip"),(7,"poison_sting"),(13,"razor_leaf"),(20,"acid"),(27,"mega_drain"),(34,"sludge_bomb"),(42,"solar_beam")],
    2:  [(1,"tackle"),(1,"vine_whip"),(7,"poison_sting"),(13,"razor_leaf"),(20,"acid"),(27,"mega_drain"),(34,"sludge_bomb"),(42,"solar_beam")],
    3:  [(1,"tackle"),(1,"vine_whip"),(7,"poison_sting"),(13,"razor_leaf"),(20,"acid"),(27,"mega_drain"),(34,"sludge_bomb"),(42,"solar_beam")],
    4:  [(1,"scratch"),(1,"ember"),(10,"bite"),(16,"fire_punch"),(24,"slam"),(32,"flamethrower"),(36,"wing_attack"),(44,"fire_blast")],
    5:  [(1,"scratch"),(1,"ember"),(10,"bite"),(16,"fire_punch"),(24,"slam"),(32,"flamethrower"),(36,"wing_attack"),(44,"fire_blast")],
    6:  [(1,"scratch"),(1,"ember"),(10,"bite"),(16,"fire_punch"),(24,"slam"),(32,"flamethrower"),(36,"fly"),(44,"fire_blast")],
    7:  [(1,"tackle"),(1,"bubble"),(8,"water_gun"),(15,"bite"),(22,"ice_shard"),(28,"surf"),(36,"ice_beam"),(42,"hydro_pump")],
    8:  [(1,"tackle"),(1,"bubble"),(8,"water_gun"),(15,"bite"),(22,"ice_shard"),(28,"surf"),(36,"ice_beam"),(42,"hydro_pump")],
    9:  [(1,"tackle"),(1,"bubble"),(8,"water_gun"),(15,"bite"),(22,"ice_shard"),(28,"surf"),(36,"ice_beam"),(42,"hydro_pump")],
    # Pikachu line
    25: [(1,"tackle"),(1,"thunder_shock"),(8,"quick_attack"),(16,"spark"),(26,"slam"),(30,"thunderbolt"),(42,"thunder")],
    26: [(1,"tackle"),(1,"thunder_shock"),(8,"quick_attack"),(16,"spark"),(26,"slam"),(30,"thunderbolt"),(42,"thunder")],
    # Magikarp / Gyarados
    129:[(1,"tackle"),(15,"slam")],
    130:[(1,"bite"),(1,"water_gun"),(20,"surf"),(28,"dragon_rage"),(36,"hydro_pump"),(44,"hyper_beam")],
    # Legendaries
    144:[(1,"ice_shard"),(1,"gust"),(15,"ice_beam"),(30,"aerial_ace"),(45,"blizzard"),(50,"hyper_beam")],
    145:[(1,"thunder_shock"),(1,"gust"),(15,"thunderbolt"),(30,"drill_peck"),(45,"thunder"),(50,"hyper_beam")],
    146:[(1,"ember"),(1,"gust"),(15,"flamethrower"),(30,"fly"),(45,"fire_blast"),(50,"hyper_beam")],
    147:[(1,"tackle"),(1,"dragon_rage"),(12,"slam"),(20,"water_gun"),(30,"dragon_claw"),(40,"hyper_beam")],
    148:[(1,"tackle"),(1,"dragon_rage"),(12,"slam"),(20,"surf"),(30,"dragon_claw"),(40,"hyper_beam")],
    149:[(1,"slam"),(1,"dragon_rage"),(20,"wing_attack"),(30,"dragon_claw"),(40,"fly"),(50,"hyper_beam")],
    150:[(1,"confusion"),(1,"quick_attack"),(15,"psybeam"),(25,"psychic_m"),(35,"ice_beam"),(45,"hyper_beam")],
    151:[(1,"pound"),(1,"confusion"),(10,"mega_drain"),(20,"psychic_m"),(30,"flamethrower"),(40,"thunderbolt"),(50,"hyper_beam")],
}

# ══════════════════════════════════════════════════════════════
#  STARTER POOL  (pokemon_id, weight)  — higher weight = more common
# ══════════════════════════════════════════════════════════════
STARTER_POOL = [
    (1, 3), (4, 3), (7, 3),        # Classic starters (rare)
    (25, 2), (133, 2), (147, 1),   # Fan favorites  (very rare)
    (16, 8), (19, 8), (21, 6),     # Common birds & rats
    (10, 7), (13, 7), (41, 6),     # Bugs & bats
    (23, 5), (27, 5), (43, 5),     # Various commons
    (29, 5), (32, 5), (35, 4),     # Nidorans & Clefairy
    (37, 4), (46, 5), (50, 5),     # Misc commons
    (52, 5), (54, 4), (56, 4),     # Meowth, Psyduck, Mankey
    (58, 3), (60, 5), (63, 3),     # Growlithe, Poliwag, Abra
    (66, 4), (69, 5), (72, 5),     # Machop, Bellsprout, Tentacool
    (74, 5), (77, 4), (79, 4),     # Geodude, Ponyta, Slowpoke
    (81, 5), (92, 3), (104, 4),    # Magnemite, Gastly, Cubone
]

# Pokémon that should NEVER spawn in the wild (legendaries, trade evos etc.)
_NO_WILD_SPAWN = {144, 145, 146, 150, 151}


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def get_sprite_url(pokemon_id: int) -> str:
    """Official artwork URL from PokeAPI sprites repo."""
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pokemon_id}.png"


def calc_hp(base_hp: int, level: int) -> int:
    """Calculate max HP based on base HP and level (simplified formula)."""
    return int((2 * base_hp * level / 100) + level + 10)


def calc_stat(base: int, level: int) -> int:
    """Calculate a stat (atk/def/spd) based on base and level."""
    return int((2 * base * level / 100) + 5)


def get_type_effectiveness(atk_type: str, def_types: list[str]) -> float:
    """Get combined type multiplier for an attack type vs defending types."""
    mult = 1.0
    chart = TYPE_CHART.get(atk_type, {})
    for dt in def_types:
        mult *= chart.get(dt, 1.0)
    return mult


def calc_damage(level: int, power: int, attack: int, defense: int,
                effectiveness: float, stab: bool) -> int:
    """Pokémon-style damage formula with STAB and effectiveness."""
    dmg = ((2 * level / 5 + 2) * power * (attack / max(defense, 1)) / 50 + 2)
    if stab:
        dmg *= 1.5
    dmg *= effectiveness
    dmg *= random.uniform(0.85, 1.0)
    return max(1, int(dmg))


def get_catch_rate(current_hp: int, max_hp: int) -> float:
    """Catch probability based on remaining HP. Lower HP = easier catch."""
    hp_ratio = current_hp / max(max_hp, 1)
    # Full HP → ~5% chance, 1 HP → ~90% chance
    catch = 0.90 - (0.85 * hp_ratio)
    return max(0.05, min(0.95, catch))


def render_hp_bar(current_hp: int, max_hp: int, length: int = 8) -> str:
    """Colored HP bar using emojis.  🟩 > 50%  |  🟨 25-50%  |  🟥 < 25%"""
    ratio = max(current_hp, 0) / max(max_hp, 1)
    filled = max(0, round(ratio * length))
    empty = length - filled
    if ratio > 0.5:
        char = "🟩"
    elif ratio > 0.25:
        char = "🟨"
    else:
        char = "🟥"
    return f"{char * filled}{'⬛' * empty}"


def get_learnset(pokemon_id: int) -> list[tuple[int, str]]:
    """
    Return the learnset for a Pokémon.
    Uses custom learnset if defined, otherwise auto-generates from types.
    """
    if pokemon_id in _CUSTOM_LEARNSETS:
        return _CUSTOM_LEARNSETS[pokemon_id]

    poke = KANTO_POKEMON.get(pokemon_id)
    if not poke:
        return [(1, "tackle")]

    moves = []
    # Always start with tackle
    moves.append((1, "tackle"))
    # Add moves from primary type pool
    primary = poke["types"][0]
    if primary in _TYPE_MOVES:
        for mv, lvl in _TYPE_MOVES[primary]:
            if (lvl, mv) not in moves:
                moves.append((lvl, mv))
    # Add moves from secondary type pool (offset levels slightly)
    if len(poke["types"]) > 1:
        secondary = poke["types"][1]
        if secondary in _TYPE_MOVES:
            for mv, lvl in _TYPE_MOVES[secondary]:
                adj_lvl = max(lvl + 4, 5)
                if mv not in [m[1] for m in moves]:
                    moves.append((adj_lvl, mv))

    moves.sort(key=lambda x: x[0])
    return moves


def get_moves_at_level(pokemon_id: int, level: int) -> list[str]:
    """
    Return the list of move keys a Pokémon should know at a given level.
    Takes the latest 4 moves available up to that level.
    """
    ls = get_learnset(pokemon_id)
    available = [mv for lvl, mv in ls if lvl <= level]
    # Keep the last 4 (most recent / strongest)
    return available[-4:] if len(available) > 4 else available


def get_wild_pokemon_ids() -> list[int]:
    """Return all Pokémon IDs eligible for wild encounters."""
    return [pid for pid in KANTO_POKEMON if pid not in _NO_WILD_SPAWN]


def pick_random_starter() -> int:
    """Pick a random starter Pokémon ID using weighted distribution."""
    ids = [p[0] for p in STARTER_POOL]
    weights = [p[1] for p in STARTER_POOL]
    return random.choices(ids, weights=weights, k=1)[0]


# ── Type emojis for display ──
TYPE_EMOJI = {
    "normal": "⚪", "fire": "🔥", "water": "💧", "grass": "🌿",
    "electric": "⚡", "ice": "❄️", "fighting": "🥊", "poison": "☠️",
    "ground": "🏔️", "flying": "🕊️", "psychic": "🔮", "bug": "🐛",
    "rock": "🪨", "ghost": "👻", "dragon": "🐉",
}


def format_types(types: list[str]) -> str:
    """Format types with emojis for embed display."""
    return " ".join(f"{TYPE_EMOJI.get(t, '❓')} {t.capitalize()}" for t in types)
