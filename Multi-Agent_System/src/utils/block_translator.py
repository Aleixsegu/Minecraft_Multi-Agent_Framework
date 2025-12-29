
def get_block_id(raw_name: str) -> int:
    """
    Translates a Minecraft block name (e.g. 'minecraft:stone', 'minecraft:oak_stairs[facing=east]')
    to a numeric block ID compatible with MCPI/RaspberryJuice (Legacy IDs).
    """
    
    # 1. Sanitize name: remove 'minecraft:' prefix and '[properties]' suffix
    raw_name = raw_name.lower()
    
    if "[" in raw_name:
        base_name = raw_name.split("[")[0]
    else:
        base_name = raw_name
        
    if ":" in base_name:
        base_name = base_name.split(":")[1]
        
    # 2. Lookup in Dictionary
    # MCPI uses legacy numeric IDs.
    
    # Direct mappings for exact matches
    mapping = {
        "air": 0,
        "cave_air": 0,
        "void_air": 0,
        "structure_void": 0,
        
        "stone": 1,
        "granite": 1,
        "polished_granite": 1,
        "diorite": 1,
        "polished_diorite": 1,
        "andesite": 1,
        "polished_andesite": 1,
        
        "grass_block": 2,
        "grass": 2, # sometimes called just grass
        
        "dirt": 3,
        "coarse_dirt": 3,
        "podzol": 3,
        
        "cobblestone": 4,
        
        "oak_planks": 5,
        "spruce_planks": 5,
        "birch_planks": 5,
        "jungle_planks": 5,
        "acacia_planks": 5,
        "dark_oak_planks": 5,
        "planks": 5,
        
        "sapling": 6,
        "oak_sapling": 6,
        "spruce_sapling": 6,
        
        "bedrock": 7,
        
        "flowing_water": 8,
        "water": 9, # Stationary water
        
        "flowing_lava": 10,
        "lava": 11,
        
        "sand": 12,
        "red_sand": 12,
        
        "gravel": 13,
        
        "gold_ore": 14,
        "iron_ore": 15,
        "coal_ore": 16,
        
        "oak_log": 17,
        "spruce_log": 17,
        "birch_log": 17,
        "jungle_log": 17,
        "log": 17,
        
        "oak_leaves": 18,
        "spruce_leaves": 18,
        "leaves": 18,
        
        "sponge": 19,
        "glass": 20,
        "lapis_ore": 21,
        "lapis_block": 22,
        "dispenser": 23,
        "sandstone": 24,
        "note_block": 25,
        "bed": 26, # bed block
        "white_bed": 26,
        
        "powered_rail": 27,
        "detector_rail": 28,
        "sticky_piston": 29,
        "cobweb": 30,
        "web": 30,
        "grass_path": 2, # fallback to grass
        "dead_bush": 32,
        "piston": 33,
        "piston_head": 34,
        
        "white_wool": 35,
        "orange_wool": 35,
        "magenta_wool": 35,
        "light_blue_wool": 35,
        "yellow_wool": 35,
        "lime_wool": 35,
        "pink_wool": 35,
        "gray_wool": 35,
        "light_gray_wool": 35,
        "cyan_wool": 35,
        "purple_wool": 35,
        "blue_wool": 35,
        "brown_wool": 35,
        "green_wool": 35,
        "red_wool": 35,
        "black_wool": 35,
        "wool": 35,
        
        "dandelion": 37,
        "poppy": 38,
        "blue_orchid": 38,
        "allium": 38,
        "azure_bluet": 38,
        "red_tulip": 38,
        "orange_tulip": 38,
        "white_tulip": 38,
        "pink_tulip": 38,
        "oxeye_daisy": 38,
        
        "brown_mushroom": 39,
        "red_mushroom": 40,
        "gold_block": 41,
        "iron_block": 42,
        
        "stone_slab": 44,
        "smooth_stone_slab": 44,
        "cobblestone_slab": 44, # Mapped to generic slab
        
        "bricks": 45,
        "tnt": 46,
        "bookshelf": 47,
        "mossy_cobblestone": 48,
        "obsidian": 49,
        "torch": 50,
        "wall_torch": 50,
        "fire": 51,
        "spawner": 52,
        "oak_stairs": 53,
        "chest": 54,
        "redstone_wire": 55,
        "diamond_ore": 56,
        "diamond_block": 57,
        "crafting_table": 58,
        "wheat": 59,
        "farmland": 60,
        "furnace": 61,
        "lit_furnace": 62,
        "standing_sign": 63,
        "oak_door": 64,
        "ladder": 65,
        "rail": 66,
        "stone_stairs": 67,
        "cobblestone_stairs": 67,
        "wall_sign": 68,
        "lever": 69,
        "stone_pressure_plate": 70,
        "iron_door": 71,
        "oak_pressure_plate": 72,
        "redstone_ore": 73,
        "lit_redstone_ore": 74,
        "unlit_redstone_torch": 75,
        "redstone_torch": 76,
        "redstone_wall_torch": 76,
        "stone_button": 77,
        "snow_layer": 78,
        "ice": 79,
        "snow_block": 80,
        "cactus": 81,
        "clay": 82,
        "sugar_cane": 83,
        "jukebox": 84,
        "oak_fence": 85,
        "pumpkin": 86,
        "netherrack": 87,
        "soul_sand": 88,
        "glowstone": 89,
        "portal": 90,
        "jack_o_lantern": 91,
        "cake": 92,
        "repeater": 93,
        "skeleton_skull": 144, # approximate
        
        "stained_glass": 95,
        "white_stained_glass": 95,
        
        "trapdoor": 96,
        "oak_trapdoor": 96,
        "spruce_trapdoor": 96,
        
        "stone_bricks": 98,
        "mossy_stone_bricks": 98,
        "cracked_stone_bricks": 98,
        "chiseled_stone_bricks": 98,
        
        "iron_bars": 101,
        "glass_pane": 102,
        "melon": 103,
        "pumpkin_stem": 104,
        "melon_stem": 105,
        "vine": 106,
        "oak_fence_gate": 107,
        "brick_stairs": 108,
        "stone_brick_stairs": 109,
        "mycelium": 110,
        "lily_pad": 111,
        "nether_brick": 112,
        "nether_bricks": 112, # Plural variant
        "nether_brick_fence": 113,
        "nether_brick_stairs": 114,
        "nether_wart": 115,
        "enchanting_table": 116,
        "brewing_stand": 117,
        "cauldron": 118,
        "end_portal": 119,
        "end_portal_frame": 120,
        "end_stone": 121,
        "dragon_egg": 122,
        "redstone_lamp": 123,
        "lit_redstone_lamp": 124,
        
        "wooden_slab": 126,
        "oak_slab": 126,
        "spruce_slab": 126,
        "birch_slab": 126,
        
        "cocoa": 127,
        "sandstone_stairs": 128,
        "emerald_ore": 129,
        "ender_chest": 130,
        "tripwire_hook": 131,
        "tripwire": 132,
        "emerald_block": 133,
        "spruce_stairs": 134,
        "birch_stairs": 135,
        "jungle_stairs": 136,
        "command_block": 137,
        "beacon": 138,
        "cobblestone_wall": 139,
        "flower_pot": 140,
        "carrots": 141,
        "potatoes": 142,
        "wooden_button": 143,
        "anvil": 145,
        "trapped_chest": 146,
        "light_weighted_pressure_plate": 147,
        "heavy_weighted_pressure_plate": 148,
        "redstone_block": 152,
        "nether_quartz_ore": 153,
        "hopper": 154,
        "quartz_block": 155,
        "quartz_stairs": 156,
        "activator_rail": 157,
        "dropper": 158,
        "stained_hardened_clay": 159,
        "white_terracotta": 159,
        "orange_terracotta": 159,
        
        "stained_glass_pane": 160,
        
        "acacia_leaves": 161,
        "dark_oak_leaves": 161,
        "acacia_log": 162,
        "dark_oak_log": 162,
        "acacia_stairs": 163,
        "dark_oak_stairs": 164,
        "slime_block": 165,
        "barrier": 166,
        "iron_trapdoor": 167,
        "prismarine": 168,
        "sea_lantern": 169,
        "hay_block": 170,
        "carpet": 171,
        "white_carpet": 171,
        "hardened_clay": 172,
        "terracotta": 172,
        "coal_block": 173,
        "packed_ice": 174,
        "double_plant": 175,
        "sunflower": 175,
        "lilac": 175,
        "tall_grass": 175,
        "large_fern": 175,
        "rose_bush": 175,
        "peony": 175,
        
        "standing_banner": 176,
        "wall_banner": 177,
        "daylight_detector": 178,
        "red_sandstone": 179,
        "red_sandstone_stairs": 180,
        "double_stone_slab2": 181,
        "stone_slab2": 182,
        "spruce_fence_gate": 183,
        "birch_fence_gate": 184,
        "jungle_fence_gate": 185,
        "dark_oak_fence_gate": 186,
        "acacia_fence_gate": 187,
        "spruce_fence": 188,
        "birch_fence": 189,
        "jungle_fence": 190,
        "dark_oak_fence": 191,
        "acacia_fence": 192,
        "spruce_door": 193,
        "birch_door": 194,
        "jungle_door": 195,
        "acacia_door": 196,
        "dark_oak_door": 197,
        "end_rod": 198,
        "chorus_plant": 199,
        "chorus_flower": 200,
        "purpur_block": 201,
        "purpur_pillar": 202,
        "purpur_stairs": 203,
        "purpur_double_slab": 204,
        "purpur_slab": 205,
        "end_stone_bricks": 206,
        "beetroots": 207,
        "grass_path": 208,
        "end_gateway": 209,
        "repeating_command_block": 210,
        "chain_command_block": 211,
        "frosted_ice": 212,
        "magma_block": 213,
        "nether_wart_block": 214,
        "red_nether_brick": 215,
        "red_nether_bricks": 215,
        "bone_block": 216,
        "structure_void": 217,
        "observer": 218,
        "white_shulker_box": 219,
        "orange_shulker_box": 220,
        "magenta_shulker_box": 221,
        "light_blue_shulker_box": 222,
        "yellow_shulker_box": 223,
        "lime_shulker_box": 224,
        "pink_shulker_box": 225,
        "gray_shulker_box": 226,
        "light_gray_shulker_box": 227,
        "cyan_shulker_box": 228,
        "purple_shulker_box": 229,
        "blue_shulker_box": 230,
        "brown_shulker_box": 231,
        "green_shulker_box": 232,
        "red_shulker_box": 233,
        "black_shulker_box": 234,
        "white_glazed_terracotta": 235,
        "orange_glazed_terracotta": 236,
        "magenta_glazed_terracotta": 237,
        "light_blue_glazed_terracotta": 238,
        "yellow_glazed_terracotta": 239,
        "lime_glazed_terracotta": 240,
        "pink_glazed_terracotta": 241,
        "gray_glazed_terracotta": 242,
        "light_gray_glazed_terracotta": 243,
        "cyan_glazed_terracotta": 244,
        "purple_glazed_terracotta": 245,
        "blue_glazed_terracotta": 246,
        "brown_glazed_terracotta": 247,
        "green_glazed_terracotta": 248,
        "red_glazed_terracotta": 249,
        "concrete": 251,
        "concrete_powder": 252,
        
        # --- Explicit Variants & Plurals (User Request) ---
        "stone_brick_slab": 44,
        "brick_slab": 44,
        "nether_brick_slab": 44,
        "quartz_slab": 44,
        "sandstone_slab": 44,
        "cobblestone_slab": 44,
        "purpur_slab": 205,
        "prismarine_slab": 44, # Fallback
        "dark_prismarine_slab": 44, 
        
        "granite": 1,
        "andesite": 1,
        "diorite": 1,
        "granite_slab": 44,
        "andesite_slab": 44,
        "diorite_slab": 44,
        "granite_stairs": 67, # Fallback to stone stairs
        "andesite_stairs": 67,
        "diorite_stairs": 67,
        
        "mossy_cobblestone_wall": 139,
        "brick_wall": 139,
        "prismarine_wall": 139,
        "red_sandstone_wall": 139,
        "mossy_stone_brick_wall": 139,
        "granite_wall": 139,
        "andesite_wall": 139,
        "diorite_wall": 139,
        "nether_brick_wall": 139,
        "end_stone_brick_wall": 139,
        
        "oak_fence_gate": 107,
        "spruce_fence_gate": 183,
        "birch_fence_gate": 184,
        "jungle_fence_gate": 185,
        "dark_oak_fence_gate": 186,
        "acacia_fence_gate": 187,
        
        # Plurals / Aliases
        "fences": 85,
        "fence_gate": 107,
        "fence_gates": 107,
        "gates": 107,
        "wooden_stairs": 53,
        "stone_stairs": 67,
        "bricks_block": 45,
        "leaves": 18,
        "leaf": 18,
        "logs": 17,
        "wood_slab": 126,
        "wood_slabs": 126,
        "stone_slabs": 44,
        "signs": 63,
        "ladders": 65,
        "rails": 66,
        "torches": 50,
        "chests": 54,
    }

    if base_name in mapping:
        return mapping[base_name]

    # Partial / keyword analysis fallback for safety
    if "stairs" in base_name:
        return 67 # Cobble stairs generic
    if "slab" in base_name:
        return 44 # Stone slab generic (safe default)
    if "planks" in base_name or "plank" in base_name:
        return 5
    if "log" in base_name:
        return 17
    if "leaves" in base_name or "leaf" in base_name:
        return 18
    if "glass" in base_name:
        return 20
    if "fence" in base_name:
        return 85
    if "gate" in base_name:
        return 107
    if "wall" in base_name:
        return 139 # Cobble wall generic
    if "door" in base_name:
        return 64
    if "bed" in base_name:
        return 26
    
    # User Default Request: Emerald Block for unknown
    return 133 
