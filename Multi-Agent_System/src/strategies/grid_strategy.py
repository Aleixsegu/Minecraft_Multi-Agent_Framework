from strategies.mining_strategy import MiningStrategy
from typing import Dict, Any
import asyncio
import mcpi.block as block
from utils.logging import Logger
from mcpi.minecraft import Minecraft

class GridStrategy(MiningStrategy):
    """
    Estrategia Concreta: Explora una región cúbica siguiendo un patrón de cuadrícula
    para una cobertura uniforme.
    """
    
    def __init__(self, mc: Minecraft, logger: Logger, agent_id: str):
        super().__init__(mc, logger, agent_id)
        self.width = 5
        self.length = 5
        self.height = 5
        
        self.current_x = 0
        self.current_y = 0
        self.current_z = 0

    async def mine(self, target_bom: Dict[int, int], current_inventory: Dict[int, int], start_pos: Dict[str, int]) -> bool:
        """
        Ejecuta el algoritmo de minería por cuadrícula.
        """
        if self.current_y >= self.height:
            self.logger.info(f"GridStrategy completada en la región.")
            return False

        # Calcular posición absoluta
        target_x = start_pos['x'] + self.current_x
        target_y = start_pos['y'] - self.current_y
        target_z = start_pos['z'] + self.current_z

        # Minería Real
        try:
            # 1. Identificar el bloque antes de picarlo
            block_id = self.mc.getBlock(target_x, target_y, target_z)

            # 2. Si no es aire, lo picamos y lo añadimos al inventario
            if block_id != block.AIR.id:
                self.mc.setBlock(target_x, target_y, target_z, block.AIR.id)
                current_inventory[block_id] = current_inventory.get(block_id, 0) + 1
                self.logger.info(f"Bloque recolectado: ID {block_id} en ({target_x}, {target_y}, {target_z})")
            else:
                 self.logger.debug(f"Bloque de aire encontrado en ({target_x}, {target_y}, {target_z}), ignorando.")
            
        except Exception as e:
            self.logger.error(f"Error minando en ({target_x}, {target_y}, {target_z}): {e}")

        # Avanzar índices
        self.current_x += 1
        if self.current_x >= self.width:
            self.current_x = 0
            self.current_z += 1
            if self.current_z >= self.length:
                self.current_z = 0
                self.current_y += 1
        
        await asyncio.sleep(0.05)
        return True
