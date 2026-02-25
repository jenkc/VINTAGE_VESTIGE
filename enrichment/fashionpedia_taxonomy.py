"""
Fashionpedia Taxonomy - Complete structured data extracted from the official
Fashionpedia annotation JSON (instances_attributes_val2020.json).

Source: https://s3.amazonaws.com/ifashionist-dataset/annotations/instances_attributes_val2020.json
Paper: "Fashionpedia: Ontology, Segmentation, and an Attribute Localization Dataset"
       (ECCV 2020) - https://arxiv.org/abs/2004.12276

Structure:
    46 total object categories:
        - 27 main apparel categories (level 2, grouped by body region)
        - 19 apparel parts:
            - 7 garment parts (hood, collar, lapel, epaulette, sleeve, pocket, neckline)
            - 2 closures (buckle, zipper)
            - 10 decorations (applique, bead, bow, flower, fringe, ribbon, rivet, ruffle, sequin, tassel)
    294 fine-grained attributes across 9 logical super-categories:
        - nickname (153) - includes sub-nicknames for garments, collars, lapels, sleeves, pockets
        - silhouette (25)
        - neckline type (25)
        - textile finishing, manufacturing techniques (21)
        - textile pattern (18 + 6 animal sub-patterns = 24 total pattern-related)
        - length (15)
        - non-textile material type (10 + 4 leather sub-types = 14 total material-related)
        - opening type (10)
        - waistline (7)
"""

# =============================================================================
# MAIN APPAREL CATEGORIES (27 total)
# Organized by body-region supercategory
# =============================================================================

MAIN_APPAREL_CATEGORIES = {
    "upperbody": [
        {"id": 0,  "name": "shirt, blouse",               "taxonomy_id": "combo000000"},
        {"id": 1,  "name": "top, t-shirt, sweatshirt",     "taxonomy_id": "combo000001"},
        {"id": 2,  "name": "sweater",                      "taxonomy_id": "obj000008_00"},
        {"id": 3,  "name": "cardigan",                     "taxonomy_id": "obj000009_00"},
        {"id": 4,  "name": "jacket",                       "taxonomy_id": "obj000010_00"},
        {"id": 5,  "name": "vest",                         "taxonomy_id": "obj000011_00"},
    ],
    "lowerbody": [
        {"id": 6,  "name": "pants",                        "taxonomy_id": "obj000013_00"},
        {"id": 7,  "name": "shorts",                       "taxonomy_id": "obj000014_00"},
        {"id": 8,  "name": "skirt",                        "taxonomy_id": "obj000015_00"},
    ],
    "wholebody": [
        {"id": 9,  "name": "coat",                         "taxonomy_id": "obj000017_00"},
        {"id": 10, "name": "dress",                        "taxonomy_id": "obj000018_00"},
        {"id": 11, "name": "jumpsuit",                     "taxonomy_id": "obj000019_00"},
        {"id": 12, "name": "cape",                         "taxonomy_id": "obj000020_00"},
    ],
    "head": [
        {"id": 13, "name": "glasses",                      "taxonomy_id": "obj000023_00"},
        {"id": 14, "name": "hat",                          "taxonomy_id": "obj000025_00"},
        {"id": 15, "name": "headband, head covering, hair accessory", "taxonomy_id": "combo000002"},
    ],
    "neck": [
        {"id": 16, "name": "tie",                          "taxonomy_id": "obj000030_00"},
    ],
    "arms and hands": [
        {"id": 17, "name": "glove",                        "taxonomy_id": "obj000032_00"},
        {"id": 18, "name": "watch",                        "taxonomy_id": "obj000033_00"},
    ],
    "waist": [
        {"id": 19, "name": "belt",                         "taxonomy_id": "obj000035_00"},
    ],
    "legs and feet": [
        {"id": 20, "name": "leg warmer",                   "taxonomy_id": "obj000037_00"},
        {"id": 21, "name": "tights, stockings",            "taxonomy_id": "combo000003"},
        {"id": 22, "name": "sock",                         "taxonomy_id": "obj000040_00"},
        {"id": 23, "name": "shoe",                         "taxonomy_id": "obj000041_00"},
    ],
    "others": [
        {"id": 24, "name": "bag, wallet",                  "taxonomy_id": "combo000004"},
        {"id": 25, "name": "scarf",                        "taxonomy_id": "obj000045_00"},
        {"id": 26, "name": "umbrella",                     "taxonomy_id": "obj000046_00"},
    ],
}

# =============================================================================
# APPAREL PARTS (19 total = 7 garment parts + 2 closures + 10 decorations)
# =============================================================================

GARMENT_PARTS = [
    {"id": 27, "name": "hood",       "supercategory": "garment parts", "taxonomy_id": "obj000049_00"},
    {"id": 28, "name": "collar",     "supercategory": "garment parts", "taxonomy_id": "obj000050_00"},
    {"id": 29, "name": "lapel",      "supercategory": "garment parts", "taxonomy_id": "obj000051_00"},
    {"id": 30, "name": "epaulette",  "supercategory": "garment parts", "taxonomy_id": "obj000052_00"},
    {"id": 31, "name": "sleeve",     "supercategory": "garment parts", "taxonomy_id": "obj000053_00"},
    {"id": 32, "name": "pocket",     "supercategory": "garment parts", "taxonomy_id": "obj000055_00"},
    {"id": 33, "name": "neckline",   "supercategory": "garment parts", "taxonomy_id": "obj000056_00"},
]

CLOSURES = [
    {"id": 34, "name": "buckle",     "supercategory": "closures",      "taxonomy_id": "obj000058_00"},
    {"id": 35, "name": "zipper",     "supercategory": "closures",      "taxonomy_id": "obj000059_00"},
]

DECORATIONS = [
    {"id": 36, "name": "applique",   "supercategory": "decorations",   "taxonomy_id": "obj000061_00"},
    {"id": 37, "name": "bead",       "supercategory": "decorations",   "taxonomy_id": "obj000062_00"},
    {"id": 38, "name": "bow",        "supercategory": "decorations",   "taxonomy_id": "obj000063_00"},
    {"id": 39, "name": "flower",     "supercategory": "decorations",   "taxonomy_id": "obj000064_00"},
    {"id": 40, "name": "fringe",     "supercategory": "decorations",   "taxonomy_id": "obj000065_00"},
    {"id": 41, "name": "ribbon",     "supercategory": "decorations",   "taxonomy_id": "obj000066_00"},
    {"id": 42, "name": "rivet",      "supercategory": "decorations",   "taxonomy_id": "obj000067_00"},
    {"id": 43, "name": "ruffle",     "supercategory": "decorations",   "taxonomy_id": "obj000068_00"},
    {"id": 44, "name": "sequin",     "supercategory": "decorations",   "taxonomy_id": "obj000069_00"},
    {"id": 45, "name": "tassel",     "supercategory": "decorations",   "taxonomy_id": "obj000070_00"},
]

ALL_APPAREL_PARTS = GARMENT_PARTS + CLOSURES + DECORATIONS  # 19 total

# =============================================================================
# ATTRIBUTES (294 total)
# Organized by super-category
#
# Note on the "nickname" super-category:
#   In Fashionpedia's JSON, "nickname" is a single super-category containing 153
#   attributes. These are contextual nicknames for specific garment types AND for
#   garment parts (collars, lapels, sleeves, pockets). Below we preserve the
#   official grouping AND provide a semantic sub-grouping for easier use.
#
# Note on hierarchy:
#   Some attributes are level 2 (sub-attributes). For example:
#     - "animal" patterns (leopard, snakeskin, etc.) are children of "textile pattern"
#     - "leather" types (suede, shearling, etc.) are children of "non-textile material type"
# =============================================================================

ATTRIBUTES_BY_SUPERCATEGORY = {
    # -------------------------------------------------------------------------
    # NICKNAME (153 attributes)
    # Specific style names for garments and garment parts
    # -------------------------------------------------------------------------
    "nickname": [
        # -- Shirt/Top nicknames --
        {"id": 0,   "name": "classic (t-shirt)",                "taxonomy_id": "att000002_00"},
        {"id": 1,   "name": "polo (shirt)",                     "taxonomy_id": "att000003_00"},
        {"id": 2,   "name": "undershirt",                       "taxonomy_id": "att000004_00"},
        {"id": 3,   "name": "henley (shirt)",                   "taxonomy_id": "att000005_00"},
        {"id": 4,   "name": "ringer (t-shirt)",                 "taxonomy_id": "att000006_00"},
        {"id": 5,   "name": "raglan (t-shirt)",                 "taxonomy_id": "att000007_00"},
        {"id": 6,   "name": "rugby (shirt)",                    "taxonomy_id": "att000008_00"},
        {"id": 7,   "name": "sailor (shirt)",                   "taxonomy_id": "att000009_00"},
        {"id": 8,   "name": "crop (top)",                       "taxonomy_id": "att000010_00"},
        {"id": 9,   "name": "halter (top)",                     "taxonomy_id": "att000011_00"},
        {"id": 10,  "name": "camisole",                         "taxonomy_id": "att000012_00"},
        {"id": 11,  "name": "tank (top)",                       "taxonomy_id": "att000013_00"},
        {"id": 12,  "name": "peasant (top)",                    "taxonomy_id": "att000014_00"},
        {"id": 13,  "name": "tube (top)",                       "taxonomy_id": "att000015_00"},
        {"id": 14,  "name": "tunic (top)",                      "taxonomy_id": "att000016_00"},
        {"id": 15,  "name": "smock (top)",                      "taxonomy_id": "att000017_00"},
        # -- Sweater/Jacket nicknames --
        {"id": 16,  "name": "hoodie",                           "taxonomy_id": "att000018_00"},
        {"id": 17,  "name": "blazer",                           "taxonomy_id": "att000019_00"},
        {"id": 18,  "name": "pea (jacket)",                     "taxonomy_id": "att000020_00"},
        {"id": 19,  "name": "puffer (jacket)",                  "taxonomy_id": "att000021_00"},
        {"id": 20,  "name": "biker (jacket)",                   "taxonomy_id": "att000022_00"},
        {"id": 21,  "name": "trucker (jacket)",                 "taxonomy_id": "att000023_00"},
        {"id": 22,  "name": "bomber (jacket)",                  "taxonomy_id": "att000024_00"},
        {"id": 23,  "name": "anorak",                           "taxonomy_id": "att000025_00"},
        {"id": 24,  "name": "safari (jacket)",                  "taxonomy_id": "att000026_00"},
        {"id": 25,  "name": "mao (jacket)",                     "taxonomy_id": "att000027_00"},
        {"id": 26,  "name": "nehru (jacket)",                   "taxonomy_id": "att000028_00"},
        {"id": 27,  "name": "norfolk (jacket)",                 "taxonomy_id": "att000029_00"},
        {"id": 28,  "name": "classic military (jacket)",        "taxonomy_id": "att000030_00"},
        {"id": 29,  "name": "track (jacket)",                   "taxonomy_id": "att000031_00"},
        {"id": 30,  "name": "windbreaker",                      "taxonomy_id": "att000032_00"},
        {"id": 31,  "name": "chanel (jacket)",                  "taxonomy_id": "att000033_00"},
        {"id": 32,  "name": "bolero",                           "taxonomy_id": "att000034_00"},
        {"id": 33,  "name": "tuxedo (jacket)",                  "taxonomy_id": "att000035_00"},
        {"id": 34,  "name": "varsity (jacket)",                 "taxonomy_id": "att000036_00"},
        {"id": 35,  "name": "crop (jacket)",                    "taxonomy_id": "att000037_00"},
        # -- Pants nicknames --
        {"id": 36,  "name": "jeans",                            "taxonomy_id": "att000038_00"},
        {"id": 37,  "name": "sweatpants",                       "taxonomy_id": "att000039_00"},
        {"id": 38,  "name": "leggings",                         "taxonomy_id": "att000040_00"},
        {"id": 39,  "name": "hip-huggers (pants)",              "taxonomy_id": "att000041_00"},
        {"id": 40,  "name": "cargo (pants)",                    "taxonomy_id": "att000042_00"},
        {"id": 41,  "name": "culottes",                         "taxonomy_id": "att000043_00"},
        {"id": 42,  "name": "capri (pants)",                    "taxonomy_id": "att000044_00"},
        {"id": 43,  "name": "harem (pants)",                    "taxonomy_id": "att000045_00"},
        {"id": 44,  "name": "sailor (pants)",                   "taxonomy_id": "att000046_00"},
        {"id": 45,  "name": "jodhpur",                          "taxonomy_id": "att000047_00"},
        {"id": 46,  "name": "peg (pants)",                      "taxonomy_id": "att000048_00"},
        {"id": 47,  "name": "camo (pants)",                     "taxonomy_id": "att000049_00"},
        {"id": 48,  "name": "track (pants)",                    "taxonomy_id": "att000050_00"},
        {"id": 49,  "name": "crop (pants)",                     "taxonomy_id": "att000051_00"},
        # -- Shorts nicknames --
        {"id": 50,  "name": "short (shorts)",                   "taxonomy_id": "att000052_00"},
        {"id": 51,  "name": "booty (shorts)",                   "taxonomy_id": "att000053_00"},
        {"id": 52,  "name": "bermuda (shorts)",                 "taxonomy_id": "att000054_00"},
        {"id": 53,  "name": "cargo (shorts)",                   "taxonomy_id": "att000055_00"},
        {"id": 54,  "name": "trunks",                           "taxonomy_id": "att000056_00"},
        {"id": 55,  "name": "boardshorts",                      "taxonomy_id": "att000057_00"},
        {"id": 56,  "name": "skort",                            "taxonomy_id": "att000058_00"},
        {"id": 57,  "name": "roll-up (shorts)",                 "taxonomy_id": "att000059_00"},
        {"id": 58,  "name": "tie-up (shorts)",                  "taxonomy_id": "att000060_00"},
        {"id": 59,  "name": "culotte (shorts)",                 "taxonomy_id": "att000061_00"},
        {"id": 60,  "name": "lounge (shorts)",                  "taxonomy_id": "att000062_00"},
        {"id": 61,  "name": "bloomers",                         "taxonomy_id": "att000063_00"},
        # -- Skirt nicknames --
        {"id": 62,  "name": "tutu (skirt)",                     "taxonomy_id": "att000064_00"},
        {"id": 63,  "name": "kilt",                             "taxonomy_id": "att000065_00"},
        {"id": 64,  "name": "wrap (skirt)",                     "taxonomy_id": "att000066_00"},
        {"id": 65,  "name": "skater (skirt)",                   "taxonomy_id": "att000067_00"},
        {"id": 66,  "name": "cargo (skirt)",                    "taxonomy_id": "att000068_00"},
        {"id": 67,  "name": "hobble (skirt)",                   "taxonomy_id": "att000069_00"},
        {"id": 68,  "name": "sheath (skirt)",                   "taxonomy_id": "att000070_00"},
        {"id": 69,  "name": "ball gown (skirt)",                "taxonomy_id": "att000071_00"},
        {"id": 70,  "name": "gypsy (skirt)",                    "taxonomy_id": "att000072_00"},
        {"id": 71,  "name": "rah-rah (skirt)",                  "taxonomy_id": "att000073_00"},
        {"id": 72,  "name": "prairie (skirt)",                  "taxonomy_id": "att000074_00"},
        {"id": 73,  "name": "flamenco (skirt)",                 "taxonomy_id": "att000075_00"},
        {"id": 74,  "name": "accordion (skirt)",                "taxonomy_id": "att000076_00"},
        {"id": 75,  "name": "sarong (skirt)",                   "taxonomy_id": "att000077_00"},
        {"id": 76,  "name": "tulip (skirt)",                    "taxonomy_id": "att000078_00"},
        {"id": 77,  "name": "dirndl (skirt)",                   "taxonomy_id": "att000079_00"},
        {"id": 78,  "name": "godet (skirt)",                    "taxonomy_id": "att000080_00"},
        # -- Coat nicknames --
        {"id": 79,  "name": "blanket (coat)",                   "taxonomy_id": "att000081_00"},
        {"id": 80,  "name": "parka",                            "taxonomy_id": "att000082_00"},
        {"id": 81,  "name": "trench (coat)",                    "taxonomy_id": "att000083_00"},
        {"id": 82,  "name": "pea (coat)",                       "taxonomy_id": "att000084_00"},
        {"id": 83,  "name": "shearling (coat)",                 "taxonomy_id": "att000085_00"},
        {"id": 84,  "name": "teddy bear (coat)",                "taxonomy_id": "att000086_00"},
        {"id": 85,  "name": "puffer (coat)",                    "taxonomy_id": "att000087_00"},
        {"id": 86,  "name": "duster (coat)",                    "taxonomy_id": "att000088_00"},
        {"id": 87,  "name": "raincoat",                         "taxonomy_id": "att000089_00"},
        {"id": 88,  "name": "kimono",                           "taxonomy_id": "att000090_00"},
        {"id": 89,  "name": "robe",                             "taxonomy_id": "att000091_00"},
        {"id": 90,  "name": "dress (coat )",                    "taxonomy_id": "att000092_00"},
        {"id": 91,  "name": "duffle (coat)",                    "taxonomy_id": "att000093_00"},
        {"id": 92,  "name": "wrap (coat)",                      "taxonomy_id": "att000094_00"},
        {"id": 93,  "name": "military (coat)",                  "taxonomy_id": "att000095_00"},
        {"id": 94,  "name": "swing (coat)",                     "taxonomy_id": "att000096_00"},
        # -- Dress nicknames --
        {"id": 95,  "name": "halter (dress)",                   "taxonomy_id": "att000097_00"},
        {"id": 96,  "name": "wrap (dress)",                     "taxonomy_id": "att000098_00"},
        {"id": 97,  "name": "chemise (dress)",                  "taxonomy_id": "att000099_00"},
        {"id": 98,  "name": "slip (dress)",                     "taxonomy_id": "att000100_00"},
        {"id": 99,  "name": "cheongsams",                       "taxonomy_id": "att000101_00"},
        {"id": 100, "name": "jumper (dress)",                   "taxonomy_id": "att000102_00"},
        {"id": 101, "name": "shift (dress)",                    "taxonomy_id": "att000103_00"},
        {"id": 102, "name": "sheath (dress)",                   "taxonomy_id": "att000104_00"},
        {"id": 103, "name": "shirt (dress)",                    "taxonomy_id": "att000105_00"},
        {"id": 104, "name": "sundress",                         "taxonomy_id": "att000106_00"},
        {"id": 105, "name": "kaftan",                           "taxonomy_id": "att000107_00"},
        {"id": 106, "name": "bodycon (dress)",                  "taxonomy_id": "att000108_00"},
        {"id": 107, "name": "nightgown",                        "taxonomy_id": "att000109_00"},
        {"id": 108, "name": "gown",                             "taxonomy_id": "att000110_00"},
        {"id": 109, "name": "sweater (dress)",                  "taxonomy_id": "att000111_00"},
        {"id": 110, "name": "tea (dress)",                      "taxonomy_id": "att000112_00"},
        {"id": 111, "name": "blouson (dress)",                  "taxonomy_id": "att000113_00"},
        {"id": 112, "name": "tunic (dress)",                    "taxonomy_id": "att000114_00"},
        {"id": 113, "name": "skater (dress)",                   "taxonomy_id": "att000115_00"},
        # -- Collar nicknames --
        {"id": 161, "name": "asymmetric (collar)",              "taxonomy_id": "att000166_00"},
        {"id": 162, "name": "regular (collar)",                 "taxonomy_id": "att000167_00"},
        {"id": 163, "name": "shirt (collar)",                   "taxonomy_id": "att000168_00"},
        {"id": 164, "name": "polo (collar)",                    "taxonomy_id": "att000169_00"},
        {"id": 165, "name": "chelsea (collar)",                 "taxonomy_id": "att000170_00"},
        {"id": 166, "name": "banded (collar)",                  "taxonomy_id": "att000171_00"},
        {"id": 167, "name": "mandarin (collar)",                "taxonomy_id": "att000172_00"},
        {"id": 168, "name": "peter pan (collar)",               "taxonomy_id": "att000173_00"},
        {"id": 169, "name": "bow (collar)",                     "taxonomy_id": "att000174_00"},
        {"id": 170, "name": "stand-away (collar)",              "taxonomy_id": "att000175_00"},
        {"id": 171, "name": "jabot (collar)",                   "taxonomy_id": "att000176_00"},
        {"id": 172, "name": "sailor (collar)",                  "taxonomy_id": "att000177_00"},
        {"id": 173, "name": "oversized (collar)",               "taxonomy_id": "att000178_00"},
        # -- Lapel nicknames --
        {"id": 174, "name": "notched (lapel)",                  "taxonomy_id": "att000179_00"},
        {"id": 175, "name": "peak (lapel)",                     "taxonomy_id": "att000180_00"},
        {"id": 176, "name": "shawl (lapel)",                    "taxonomy_id": "att000181_00"},
        {"id": 177, "name": "napoleon (lapel)",                 "taxonomy_id": "att000182_00"},
        {"id": 178, "name": "oversized (lapel)",                "taxonomy_id": "att000183_00"},
        # -- Sleeve nicknames --
        {"id": 204, "name": "set-in sleeve",                    "taxonomy_id": "att000210_00"},
        {"id": 205, "name": "dropped-shoulder sleeve",          "taxonomy_id": "att000211_00"},
        {"id": 206, "name": "raglan (sleeve)",                  "taxonomy_id": "att000212_00"},
        {"id": 207, "name": "cap (sleeve)",                     "taxonomy_id": "att000213_00"},
        {"id": 208, "name": "tulip (sleeve)",                   "taxonomy_id": "att000214_00"},
        {"id": 209, "name": "puff (sleeve)",                    "taxonomy_id": "att000215_00"},
        {"id": 210, "name": "bell (sleeve)",                    "taxonomy_id": "att000216_00"},
        {"id": 211, "name": "circular flounce (sleeve)",        "taxonomy_id": "att000217_00"},
        {"id": 212, "name": "poet (sleeve)",                    "taxonomy_id": "att000218_00"},
        {"id": 213, "name": "dolman (sleeve), batwing (sleeve)", "taxonomy_id": "combo000005"},
        {"id": 214, "name": "bishop (sleeve)",                  "taxonomy_id": "att000221_00"},
        {"id": 215, "name": "leg of mutton (sleeve)",           "taxonomy_id": "att000222_00"},
        {"id": 216, "name": "kimono (sleeve)",                  "taxonomy_id": "att000223_00"},
        # -- Pocket nicknames --
        {"id": 217, "name": "cargo (pocket)",                   "taxonomy_id": "att000224_00"},
        {"id": 218, "name": "patch (pocket)",                   "taxonomy_id": "att000225_00"},
        {"id": 219, "name": "welt (pocket)",                    "taxonomy_id": "att000226_00"},
        {"id": 220, "name": "kangaroo (pocket)",                "taxonomy_id": "att000227_00"},
        {"id": 221, "name": "seam (pocket)",                    "taxonomy_id": "att000228_00"},
        {"id": 222, "name": "slash (pocket)",                   "taxonomy_id": "att000229_00"},
        {"id": 223, "name": "curved (pocket)",                  "taxonomy_id": "att000230_00"},
        {"id": 224, "name": "flap (pocket)",                    "taxonomy_id": "att000231_00"},
    ],

    # -------------------------------------------------------------------------
    # SILHOUETTE (25 attributes)
    # Shape, fit, and overall garment silhouette
    # -------------------------------------------------------------------------
    "silhouette": [
        {"id": 114, "name": "asymmetrical",                    "taxonomy_id": "att000117_00"},
        {"id": 115, "name": "symmetrical",                     "taxonomy_id": "att000118_00"},
        {"id": 116, "name": "peplum",                          "taxonomy_id": "att000119_00"},
        {"id": 117, "name": "circle",                          "taxonomy_id": "att000120_00"},
        {"id": 118, "name": "flare",                           "taxonomy_id": "att000121_00"},
        {"id": 119, "name": "fit and flare",                   "taxonomy_id": "att000122_00"},
        {"id": 120, "name": "trumpet",                         "taxonomy_id": "att000123_00"},
        {"id": 121, "name": "mermaid",                         "taxonomy_id": "att000124_00"},
        {"id": 122, "name": "balloon",                         "taxonomy_id": "att000125_00"},
        {"id": 123, "name": "bell",                            "taxonomy_id": "att000126_00"},
        {"id": 124, "name": "bell bottom",                     "taxonomy_id": "att000127_00"},
        {"id": 125, "name": "bootcut",                         "taxonomy_id": "att000128_00"},
        {"id": 126, "name": "peg",                             "taxonomy_id": "att000129_00"},
        {"id": 127, "name": "pencil",                          "taxonomy_id": "att000130_00"},
        {"id": 128, "name": "straight",                        "taxonomy_id": "att000131_00"},
        {"id": 129, "name": "a-line",                          "taxonomy_id": "att000132_00"},
        {"id": 130, "name": "tent",                            "taxonomy_id": "att000133_00"},
        {"id": 131, "name": "baggy",                           "taxonomy_id": "att000134_00"},
        {"id": 132, "name": "wide leg",                        "taxonomy_id": "att000135_00"},
        {"id": 133, "name": "high low",                        "taxonomy_id": "att000136_00"},
        {"id": 134, "name": "curved (fit)",                    "taxonomy_id": "att000137_00"},
        {"id": 135, "name": "tight (fit)",                     "taxonomy_id": "att000138_00"},
        {"id": 136, "name": "regular (fit)",                   "taxonomy_id": "att000139_00"},
        {"id": 137, "name": "loose (fit)",                     "taxonomy_id": "att000140_00"},
        {"id": 138, "name": "oversized",                       "taxonomy_id": "att000141_00"},
    ],

    # -------------------------------------------------------------------------
    # WAISTLINE (7 attributes)
    # -------------------------------------------------------------------------
    "waistline": [
        {"id": 139, "name": "empire waistline",                "taxonomy_id": "att000143_00"},
        {"id": 140, "name": "dropped waistline",               "taxonomy_id": "att000144_00"},
        {"id": 141, "name": "high waist",                      "taxonomy_id": "att000145_00"},
        {"id": 142, "name": "normal waist",                    "taxonomy_id": "att000146_00"},
        {"id": 143, "name": "low waist",                       "taxonomy_id": "att000147_00"},
        {"id": 144, "name": "basque (wasitline)",              "taxonomy_id": "att000148_00"},
        {"id": 145, "name": "no waistline",                    "taxonomy_id": "att000149_00"},
    ],

    # -------------------------------------------------------------------------
    # LENGTH (15 attributes)
    # Garment and sleeve lengths
    # -------------------------------------------------------------------------
    "length": [
        # -- Garment length --
        {"id": 146, "name": "above-the-hip (length)",          "taxonomy_id": "att000151_00"},
        {"id": 147, "name": "hip (length)",                    "taxonomy_id": "att000152_00"},
        {"id": 148, "name": "micro (length)",                  "taxonomy_id": "att000153_00"},
        {"id": 149, "name": "mini (length)",                   "taxonomy_id": "att000154_00"},
        {"id": 150, "name": "above-the-knee (length)",         "taxonomy_id": "att000155_00"},
        {"id": 151, "name": "knee (length)",                   "taxonomy_id": "att000156_00"},
        {"id": 152, "name": "below the knee (length)",         "taxonomy_id": "att000157_00"},
        {"id": 153, "name": "midi",                            "taxonomy_id": "att000158_00"},
        {"id": 154, "name": "maxi (length)",                   "taxonomy_id": "att000159_00"},
        {"id": 155, "name": "floor (length)",                  "taxonomy_id": "att000160_00"},
        # -- Sleeve length --
        {"id": 156, "name": "sleeveless",                      "taxonomy_id": "att000161_00"},
        {"id": 157, "name": "short (length)",                  "taxonomy_id": "att000162_00"},
        {"id": 158, "name": "elbow-length",                    "taxonomy_id": "att000163_00"},
        {"id": 159, "name": "three quarter (length)",          "taxonomy_id": "att000164_00"},
        {"id": 160, "name": "wrist-length",                    "taxonomy_id": "att000165_00"},
    ],

    # -------------------------------------------------------------------------
    # NECKLINE TYPE (25 attributes)
    # -------------------------------------------------------------------------
    "neckline type": [
        {"id": 179, "name": "collarless",                      "taxonomy_id": "att000185_00"},
        {"id": 180, "name": "asymmetric (neckline)",           "taxonomy_id": "att000186_00"},
        {"id": 181, "name": "crew (neck)",                     "taxonomy_id": "att000187_00"},
        {"id": 182, "name": "round (neck)",                    "taxonomy_id": "att000188_00"},
        {"id": 183, "name": "v-neck",                          "taxonomy_id": "att000189_00"},
        {"id": 184, "name": "surplice (neck)",                 "taxonomy_id": "att000190_00"},
        {"id": 185, "name": "oval (neck)",                     "taxonomy_id": "att000191_00"},
        {"id": 186, "name": "u-neck",                          "taxonomy_id": "att000192_00"},
        {"id": 187, "name": "sweetheart (neckline)",           "taxonomy_id": "att000193_00"},
        {"id": 188, "name": "queen anne (neck)",               "taxonomy_id": "att000194_00"},
        {"id": 189, "name": "boat (neck)",                     "taxonomy_id": "att000195_00"},
        {"id": 190, "name": "scoop (neck)",                    "taxonomy_id": "att000196_00"},
        {"id": 191, "name": "square (neckline)",               "taxonomy_id": "att000197_00"},
        {"id": 192, "name": "plunging (neckline)",             "taxonomy_id": "att000198_00"},
        {"id": 193, "name": "keyhole (neck)",                  "taxonomy_id": "att000199_00"},
        {"id": 194, "name": "halter (neck)",                   "taxonomy_id": "att000200_00"},
        {"id": 195, "name": "crossover (neck)",                "taxonomy_id": "att000201_00"},
        {"id": 196, "name": "choker (neck)",                   "taxonomy_id": "att000202_00"},
        {"id": 197, "name": "high (neck)",                     "taxonomy_id": "att000203_00"},
        {"id": 198, "name": "turtle (neck)",                   "taxonomy_id": "att000204_00"},
        {"id": 199, "name": "cowl (neck)",                     "taxonomy_id": "att000205_00"},
        {"id": 200, "name": "straight across (neck)",          "taxonomy_id": "att000206_00"},
        {"id": 201, "name": "illusion (neck)",                 "taxonomy_id": "att000207_00"},
        {"id": 202, "name": "off-the-shoulder",                "taxonomy_id": "att000208_00"},
        {"id": 203, "name": "one shoulder",                    "taxonomy_id": "att000209_00"},
    ],

    # -------------------------------------------------------------------------
    # OPENING TYPE (10 attributes)
    # -------------------------------------------------------------------------
    "opening type": [
        {"id": 225, "name": "single breasted",                 "taxonomy_id": "att000233_00"},
        {"id": 226, "name": "double breasted",                 "taxonomy_id": "att000234_00"},
        {"id": 227, "name": "lace up",                         "taxonomy_id": "att000235_00"},
        {"id": 228, "name": "wrapping",                        "taxonomy_id": "att000236_00"},
        {"id": 229, "name": "zip-up",                          "taxonomy_id": "att000237_00"},
        {"id": 230, "name": "fly (opening)",                   "taxonomy_id": "att000238_00"},
        {"id": 231, "name": "chained (opening)",               "taxonomy_id": "att000239_00"},
        {"id": 232, "name": "buckled (opening)",               "taxonomy_id": "att000240_00"},
        {"id": 233, "name": "toggled (opening)",               "taxonomy_id": "att000241_00"},
        {"id": 234, "name": "no opening",                      "taxonomy_id": "att000242_00"},
    ],

    # -------------------------------------------------------------------------
    # TEXTILE PATTERN (24 attributes: 18 main + 6 animal sub-patterns)
    # -------------------------------------------------------------------------
    "textile pattern": [
        {"id": 317, "name": "plain (pattern)",                 "taxonomy_id": "att000338_00"},
        {"id": 318, "name": "abstract",                        "taxonomy_id": "att000339_00"},
        {"id": 319, "name": "cartoon",                         "taxonomy_id": "att000340_00"},
        {"id": 320, "name": "letters, numbers",                "taxonomy_id": "combo000009"},
        {"id": 321, "name": "camouflage",                      "taxonomy_id": "att000343_00"},
        {"id": 322, "name": "check",                           "taxonomy_id": "att000344_00"},
        {"id": 323, "name": "dot",                             "taxonomy_id": "att000345_00"},
        {"id": 324, "name": "fair isle",                       "taxonomy_id": "att000346_00"},
        {"id": 325, "name": "floral",                          "taxonomy_id": "att000347_00"},
        {"id": 326, "name": "geometric",                       "taxonomy_id": "att000348_00"},
        {"id": 327, "name": "paisley",                         "taxonomy_id": "att000349_00"},
        {"id": 328, "name": "stripe",                          "taxonomy_id": "att000350_00"},
        {"id": 329, "name": "houndstooth (pattern)",           "taxonomy_id": "att000351_00"},
        {"id": 330, "name": "herringbone (pattern)",           "taxonomy_id": "att000352_00"},
        {"id": 331, "name": "chevron",                         "taxonomy_id": "att000353_00"},
        {"id": 332, "name": "argyle",                          "taxonomy_id": "att000354_00"},
        {"id": 339, "name": "toile de jouy",                   "taxonomy_id": "att000362_00"},
        {"id": 340, "name": "plant",                           "taxonomy_id": "att000363_00"},
        # -- Animal sub-patterns (level 2, children of textile pattern) --
        {"id": 333, "name": "leopard",                         "taxonomy_id": "att000356_00", "parent_supercategory": "animal"},
        {"id": 334, "name": "snakeskin (pattern)",             "taxonomy_id": "att000357_00", "parent_supercategory": "animal"},
        {"id": 335, "name": "cheetah",                         "taxonomy_id": "att000358_00", "parent_supercategory": "animal"},
        {"id": 336, "name": "peacock",                         "taxonomy_id": "att000359_00", "parent_supercategory": "animal"},
        {"id": 337, "name": "zebra",                           "taxonomy_id": "att000360_00", "parent_supercategory": "animal"},
        {"id": 338, "name": "giraffe",                         "taxonomy_id": "att000361_00", "parent_supercategory": "animal"},
    ],

    # -------------------------------------------------------------------------
    # TEXTILE FINISHING / MANUFACTURING TECHNIQUES (21 attributes)
    # -------------------------------------------------------------------------
    "textile finishing, manufacturing techniques": [
        {"id": 296, "name": "burnout",                         "taxonomy_id": "att000316_00"},
        {"id": 297, "name": "distressed",                      "taxonomy_id": "att000317_00"},
        {"id": 298, "name": "washed",                          "taxonomy_id": "att000318_00"},
        {"id": 299, "name": "embossed",                        "taxonomy_id": "att000319_00"},
        {"id": 300, "name": "frayed",                          "taxonomy_id": "att000320_00"},
        {"id": 301, "name": "printed",                         "taxonomy_id": "att000321_00"},
        {"id": 302, "name": "ruched",                          "taxonomy_id": "att000322_00"},
        {"id": 303, "name": "quilted",                         "taxonomy_id": "att000323_00"},
        {"id": 304, "name": "pleat",                           "taxonomy_id": "att000324_00"},
        {"id": 305, "name": "gathering",                       "taxonomy_id": "att000325_00"},
        {"id": 306, "name": "smocking",                        "taxonomy_id": "att000326_00"},
        {"id": 307, "name": "tiered",                          "taxonomy_id": "att000327_00"},
        {"id": 308, "name": "cutout",                          "taxonomy_id": "att000328_00"},
        {"id": 309, "name": "slit",                            "taxonomy_id": "att000329_00"},
        {"id": 310, "name": "perforated",                      "taxonomy_id": "att000330_00"},
        {"id": 311, "name": "lining",                          "taxonomy_id": "att000331_00"},
        {"id": 312, "name": "applique(a)",                     "taxonomy_id": "att000332_00"},
        {"id": 313, "name": "bead(a)",                         "taxonomy_id": "att000333_00"},
        {"id": 314, "name": "rivet(a)",                        "taxonomy_id": "att000334_00"},
        {"id": 315, "name": "sequin(a)",                       "taxonomy_id": "att000335_00"},
        {"id": 316, "name": "no special manufacturing technique", "taxonomy_id": "att000336_00"},
    ],

    # -------------------------------------------------------------------------
    # NON-TEXTILE MATERIAL TYPE (14 attributes: 10 main + 4 leather sub-types)
    # -------------------------------------------------------------------------
    "non-textile material type": [
        {"id": 281, "name": "plastic",                         "taxonomy_id": "att000298_00"},
        {"id": 282, "name": "rubber",                          "taxonomy_id": "att000299_00"},
        {"id": 283, "name": "metal",                           "taxonomy_id": "att000300_00"},
        {"id": 285, "name": "feather",                         "taxonomy_id": "att000302_00"},
        {"id": 286, "name": "gem",                             "taxonomy_id": "att000303_00"},
        {"id": 287, "name": "bone",                            "taxonomy_id": "att000304_00"},
        {"id": 288, "name": "ivory",                           "taxonomy_id": "att000305_00"},
        {"id": 289, "name": "fur",                             "taxonomy_id": "att000306_00"},
        {"id": 294, "name": "wood",                            "taxonomy_id": "att000312_00"},
        {"id": 295, "name": "no non-textile material",         "taxonomy_id": "att000313_00"},
        # -- Leather sub-types (level 2, children of non-textile material) --
        {"id": 290, "name": "suede",                           "taxonomy_id": "att000308_00", "parent_supercategory": "leather"},
        {"id": 291, "name": "shearling",                       "taxonomy_id": "att000309_00", "parent_supercategory": "leather"},
        {"id": 292, "name": "crocodile",                       "taxonomy_id": "att000310_00", "parent_supercategory": "leather"},
        {"id": 293, "name": "snakeskin",                       "taxonomy_id": "att000311_00", "parent_supercategory": "leather"},
    ],
}


# =============================================================================
# FLAT LOOKUP DICTIONARIES
# For fast ID-based and name-based lookups
# =============================================================================

# Category ID -> category info
CATEGORY_BY_ID = {}
for supcat, cats in MAIN_APPAREL_CATEGORIES.items():
    for cat in cats:
        CATEGORY_BY_ID[cat["id"]] = {**cat, "supercategory": supcat, "type": "main_apparel"}
for part in ALL_APPAREL_PARTS:
    CATEGORY_BY_ID[part["id"]] = {**part, "type": "apparel_part"}

# Category name -> category ID (lowercase for matching)
CATEGORY_NAME_TO_ID = {}
for cat_id, cat_info in CATEGORY_BY_ID.items():
    # Add full name
    CATEGORY_NAME_TO_ID[cat_info["name"].lower()] = cat_id
    # Also add individual names for combo categories like "shirt, blouse"
    for name_part in cat_info["name"].split(", "):
        CATEGORY_NAME_TO_ID[name_part.strip().lower()] = cat_id

# Attribute ID -> attribute info
ATTRIBUTE_BY_ID = {}
for supcat, attrs in ATTRIBUTES_BY_SUPERCATEGORY.items():
    for attr in attrs:
        ATTRIBUTE_BY_ID[attr["id"]] = {**attr, "supercategory": supcat}

# Attribute name -> attribute ID (lowercase for matching)
ATTRIBUTE_NAME_TO_ID = {}
for attr_id, attr_info in ATTRIBUTE_BY_ID.items():
    ATTRIBUTE_NAME_TO_ID[attr_info["name"].lower()] = attr_id
    # Also strip parenthetical qualifiers: "cargo (pants)" -> "cargo"
    base_name = attr_info["name"].split(" (")[0].strip().lower()
    if base_name not in ATTRIBUTE_NAME_TO_ID:
        ATTRIBUTE_NAME_TO_ID[base_name] = attr_id


# =============================================================================
# SEMANTIC SUB-GROUPINGS OF NICKNAMES
# The official "nickname" supercategory (153 attrs) lumps together garment-type
# nicknames and part-type nicknames. This provides a semantic breakdown for
# easier use in search and enrichment pipelines.
# =============================================================================

NICKNAME_SUBGROUPS = {
    "shirt_top_nicknames": list(range(0, 16)),         # IDs 0-15
    "sweater_jacket_nicknames": list(range(16, 36)),   # IDs 16-35
    "pants_nicknames": list(range(36, 50)),             # IDs 36-49
    "shorts_nicknames": list(range(50, 62)),            # IDs 50-61
    "skirt_nicknames": list(range(62, 79)),             # IDs 62-78
    "coat_nicknames": list(range(79, 95)),              # IDs 79-94
    "dress_nicknames": list(range(95, 114)),            # IDs 95-113
    "collar_nicknames": list(range(161, 174)),          # IDs 161-173
    "lapel_nicknames": list(range(174, 179)),           # IDs 174-178
    "sleeve_nicknames": list(range(204, 217)),          # IDs 204-216
    "pocket_nicknames": list(range(217, 225)),          # IDs 217-224
}

# Which main category IDs can each nickname subgroup apply to
NICKNAME_TO_CATEGORY_MAPPING = {
    "shirt_top_nicknames":          [0, 1],        # shirt/blouse, top/t-shirt
    "sweater_jacket_nicknames":     [2, 3, 4, 5],  # sweater, cardigan, jacket, vest
    "pants_nicknames":              [6],            # pants
    "shorts_nicknames":             [7],            # shorts
    "skirt_nicknames":              [8],            # skirt
    "coat_nicknames":               [9],            # coat
    "dress_nicknames":              [10],           # dress
    "collar_nicknames":             [28],           # collar (part)
    "lapel_nicknames":              [29],           # lapel (part)
    "sleeve_nicknames":             [31],           # sleeve (part)
    "pocket_nicknames":             [32],           # pocket (part)
}


# =============================================================================
# BODY REGION SUPERCATEGORIES (for main apparel)
# =============================================================================

BODY_REGIONS = list(MAIN_APPAREL_CATEGORIES.keys())
# ['upperbody', 'lowerbody', 'wholebody', 'head', 'neck',
#  'arms and hands', 'waist', 'legs and feet', 'others']


# =============================================================================
# ATTRIBUTE SUPERCATEGORIES (canonical list)
# =============================================================================

ATTRIBUTE_SUPERCATEGORIES = list(ATTRIBUTES_BY_SUPERCATEGORY.keys())
# ['nickname', 'silhouette', 'waistline', 'length', 'neckline type',
#  'opening type', 'textile pattern', 'textile finishing, manufacturing techniques',
#  'non-textile material type']


# =============================================================================
# SUMMARY COUNTS
# =============================================================================

TAXONOMY_SUMMARY = {
    "main_apparel_categories": 27,
    "apparel_parts": {
        "garment_parts": 7,
        "closures": 2,
        "decorations": 10,
        "total": 19,
    },
    "total_object_categories": 46,
    "attributes": {
        "nickname": 153,
        "silhouette": 25,
        "neckline_type": 25,
        "textile_pattern": 24,  # 18 main + 6 animal sub-patterns
        "textile_finishing": 21,
        "length": 15,
        "non_textile_material_type": 14,  # 10 main + 4 leather sub-types
        "opening_type": 10,
        "waistline": 7,
        "total": 294,
    },
}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_category_name(category_id: int) -> str:
    """Get category name by ID."""
    if category_id in CATEGORY_BY_ID:
        return CATEGORY_BY_ID[category_id]["name"]
    return None


def get_attribute_name(attribute_id: int) -> str:
    """Get attribute name by ID."""
    if attribute_id in ATTRIBUTE_BY_ID:
        return ATTRIBUTE_BY_ID[attribute_id]["name"]
    return None


def get_attributes_for_supercategory(supercategory: str) -> list:
    """Get all attributes for a given super-category."""
    return ATTRIBUTES_BY_SUPERCATEGORY.get(supercategory, [])


def get_main_categories_for_region(region: str) -> list:
    """Get all main apparel categories for a body region."""
    return MAIN_APPAREL_CATEGORIES.get(region, [])


def search_attributes_by_name(query: str) -> list:
    """Search attributes by partial name match (case-insensitive)."""
    query_lower = query.lower()
    results = []
    for attr_id, attr_info in ATTRIBUTE_BY_ID.items():
        if query_lower in attr_info["name"].lower():
            results.append(attr_info)
    return results


def search_categories_by_name(query: str) -> list:
    """Search categories by partial name match (case-insensitive)."""
    query_lower = query.lower()
    results = []
    for cat_id, cat_info in CATEGORY_BY_ID.items():
        if query_lower in cat_info["name"].lower():
            results.append(cat_info)
    return results


def get_all_attribute_ids() -> list:
    """Get all 294 attribute IDs as a sorted list."""
    return sorted(ATTRIBUTE_BY_ID.keys())


def get_all_category_ids() -> list:
    """Get all 46 category IDs as a sorted list."""
    return sorted(CATEGORY_BY_ID.keys())
