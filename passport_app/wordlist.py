import secrets

# 256 travel-evocative words — enough for ~4 billion 4-word combinations
WORDS = [
    # landscapes
    "alpine", "canyon", "coast", "delta", "desert", "dune", "fjord", "forest",
    "glacier", "gorge", "harbor", "island", "jungle", "lagoon", "marsh", "mesa",
    "moor", "mountain", "oasis", "ocean", "peak", "plateau", "prairie", "reef",
    "ridge", "river", "savanna", "steppe", "summit", "tundra", "valley", "volcano",
    # directions & movement
    "anchor", "compass", "crossing", "dawn", "departure", "drift", "dusk", "ferry",
    "journey", "landing", "latitude", "layover", "passage", "return", "route", "transit",
    # colours & light
    "amber", "azure", "bronze", "crimson", "ebony", "emerald", "golden", "indigo",
    "ivory", "jade", "mahogany", "midnight", "ochre", "onyx", "sapphire", "scarlet",
    "silver", "tawny", "violet", "verdigris",
    # food & drink
    "basil", "cardamom", "cinnamon", "clove", "coconut", "cumin", "fig", "ginger",
    "honey", "jasmine", "lemon", "mango", "mint", "olive", "pepper", "saffron",
    "tamarind", "thyme", "vanilla", "walnut",
    # architecture & places
    "alley", "arcade", "archway", "bazaar", "bridge", "castle", "cloister", "courtyard",
    "harbour", "lighthouse", "market", "medina", "minaret", "palace", "plaza", "port",
    "quarter", "ruins", "temple", "tower",
    # animals
    "albatross", "bear", "crane", "dolphin", "eagle", "falcon", "fox", "heron",
    "ibis", "jackal", "leopard", "lynx", "osprey", "otter", "raven", "stork",
    "swift", "tiger", "whale", "wolf",
    # weather & sky
    "blizzard", "breeze", "cloud", "cyclone", "fog", "frost", "gale", "haze",
    "lightning", "monsoon", "mist", "rain", "solstice", "squall", "storm", "sunbeam",
    "thunder", "trade", "typhoon", "zenith",
    # textures & materials
    "bamboo", "basalt", "cedar", "chalk", "cobalt", "coral", "flint", "granite",
    "gravel", "linen", "marble", "obsidian", "pine", "quartz", "silk", "slate",
    "teak", "terracotta", "timber", "willow",
    # abstract / travel feeling
    "ancient", "bold", "calm", "distant", "endless", "forgotten", "grand", "hidden",
    "humble", "lost", "narrow", "open", "quiet", "remote", "sacred", "serene",
    "silent", "steep", "wild", "wonder",
    # numbers / time words (add variety)
    "seven", "thirty", "forty", "fifty", "sixty", "eighty", "hundred",
    "morning", "noon", "evening", "spring", "winter", "summer", "autumn",
    "century", "epoch",
]

# Deduplicate and trim to exactly 256 for clean entropy
WORDS = list(dict.fromkeys(WORDS))[:256]


def generate_passphrase(n: int = 4) -> str:
    """Return n random words from the wordlist joined by spaces."""
    return " ".join(secrets.choice(WORDS) for _ in range(n))
