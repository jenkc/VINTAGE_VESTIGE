"""
Era Taxonomy - Canonical era definitions for Vintage Vestige.

~54 eras spanning Ancient Egyptian (3100 BCE) through Gorpcore (2020-present),
organized into period groupings. This module is the single source of truth
for era names used in enrichment prompts, data loaders, and validation.

Each era has a "type" field:
  - "chronological": A bounded historical period defined by *when* it happened.
    The date range is the era's identity (e.g., Victorian, Art Deco, Wartime).
  - "aesthetic": A style movement or subculture. Has a date range for when it
    emerged, but the aesthetic can appear across decades. Actual dates should
    take precedence over era dates for timeline ordering.

Modeled after fashionpedia_taxonomy.py.
"""

# =============================================================================
# CANONICAL ERA REGISTRY
# =============================================================================
# Key = canonical era name (stored in Product.era)
# Value = dict with start year, end year, period grouping, keywords

ERAS = {
    # --- Ancient & Classical ---
    "Ancient Egyptian": {
        "start": -3100, "end": -30,
        "period": "Ancient & Classical",
        "type": "chronological",
        "keywords": ["draped linen", "wigs", "kohl", "kalasiris", "sheath dress"],
    },
    "Ancient Greek": {
        "start": -800, "end": -146,
        "period": "Ancient & Classical",
        "type": "chronological",
        "keywords": ["chiton", "himation", "peplos", "draped wool"],
    },
    "Ancient Roman": {
        "start": -509, "end": 476,
        "period": "Ancient & Classical",
        "type": "chronological",
        "keywords": ["toga", "stola", "tunics", "draped wool"],
    },

    # --- Medieval ---
    "Early Medieval": {
        "start": 476, "end": 1000,
        "period": "Medieval",
        "type": "chronological",
        "keywords": ["simple tunics", "rough wools", "dark ages"],
    },
    "Romanesque": {
        "start": 1000, "end": 1200,
        "period": "Medieval",
        "type": "chronological",
        "keywords": ["long robes", "mantles", "modest silhouettes"],
    },
    "Gothic / High Medieval": {
        "start": 1200, "end": 1400,
        "period": "Medieval",
        "type": "chronological",
        "keywords": ["pointed shoes", "hennin", "rich brocades", "heraldic dress"],
    },
    "Late Medieval": {
        "start": 1400, "end": 1485,
        "period": "Medieval",
        "type": "chronological",
        "keywords": ["houppelande", "elaborate sleeves", "heraldic dress"],
    },

    # --- Renaissance & Early Modern ---
    "Italian Renaissance": {
        "start": 1450, "end": 1550,
        "period": "Renaissance & Early Modern",
        "type": "chronological",
        "keywords": ["slashing", "rich velvets", "low necklines"],
    },
    "Northern Renaissance": {
        "start": 1500, "end": 1600,
        "period": "Renaissance & Early Modern",
        "type": "chronological",
        "keywords": ["ruff collars", "puffed sleeves", "Flemish influence"],
    },
    "Elizabethan": {
        "start": 1558, "end": 1603,
        "period": "Renaissance & Early Modern",
        "type": "chronological",
        "keywords": ["farthingales", "stiff ruffs", "intricate embroidery"],
    },
    "Jacobean": {
        "start": 1603, "end": 1625,
        "period": "Renaissance & Early Modern",
        "type": "chronological",
        "keywords": ["lace", "naturalistic silhouettes", "falling ruffs"],
    },

    # --- 17th Century ---
    "Baroque": {
        "start": 1625, "end": 1700,
        "period": "17th Century",
        "type": "chronological",
        "keywords": ["cavalier hats", "falling lace collars", "opulence", "ribbons"],
    },
    "Restoration": {
        "start": 1660, "end": 1685,
        "period": "17th Century",
        "type": "chronological",
        "keywords": ["petticoat breeches", "ribbons", "flamboyance"],
    },

    # --- 18th Century ---
    "Rococo": {
        "start": 1700, "end": 1775,
        "period": "18th Century",
        "type": "chronological",
        "keywords": ["panniers", "powdered wigs", "pastel florals", "Georgian"],
    },
    "Neoclassical Transition": {
        "start": 1775, "end": 1790,
        "period": "18th Century",
        "type": "chronological",
        "keywords": ["simpler silhouettes", "influence of antiquity"],
    },
    "Revolutionary / Directoire": {
        "start": 1790, "end": 1799,
        "period": "18th Century",
        "type": "chronological",
        "keywords": ["rejection of excess", "natural waistlines", "French Revolution"],
    },

    # --- 19th Century ---
    "Empire / Regency": {
        "start": 1800, "end": 1820,
        "period": "19th Century",
        "type": "chronological",
        "keywords": ["high waistlines", "muslin", "Greco-Roman influence"],
    },
    "Romantic": {
        "start": 1820, "end": 1840,
        "period": "19th Century",
        "type": "chronological",
        "keywords": ["puffed sleeves", "corseted waist", "sentimentality"],
    },
    "Victorian Early / Crinoline": {
        "start": 1840, "end": 1869,
        "period": "19th Century",
        "type": "chronological",
        "keywords": ["cage crinolines", "wide skirts", "mourning dress"],
    },
    "Victorian Late / Bustle": {
        "start": 1870, "end": 1890,
        "period": "19th Century",
        "type": "chronological",
        "keywords": ["back fullness", "tailored structures", "bustle"],
    },
    "Aesthetic / Artistic Dress": {
        "start": 1870, "end": 1900,
        "period": "19th Century",
        "type": "aesthetic",
        "keywords": ["reform dress", "Pre-Raphaelite influence", "loose fit"],
    },
    "Fin de Siecle / Gibson Girl": {
        "start": 1890, "end": 1900,
        "period": "19th Century",
        "type": "chronological",
        "keywords": ["S-curve corset", "hourglass ideal", "Gibson Girl"],
    },

    # --- Early 20th Century ---
    "Edwardian": {
        "start": 1901, "end": 1910,
        "period": "Early 20th Century",
        "type": "chronological",
        "keywords": ["lace blouses", "wide hats", "soft femininity"],
    },
    "Belle Epoque": {
        "start": 1890, "end": 1914,
        "period": "Early 20th Century",
        "type": "chronological",
        "keywords": ["haute couture", "Worth", "Poiret", "opulence"],
    },
    "World War I Transition": {
        "start": 1914, "end": 1918,
        "period": "Early 20th Century",
        "type": "chronological",
        "keywords": ["practical silhouettes", "women enter workforce"],
    },
    "Roaring Twenties / Art Deco": {
        "start": 1920, "end": 1929,
        "period": "Early 20th Century",
        "type": "chronological",
        "keywords": ["dropped waist", "flappers", "beading", "boyish figure"],
    },
    "Great Depression": {
        "start": 1930, "end": 1939,
        "period": "Early 20th Century",
        "type": "chronological",
        "keywords": ["bias cut", "Hollywood glamour", "economical elegance"],
    },

    # --- Mid 20th Century ---
    "Wartime / Utility Fashion": {
        "start": 1940, "end": 1945,
        "period": "Mid 20th Century",
        "type": "chronological",
        "keywords": ["rationing", "broad shoulders", "practical tailoring"],
    },
    "New Look / Post-War": {
        "start": 1947, "end": 1954,
        "period": "Mid 20th Century",
        "type": "chronological",
        "keywords": ["Dior", "full skirts", "nipped waist", "feminine revival"],
    },
    "Atomic Age": {
        "start": 1950, "end": 1960,
        "period": "Mid 20th Century",
        "type": "chronological",
        "keywords": ["poodle skirts", "sportswear", "suburban elegance"],
    },
    "Beat Generation": {
        "start": 1950, "end": 1963,
        "period": "Mid 20th Century",
        "type": "aesthetic",
        "keywords": ["black turtlenecks", "existentialist minimalism"],
    },
    "Space Age": {
        "start": 1960, "end": 1969,
        "period": "Mid 20th Century",
        "type": "chronological",
        "keywords": ["Courreges", "PVC", "Paco Rabanne", "geometric shapes", "futurism"],
    },
    "Mod": {
        "start": 1958, "end": 1968,
        "period": "Mid 20th Century",
        "type": "aesthetic",
        "keywords": ["Mary Quant", "Carnaby Street", "miniskirts", "sharp suits", "parkas", "target logo"],
    },
    "Hippie / Counterculture": {
        "start": 1965, "end": 1974,
        "period": "Mid 20th Century",
        "type": "aesthetic",
        "keywords": ["peasant blouses", "fringe", "tie-dye", "anti-fashion"],
    },
    "Glam Rock": {
        "start": 1970, "end": 1976,
        "period": "Mid 20th Century",
        "type": "aesthetic",
        "keywords": ["platform shoes", "androgyny", "Bowie influence"],
    },

    # --- Late 20th Century ---
    "Disco": {
        "start": 1975, "end": 1980,
        "period": "Late 20th Century",
        "type": "chronological",
        "keywords": ["sequins", "halter necks", "spandex"],
    },
    "Punk": {
        "start": 1976, "end": 1983,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["safety pins", "ripped fabrics", "anti-establishment"],
    },
    "New Wave / Post-Punk": {
        "start": 1979, "end": 1985,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["sharp tailoring", "dark palettes", "androgyny"],
    },
    "Power Dressing": {
        "start": 1980, "end": 1990,
        "period": "Late 20th Century",
        "type": "chronological",
        "keywords": ["shoulder pads", "corporate feminism", "Dynasty glam"],
    },
    "New Romanticism": {
        "start": 1980, "end": 1985,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["ruffles", "piracy aesthetics", "Vivienne Westwood"],
    },
    "Hip-Hop": {
        "start": 1980, "end": 2030,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["tracksuits", "gold chains", "streetwear origins"],
    },
    "Grunge": {
        "start": 1988, "end": 1996,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["flannel", "combat boots", "anti-fashion aesthetic"],
    },
    "Minimalism": {
        "start": 1990, "end": 1999,
        "period": "Late 20th Century",
        "type": "chronological",
        "keywords": ["Calvin Klein", "Helmut Lang", "clean lines"],
    },
    "Rave / Club Kid": {
        "start": 1988, "end": 1998,
        "period": "Late 20th Century",
        "type": "aesthetic",
        "keywords": ["neon", "PLUR", "exaggerated fantasy"],
    },
    "Supermodel Era": {
        "start": 1990, "end": 1997,
        "period": "Late 20th Century",
        "type": "chronological",
        "keywords": ["logomania", "body-conscious", "runway excess"],
    },

    # --- 21st Century ---
    "Y2K": {
        "start": 1999, "end": 2004,
        "period": "21st Century",
        "type": "chronological",
        "keywords": ["low-rise", "butterfly clips", "metallic", "Juicy Couture"],
    },
    "Indie Sleaze": {
        "start": 2004, "end": 2010,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["American Apparel", "skinny jeans", "hipster"],
    },
    "Normcore": {
        "start": 2013, "end": 2016,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["deliberate averageness", "anti-trend"],
    },
    "Athleisure": {
        "start": 2010, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["Lululemon", "performance-as-lifestyle"],
    },
    "Cottagecore": {
        "start": 2018, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["prairie dresses", "pastoral nostalgia"],
    },
    "Dark Academia": {
        "start": 2019, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["tweed", "layering", "literary romanticism"],
    },
    "Quiet Luxury": {
        "start": 2020, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["Loro Piana", "logoless", "understated wealth"],
    },
    "Gorpcore": {
        "start": 2020, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["technical outdoor wear", "Arc'teryx", "Salomon"],
    },
    "Dopamine Dressing": {
        "start": 2021, "end": 2030,
        "period": "21st Century",
        "type": "aesthetic",
        "keywords": ["maximalist color", "joy-forward"],
    },
    "Preppy / Ivy League": {
        "start": 1950, "end": 2030,
        "period": "Mid 20th Century",
        "type": "aesthetic",
        "keywords": ["Ralph Lauren", "Brooks Brothers", "polo shirts", "blazers", "penny loafers", "madras"],
    },
}


# =============================================================================
# DERIVED LOOKUPS
# =============================================================================

ERA_NAMES = list(ERAS.keys())

PERIODS = list(dict.fromkeys(era_data["period"] for era_data in ERAS.values()))

ERAS_BY_PERIOD = {}
for _era_name, _era_data in ERAS.items():
    ERAS_BY_PERIOD.setdefault(_era_data["period"], []).append(_era_name)

ERA_NAME_LOWER = {name.lower(): name for name in ERA_NAMES}
_UNRECOGNIZED_ERAS = {}  # For collecting unrecognized eras for later analysis

# =============================================================================
# ALIAS MAP — deterministic normalization of known variants
# =============================================================================

ERA_ALIASES = {
    # --- Common Claude output variants ---
    "victorian": "Victorian Late / Bustle",
    "victorian era": "Victorian Late / Bustle",
    "art deco": "Roaring Twenties / Art Deco",
    "art deco period": "Roaring Twenties / Art Deco",
    "jazz age": "Roaring Twenties / Art Deco",
    "roaring twenties": "Roaring Twenties / Art Deco",
    "mid-century": "Atomic Age",
    "mid century": "Atomic Age",
    "mid-century modern": "Atomic Age",
    "belle epoque": "Belle Epoque",
    "belle \u00e9poque": "Belle Epoque",
    "regency": "Empire / Regency",
    "empire": "Empire / Regency",
    "georgian": "Rococo",
    "crinoline": "Victorian Early / Crinoline",
    "bustle": "Victorian Late / Bustle",
    "bustle era": "Victorian Late / Bustle",
    "gibson girl": "Fin de Siecle / Gibson Girl",
    "fin de si\u00e8cle": "Fin de Siecle / Gibson Girl",
    "aesthetic movement": "Aesthetic / Artistic Dress",
    "artistic dress": "Aesthetic / Artistic Dress",
    "counterculture": "Hippie / Counterculture",
    "hippie": "Hippie / Counterculture",
    "mod": "Mod",
    "new look": "New Look / Post-War",
    "post-war": "New Look / Post-War",
    "directoire": "Revolutionary / Directoire",
    "club kid": "Rave / Club Kid",
    "rave": "Rave / Club Kid",
    "new wave": "New Wave / Post-Punk",
    "post-punk": "New Wave / Post-Punk",
    "old money": "Quiet Luxury",
    "quiet luxury / old money": "Quiet Luxury",
    "recession chic": "Normcore",
    "space age": "Space Age",
    "mod / space age": "Space Age",
    "preppy": "Preppy / Ivy League",
    "ivy league": "Preppy / Ivy League",

    # --- Legacy data loader values (load_met_vintage.py ERA_MAP) ---
    "pre-1700s": "Baroque",
    "colonial": "Rococo",
    "post-modern": "Grunge",
    "contemporary": "Y2K",
    "modern": "Quiet Luxury",

    # --- Decade-as-era values from Smithsonian / Met modern loaders ---
    "1700s": "Rococo",
    "1800s": "Empire / Regency",
    "1810s": "Empire / Regency",
    "1820s": "Romantic",
    "1830s": "Romantic",
    "1840s": "Victorian Early / Crinoline",
    "1850s": "Victorian Early / Crinoline",
    "1860s": "Victorian Early / Crinoline",
    "1870s": "Victorian Late / Bustle",
    "1880s": "Victorian Late / Bustle",
    "1890s": "Fin de Siecle / Gibson Girl",
    "1900s": "Edwardian",
    "1910s": "World War I Transition",
    "1920s": "Roaring Twenties / Art Deco",
    "1930s": "Great Depression",
    "1940s": "Wartime / Utility Fashion",
    "1950s": "Atomic Age",
    "1960s": "Space Age",
    "1970s": "Hippie / Counterculture",
    "1980s": "Power Dressing",
    "1990s": "Minimalism",
    "2000s": "Y2K",
    "2010s": "Athleisure",
    "2020s": "Quiet Luxury",

    # --- Enrichment prompt legacy values ---
    "streetwear": "Hip-Hop",
    "preppy revival": "Normcore",
    "bohemian revival": "Cottagecore",
    "retro revival": "Y2K",
    "avant-garde": "Space Age",
    "minimalist": "Minimalism",

    # --- Variants found in existing database ---
    "disco era": "Disco",
    "grunge era": "Grunge",
    "victorian-inspired": "Victorian Late / Bustle",
    "1940s-inspired": "Wartime / Utility Fashion",
    "1950s-inspired": "Atomic Age",
    "1960s-inspired": "Space Age",
    "1970s-inspired": "Hippie / Counterculture",
    "1990s-inspired": "Minimalism",
    "art deco revival": "Roaring Twenties / Art Deco",
    "post-disco": "Disco",
    "antebellum": "Victorian Early / Crinoline",
    "federal": "Empire / Regency",
    "federal period": "Empire / Regency",
    "medieval": "Gothic / High Medieval",
    "renaissance": "Italian Renaissance",
    "stuart": "Baroque",
    "imperial russian": "Victorian Late / Bustle",
    "ottoman empire": "Baroque",
    "qing dynasty": "Rococo",
    "cold war": "Atomic Age",
    "late cold war": "Power Dressing",
    "reagan era": "Power Dressing",
    "late 20th century": "Minimalism",
    "folk revival": "Hippie / Counterculture",
    "contemporary folk": "Cottagecore",
    "taish\u014d": "Edwardian",
}


# =============================================================================
# YEAR -> ERA MAPPING
# =============================================================================

def year_to_era(year: int) -> str | None:
    """Map a year to its canonical era name.

    Prefers chronological eras over aesthetic ones. Among same-type matches,
    prefers the more specific (shorter-range) era.
    Returns None if no era covers the given year.
    """
    matches = []
    for era_name, era_data in ERAS.items():
        if era_data["start"] <= year <= era_data["end"]:
            # Sort key: chronological first (0), aesthetic second (1), then by span
            type_order = 0 if era_data.get("type") == "chronological" else 1
            span = era_data["end"] - era_data["start"]
            matches.append((type_order, span, era_name))
    if not matches:
        return None
    matches.sort()
    return matches[0][2]


# =============================================================================
# NORMALIZATION
# =============================================================================

def normalize_era(raw_era: str | None, product_id: int | None = None) -> str | None:
    """Normalize a raw era string to its canonical name.

    Lookup order:
      1. Exact match (case-insensitive) against canonical names
      2. Alias dict lookup
      3. Strip common suffixes ("era", "period", "style", "movement")
      4. Return raw_era unchanged if no match
    """
    if not raw_era:
        return None
    lowered = raw_era.strip().lower()

    # Strip parenthetical date ranges: "Athleisure (2010-present)" → "athleisure"
    import re
    lowered = re.sub(r'\s*\([^)]*\)\s*$', '', lowered).strip()


    # Exact match against canonical names
    if lowered in ERA_NAME_LOWER:
        return ERA_NAME_LOWER[lowered]

    # Alias lookup
    if lowered in ERA_ALIASES:
        return ERA_ALIASES[lowered]

    # Strip common suffixes and retry
    for suffix in (" era", " period", " style", " movement", " fashion"):
        if lowered.endswith(suffix):
            stripped = lowered[:-len(suffix)].rstrip()
            if stripped in ERA_NAME_LOWER:
                return ERA_NAME_LOWER[stripped]
            if stripped in ERA_ALIASES:
                return ERA_ALIASES[stripped]

    # No match — collect for later fix-up, pass through
    if lowered not in _UNRECOGNIZED_ERAS:
        _UNRECOGNIZED_ERAS[lowered] = {'raw': raw_era, 'product_ids': set()}
    if product_id is not None:
        _UNRECOGNIZED_ERAS[lowered]['product_ids'].add(product_id)

    return raw_era

def report_unrecognized_eras():
    """Print summary of unrecognized era strings and which products have them."""
    if not _UNRECOGNIZED_ERAS:
        print("  All eras matched taxonomy.")
        return
    print(f"\n  [ERA SUMMARY] {len(_UNRECOGNIZED_ERAS)} unrecognized era values:")
    for lowered, entry in sorted(_UNRECOGNIZED_ERAS.items()):
        print(f"    '{entry['raw']}' ({len(entry['product_ids'])} products): {sorted(entry['product_ids'])[:10]}...")

    print(f"  → Add these to ERA_ALIASES in era_taxonomy.py, then run fix_unrecognized_eras(db)\n")


def fix_unrecognized_eras(db):
    """Re-normalize eras for products that had unrecognized values.
    
    Call this AFTER adding new entries to ERA_ALIASES.
    """
    from storage.database import Product
    
    fixed = 0
    still_unknown = []
    for lowered, entry in _UNRECOGNIZED_ERAS.items():
        canonical = normalize_era(entry['raw'])
        if canonical != entry['raw']:
            for pid in entry['product_ids']:
                product = db.query(Product).filter(Product.id == pid).first()
                if product:
                    product.era = canonical
                    fixed += 1
        else:
            still_unknown.append(entry['raw'])
    
    db.commit()
    print(f"  Fixed {fixed} products.")
    if still_unknown:
        print(f"  Still unrecognized: {still_unknown}")
    _UNRECOGNIZED_ERAS.clear()

def export_unrecognized_eras(filepath="unrecognized_eras.csv"):
    """Export unrecognized eras to CSV with product IDs."""
    import csv
    if not _UNRECOGNIZED_ERAS:
        print("  No unrecognized eras to export.")
        return
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['raw_era', 'count', 'product_ids'])
        for lowered, entry in sorted(_UNRECOGNIZED_ERAS.items()):
            writer.writerow([entry['raw'], len(entry['product_ids']), ','.join(str(pid) for pid in sorted(entry['product_ids']))])
    print(f"  Exported {len(_UNRECOGNIZED_ERAS)} unrecognized eras to {filepath}")


# =============================================================================
# PROMPT BUILDER
# =============================================================================

def build_era_prompt_section() -> str:
    """Build the era section for Claude enrichment prompts.

    Returns a formatted string listing all eras grouped by period,
    suitable for embedding in the enrichment prompt.
    """
    lines = []
    for period in PERIODS:
        era_parts = []
        for era_name in ERAS_BY_PERIOD[period]:
            era = ERAS[era_name]
            start = era["start"]
            end = era["end"]
            if start < 0 and end < 0:
                start_str = f"{abs(start)} BCE"
                end_str = f"{abs(end)} BCE"
            elif start < 0:
                start_str = f"{abs(start)} BCE"
                end_str = str(end)
            else:
                start_str = str(start)
                end_str = "present" if end >= 2030 else str(end)
            era_parts.append(f"{era_name} ({start_str}-{end_str})")
        lines.append(f"  {period}: {' | '.join(era_parts)}")
    return "\n".join(lines)


# =============================================================================
# ERA TYPE HELPERS
# =============================================================================

def is_aesthetic(era_name: str) -> bool:
    """Return True if the era is an aesthetic/vibe rather than a chronological period."""
    era = ERAS.get(era_name)
    return era is not None and era.get("type") == "aesthetic"


def is_chronological(era_name: str) -> bool:
    """Return True if the era is a chronological period."""
    era = ERAS.get(era_name)
    return era is not None and era.get("type") == "chronological"


def era_sort_key(era_name: str) -> float:
    """Return a numeric sort key for chronological ordering.

    Uses the midpoint of the era's date range. Aesthetic eras use their
    emergence midpoint but actual item dates should be preferred when available.
    Returns float('inf') for unknown eras.
    """
    era = ERAS.get(era_name)
    if not era:
        return float('inf')
    return (era["start"] + era["end"]) / 2


def eras_between(era_a: str, era_b: str) -> list[str]:
    """Return all eras chronologically between two eras (inclusive), sorted by midpoint."""
    a_key = era_sort_key(era_a)
    b_key = era_sort_key(era_b)
    lo, hi = min(a_key, b_key), max(a_key, b_key)
    between = []
    for name in ERA_NAMES:
        mid = era_sort_key(name)
        if lo <= mid <= hi:
            between.append((mid, name))
    between.sort()
    return [name for _, name in between]
