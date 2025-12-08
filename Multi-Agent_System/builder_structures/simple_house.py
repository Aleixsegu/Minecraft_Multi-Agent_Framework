
class SimpleHouse:
    """
    Estructura de ejemplo para probar el BuilderBot.
    Define una casa simple 5x5.
    """
    def __init__(self):
        pass

    def get_bom(self):
        """
        Devuelve la lista de materiales necesarios.
        Formato: { "material_name": quantity, ... }
        """
        return {
            "cobblestone": 64,
            "planks": 32,
            "glass": 8
        }
        
    def build(self, mc, origin_x, origin_y, origin_z):
        """
        Construye la estructura en la posición dada.
        """
        # Aquí iría la lógica de construcción (mc.setBlock, etc.)
        pass
