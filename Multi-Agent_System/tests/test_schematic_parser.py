import pytest
import io
import struct
import gzip
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from utils.schematic_parser import SimpleNBT, SchematicParser

class TestSimpleNBT:
    """Test individual NBT tag parsing using BytesIO."""
    
    def test_read_byte(self):
        stream = io.BytesIO(b'\x05')
        assert SimpleNBT.read_byte(stream) == 5
        
        stream = io.BytesIO(b'\xff')
        assert SimpleNBT.read_byte(stream, signed=True) == -1

    def test_read_short(self):
        stream = io.BytesIO(struct.pack('>h', -123))
        assert SimpleNBT.read_short(stream) == -123

    def test_read_int(self):
        stream = io.BytesIO(struct.pack('>i', 123456))
        assert SimpleNBT.read_int(stream) == 123456

    def test_read_long(self):
        stream = io.BytesIO(struct.pack('>q', 1234567890123))
        assert SimpleNBT.read_long(stream) == 1234567890123
        
    def test_read_float_double(self):
        stream = io.BytesIO(struct.pack('>f', 3.14))
        assert abs(SimpleNBT.read_float(stream) - 3.14) < 0.001
        
        stream = io.BytesIO(struct.pack('>d', 3.14159))
        assert abs(SimpleNBT.read_double(stream) - 3.14159) < 0.00001
        
    def test_read_string(self):
        data = b'hello'
        stream = io.BytesIO(struct.pack('>H', len(data)) + data)
        assert SimpleNBT.read_string(stream) == "hello"

    def test_read_int_array(self):
        # [1, 2]
        stream = io.BytesIO(struct.pack('>i', 2) + struct.pack('>i', 1) + struct.pack('>i', 2))
        assert SimpleNBT.read_payload(stream, SimpleNBT.TAG_Int_Array) == [1, 2]

    def test_read_long_array(self):
        # [10, 20]
        stream = io.BytesIO(struct.pack('>i', 2) + struct.pack('>q', 10) + struct.pack('>q', 20))
        assert SimpleNBT.read_payload(stream, SimpleNBT.TAG_Long_Array) == [10, 20]

    def test_read_list(self):
        # List of Bytes [10, 20]
        payload = (
            struct.pack('b', 1) + # Type Byte
            struct.pack('>i', 2) + # Length 2
            struct.pack('b', 10) + 
            struct.pack('b', 20)
        )
        stream = io.BytesIO(payload)
        # We call read_payload for TAG_List directly? No, parse calls it based on tag
        # Let's call read_payload manually
        assert SimpleNBT.read_payload(stream, SimpleNBT.TAG_List) == [10, 20]


class TestSchematicParser:

    @patch("utils.schematic_parser.gzip.open")
    def test_load_error(self, mock_gzip):
        mock_gzip.side_effect = Exception("File not found")
        parser = SchematicParser("dummy.schem")
        assert parser.data == {}

    def test_decode_block_data(self):
        # VarInt encoding check
        # 127 -> 0x7F
        # 128 -> 0x80, 0x01
        
        # Test 128 (encoded as 0x80, 0x01)
        parser = SchematicParser("dummy")
        # Bypass load
        parser.data = {}
        
        byte_array = b'\x80\x01' 
        decoded = parser.decode_block_data(byte_array)
        assert decoded == [128]

        # Test [1, 2] -> 0x01, 0x02
        decoded = parser.decode_block_data(b'\x01\x02')
        assert decoded == [1, 2]

    def test_get_blocks_and_bom(self):
        parser = SchematicParser("dummy")
        
        # Mock data structure representing a 1x1x1 schematic
        parser.data = {
            "Width": 1,
            "Height": 1,
            "Length": 1,
            "Palette": {"minecraft:stone": 0, "minecraft:dirt": 1},
            # Encoded BlockData: Index 0 (stone) -> 0x00
            "BlockData": b'\x00' 
        }
        # Re-parse dims
        parser._parse_dimensions()
        
        # Test get_blocks
        blocks = parser.get_blocks()
        assert len(blocks) == 1
        assert blocks[0]['block'] == "minecraft:stone"
        
        # Test BOM
        bom = parser.get_bom()
        assert bom["stone"] == 1

        # Test Cache
        assert parser.get_blocks() == blocks
        
    def test_get_blocks_nested_format(self):
        parser = SchematicParser("dummy")
        parser.data = {
            "Schematic": {
                "Width": 1, "Height": 1, "Length": 1,
                "Blocks": {
                    "Palette": {"minecraft:dirt": 5},
                    "Data": b'\x05' # Index 5
                }
            }
        }
        parser._parse_dimensions()
        blocks = parser.get_blocks()
        assert len(blocks) == 1
        assert blocks[0]['block'] == "minecraft:dirt"
