
import gzip
import struct
import os

class SimpleNBT:
    # Tag Constants
    TAG_End = 0
    TAG_Byte = 1
    TAG_Short = 2
    TAG_Int = 3
    TAG_Long = 4
    TAG_Float = 5
    TAG_Double = 6
    TAG_Byte_Array = 7
    TAG_String = 8
    TAG_List = 9
    TAG_Compound = 10
    TAG_Int_Array = 11
    TAG_Long_Array = 12

    @staticmethod
    def parse(stream):
        # Read Root Tag (Type + Name + Payload)
        tag_type = SimpleNBT.read_byte(stream)
        if tag_type == SimpleNBT.TAG_End:
            return None
        _ = SimpleNBT.read_string(stream) # Name is usually empty for root or irrelevant
        payload = SimpleNBT.read_payload(stream, tag_type)
        return payload

    @staticmethod
    def read_payload(stream, tag_type):
        if tag_type == SimpleNBT.TAG_Byte:
            return SimpleNBT.read_byte(stream, signed=True)
        elif tag_type == SimpleNBT.TAG_Short:
            return SimpleNBT.read_short(stream)
        elif tag_type == SimpleNBT.TAG_Int:
            return SimpleNBT.read_int(stream)
        elif tag_type == SimpleNBT.TAG_Long:
            return SimpleNBT.read_long(stream)
        elif tag_type == SimpleNBT.TAG_Float:
            return SimpleNBT.read_float(stream)
        elif tag_type == SimpleNBT.TAG_Double:
            return SimpleNBT.read_double(stream)
        elif tag_type == SimpleNBT.TAG_Byte_Array:
            length = SimpleNBT.read_int(stream)
            return stream.read(length)
        elif tag_type == SimpleNBT.TAG_String:
            return SimpleNBT.read_string(stream)
        elif tag_type == SimpleNBT.TAG_List:
            elem_type = SimpleNBT.read_byte(stream)
            length = SimpleNBT.read_int(stream)
            return [SimpleNBT.read_payload(stream, elem_type) for _ in range(length)]
        elif tag_type == SimpleNBT.TAG_Compound:
            compound = {}
            while True:
                child_type = SimpleNBT.read_byte(stream)
                if child_type == SimpleNBT.TAG_End:
                    break
                child_name = SimpleNBT.read_string(stream)
                child_payload = SimpleNBT.read_payload(stream, child_type)
                compound[child_name] = child_payload
            return compound
        elif tag_type == SimpleNBT.TAG_Int_Array:
            length = SimpleNBT.read_int(stream)
            return [SimpleNBT.read_int(stream) for _ in range(length)]
        elif tag_type == SimpleNBT.TAG_Long_Array:
            length = SimpleNBT.read_int(stream)
            return [SimpleNBT.read_long(stream) for _ in range(length)]
        else:
            raise ValueError(f"Unknown tag type: {tag_type}")

    @staticmethod
    def read_byte(stream, signed=False):
        b = stream.read(1)
        if not b: return 0 
        val = b[0]
        if signed and val > 127: val -= 256
        return val

    @staticmethod
    def read_short(stream):
        return struct.unpack('>h', stream.read(2))[0]

    @staticmethod
    def read_int(stream):
        return struct.unpack('>i', stream.read(4))[0]

    @staticmethod
    def read_long(stream):
        return struct.unpack('>q', stream.read(8))[0]

    @staticmethod
    def read_float(stream):
        return struct.unpack('>f', stream.read(4))[0]

    @staticmethod
    def read_double(stream):
        return struct.unpack('>d', stream.read(8))[0]

    @staticmethod
    def read_string(stream):
        length = struct.unpack('>H', stream.read(2))[0]
        return stream.read(length).decode('utf-8')

class SchematicParser:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = self._load()
        self.blocks_cache = None
        
        # Dimensions
        self.width = 0
        self.height = 0
        self.length = 0
        self._parse_dimensions()

    def _load(self):
        try:
            with gzip.open(self.filepath, 'rb') as f:
                return SimpleNBT.parse(f)
        except Exception as e:
            print(f"Error loading {self.filepath}: {e}")
            return {}

    def _parse_dimensions(self):
        root = self.data
        if 'Schematic' in root:
            root = root['Schematic']
            
        self.width = root.get('Width', 0)
        self.height = root.get('Height', 0)
        self.length = root.get('Length', 0)

    def decode_block_data(self, byte_array):
        data = []
        i = 0
        length = len(byte_array)
        while i < length:
            val = 0
            shift = 0
            while True:
                if i >= length: break
                byte = byte_array[i]
                i += 1
                val |= (byte & 0x7F) << shift
                if not (byte & 0x80):
                    break
                shift += 7
            data.append(val)
        return data

    def get_blocks(self):
        if self.blocks_cache is not None:
            return self.blocks_cache

        root = self.data
        # Unwrap Schematic if present
        if 'Schematic' in root:
            root = root['Schematic']

        # Use stored dimensions
        width = self.width
        height = self.height
        length = self.length

        # Handle different structures
        palette = {}
        block_data_bytes = b''

        # Case 1: Nested Blocks compound (e.g. WorldEdit/Sponge v3?)
        if 'Blocks' in root and isinstance(root['Blocks'], dict):
            blocks_compound = root['Blocks']
            palette = blocks_compound.get('Palette', {})
            block_data_bytes = blocks_compound.get('Data', b'')
        # Case 2: Flattened (Sponge v1/v2)
        else:
            palette = root.get('Palette', {})
            block_data_bytes = root.get('BlockData', b'')

        
        id_to_name = {v: k for k, v in palette.items()}
        block_indices = self.decode_block_data(block_data_bytes)
        
        blocks = []
        # Sponge schematics order: (y * length + z) * width + x
        idx = 0
        for y in range(height):
            for z in range(length):
                for x in range(width):
                    if idx < len(block_indices):
                        block_id = block_indices[idx]
                        block_name = id_to_name.get(block_id, "minecraft:air")
                        if block_name != "minecraft:air":
                            blocks.append({
                                'x': x,
                                'y': y,
                                'z': z,
                                'block': block_name
                            })
                        idx += 1
        self.blocks_cache = blocks
        return blocks

    def get_bom(self):
        blocks = self.get_blocks()
        bom = {}
        for b in blocks:
            # Clean up block name (remove minecraft: prefix and properties like [facing=...])
            full_name = b['block']
            name = full_name.split('[')[0].replace('minecraft:', '')
            
            bom[name] = bom.get(name, 0) + 1
        return bom
