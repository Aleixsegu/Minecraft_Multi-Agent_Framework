from strategies.mining_strategy import MiningStrategy
from typing import Dict, Any
import asyncio
import mcpi.block as block
from mcpi.minecraft import Minecraft
from utils.logging import Logger

class VerticalStrategy(MiningStrategy):
    """
    Estrategia Vertical con DIAGNÓSTICO (Chat Debug).
    """
    
    def __init__(self, mc: Minecraft, logger: Logger, agent_id: str):
        super().__init__(mc, logger, agent_id)
        self.current_depth = 0
        self.max_depth = 60
        self.bedrock_hit = False

    async def mine(self, target_bom: Dict[int, int], current_inventory: Dict[int, int], start_pos: Dict[str, int]) -> bool:
        """
        Ejecuta minería vertical con mensajes de depuración en el chat.
        """
        if self.current_depth >= self.max_depth or self.bedrock_hit:
            return False

        # 1. Asegurar Coordenadas Enteras (Crucial para mcpi)
        start_x = int(start_pos['x'])
        start_y = int(start_pos['y'])
        start_z = int(start_pos['z'])

        target_x = start_x
        target_y = start_y - self.current_depth
        target_z = start_z

        try:
            # 2. Leer bloque
            b_id = self.mc.getBlock(target_x, target_y, target_z)
            
            # --- DEBUG EN CHAT (Para que veas qué pasa) ---
            # Solo mostramos mensaje cada 5 bloques o si encuentra algo interesante, para no saturar demasiado
            # o si es el primer bloque (depth 0)
            if self.current_depth == 0 or b_id != 0:
                pass # self.mc.postToChat(f"[DEBUG] Prof: {self.current_depth} | En ({target_x},{target_y},{target_z}) veo ID: {b_id}")

            # 3. Chequear Bedrock
            if b_id == block.BEDROCK.id:
                self.mc.postToChat(f"[DEBUG] Bedrock alcanzada en prof {self.current_depth}. Parando.")
                self.bedrock_hit = True
                return False

            # 4. Minar (Si no es aire)
            if b_id != block.AIR.id:
                # Poner AIRE explícitamente
                self.mc.setBlock(target_x, target_y, target_z, block.AIR.id)
                
                # Añadir al inventario
                current_inventory[b_id] = current_inventory.get(b_id, 0) + 1
                
                # Feedback visual
                pass # self.mc.postToChat(f"[MINADO] ID {b_id} eliminado!")
            
        except Exception as e:
            self.logger.error(f"Error en VerticalStrategy: {e}")
            self.mc.postToChat(f"[ERROR] Fallo al minar: {e}")
            return False

        # Avanzar profundidad
        self.current_depth += 1
        
        # Pausa pequeña para que veas el proceso
        await asyncio.sleep(0.5) 
        
        return True