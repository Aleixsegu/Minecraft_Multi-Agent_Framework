import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from utils.block_translator import get_block_id, get_block_name

class TestBlockTranslator:

    def test_get_block_id_simple(self):
        """Test simple lookups."""
        assert get_block_id("stone") == 1
        assert get_block_id("air") == 0

    def test_get_block_id_with_namespace(self):
        """Test parsing strings with 'minecraft:' prefix."""
        assert get_block_id("minecraft:stone") == 1
        assert get_block_id("minecraft:dirt") == 3

    def test_get_block_id_with_properties(self):
        """Test parsing strings with block states/properties."""
        assert get_block_id("oak_stairs[facing=east]") == 53
        assert get_block_id("minecraft:grass_block[snowy=true]") == 2

    def test_get_block_id_fallbacks(self):
        """Test partial match fallbacks for unknown blocks."""
        assert get_block_id("unknown_stairs") == 67
        assert get_block_id("weird_slab") == 44
        assert get_block_id("mystery_planks") == 5
        assert get_block_id("super_log") == 17
        assert get_block_id("strange_leaves") == 18
        assert get_block_id("blue_glass_thing") == 20
        assert get_block_id("big_fence") == 85
        assert get_block_id("small_gate") == 107
        assert get_block_id("tall_wall") == 139
        assert get_block_id("red_door") == 64
        assert get_block_id("soft_bed") == 26

    def test_get_block_id_unknown_default(self):
        """Test completely unknown block returns default (Emerald Block)."""
        assert get_block_id("completely_random_string_xyz") == 133

    def test_get_block_name_found(self):
        """Test reverse lookup for known ID."""
        name = get_block_name(1)
        # Puede ser stone, granite, etc. (varios mapean a 1), pero debe ser válido
        assert name in ["stone", "granite", "polished_granite", "diorite", "polished_diorite", "andesite", "polished_andesite"]

    def test_get_block_name_not_found(self):
        """Test reverse lookup for unknown ID."""
        assert get_block_name(999999) == "unknown"
