from strategies.mining_strategy import MiningStrategy
from typing import Dict, Any
import asyncio
import mcpi.block as block
from mcpi.minecraft import Minecraft
from utils.logging import Logger

class VerticalStrategy(MiningStrategy):
    """
    Estrategia Concreta: Drilla verticalmente hacia abajo para extraer recursos
    a profundidades crecientes.
    """
    
    def __init__(self, mc: Minecraft, logger: Logger, agent_id: str):
        super().__init__(mc, logger, agent_id)
        self.current_depth = 0
        self.max_depth = 60 # Drilla hasta 60 bloques hacia abajo (o hasta bedrock)
        self.bedrock_hit = False

    async def mine(self, target_bom: Dict[int, int], current_inventory: Dict[int, int], start_pos: Dict[str, int]) -> bool:
        """
        Ejecuta la minería vertical (hacia abajo).
        """
        if self.current_depth >= self.max_depth or self.bedrock_hit:
            self.logger.info(f"VerticalStrategy: Fin de minería vertical (Prof: {self.current_depth}, Bedrock: {self.bedrock_hit}).")
            return False

        # Posición objetivo
        target_x = start_pos['x']
        target_y = start_pos['y'] - self.current_depth
        target_z = start_pos['z']

        try:
            # Identificar bloque
            b_id = self.mc.getBlock(target_x, target_y, target_z)
            
            # Chequear Bedrock (indestructible)
            if b_id == block.BEDROCK.id:
                self.logger.info("VerticalStrategy: Bedrock alcanzada.")
                self.bedrock_hit = True
                return False

            # Minar si no es aire
            if b_id != block.AIR.id:
                self.mc.setBlock(target_x, target_y, target_z, block.AIR.id)
                current_inventory[b_id] = current_inventory.get(b_id, 0) + 1
                # self.logger.debug(f"VerticalStrategy: Bloque {b_id} extraído a profundidad {self.current_depth}.")
            
        except Exception as e:
            self.logger.error(f"Error en VerticalStrategy ({target_x}, {target_y}, {target_z}): {e}")
            return False

        # Avanzar profundidad
        self.current_depth += 1
        await asyncio.sleep(0.05)
        
        return True
