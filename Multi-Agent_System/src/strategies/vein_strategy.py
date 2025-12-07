from strategies.mining_strategy import MiningStrategy
from typing import Dict, Any, List, Tuple, Set
import asyncio
import mcpi.block as block
from mcpi.minecraft import Minecraft
from utils.logging import Logger

class VeinStrategy(MiningStrategy):
    """
    Estrategia Concreta: Detects clusters of identical materials (veins) and recursively mines
    adjacent blocks to maximize yield.
    """

    def __init__(self, mc: Minecraft, logger: Logger, agent_id: str):
        super().__init__(mc, logger, agent_id)
        self.queue: List[Tuple[int, int, int]] = []
        self.visited: Set[Tuple[int, int, int]] = set()
        self.target_id: int = None
        self.searching = True # Fase de búsqueda inicial
        
    async def mine(self, target_bom: Dict[int, int], current_inventory: Dict[int, int], start_pos: Dict[str, int]) -> bool:
        """
        Ejecuta el algoritmo de exploración de vetas (Vein Mining).
        """
        if self.searching:
            # 1. Detectar el material objetivo
            # Primero miramos en la posición exacta
            sx, sy, sz = start_pos['x'], start_pos['y'], start_pos['z']
            
            # Bloques que ignoramos como "veta" por defecto (aire, tierra, piedra base)
            # Nota: Piedra (STONE) podria ser valida si eso es lo que buscamos, pero suele ser el material de relleno.
            # Asumiremos que si está en BOM, es válido.
            ignored_blocks = [block.AIR.id, block.BEDROCK.id, block.GRASS.id, block.DIRT.id] 
            
            try:
                b_id = self.mc.getBlock(sx, sy, sz)
            except Exception as e:
                self.logger.error(f"Error reading block at start_pos: {e}")
                return False
            
            found_vein = False
            
            # Chequeo directo
            is_valid = (b_id not in ignored_blocks) or (target_bom and b_id in target_bom)
            
            if is_valid and b_id != block.AIR.id:
                self.target_id = b_id
                self.queue.append((sx, sy, sz))
                found_vein = True
                self.logger.info(f"VeinStrategy: Veta detectada en inicio (ID: {b_id}).")
            else:
                # Búsqueda local de 3x3x3 si no encontramos nada justo en los pies
                self.logger.info("VeinStrategy: Buscando veta adyacente...")
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        for dz in range(-1, 2):
                            if found_vein: break # Optimization loop break
                            
                            chk_x, chk_y, chk_z = sx + dx, sy + dy, sz + dz
                            try:
                                chk_id = self.mc.getBlock(chk_x, chk_y, chk_z)
                            except: continue

                            # Logica de aceptacion
                            chk_valid = (chk_id not in ignored_blocks) or (target_bom and chk_id in target_bom)

                            if chk_valid and chk_id != block.AIR.id:
                                # Prioridad a BOM si existe: Si BOM tiene items, y este bloque NO esta en BOM, lo ignoramos 
                                # (salvo que BOM este vacio, entonces minamos cualquier cosa interesante)
                                if target_bom and chk_id not in target_bom:
                                    continue
                                
                                self.target_id = chk_id
                                self.queue.append((chk_x, chk_y, chk_z))
                                found_vein = True
                                self.logger.info(f"VeinStrategy: Veta encontrada adyacente (ID: {self.target_id}) en ({chk_x, chk_y, chk_z}).")
                                break
            
            self.searching = False
            if not found_vein:
                self.logger.info("VeinStrategy: No se encontró ninguna veta válida cerca.")
                return False
        
        # 2. Procesar la cola (Minería Recursiva/Iterativa)
        if not self.queue:
            self.logger.info("VeinStrategy: Veta agotada.")
            return False

        # Procesar un bloque por tick
        curr_x, curr_y, curr_z = self.queue.pop(0)
        
        if (curr_x, curr_y, curr_z) in self.visited:
            return True # Ya visitado, siguiente ciclo
        
        self.visited.add((curr_x, curr_y, curr_z))
        
        try:
            # Verificar bloque actual
            b_id = self.mc.getBlock(curr_x, curr_y, curr_z)
            
            if b_id == self.target_id:
                # Minar
                self.mc.setBlock(curr_x, curr_y, curr_z, block.AIR.id)
                current_inventory[b_id] = current_inventory.get(b_id, 0) + 1
                
                # Añadir vecinos (6 direcciones)
                neighbors = [
                    (curr_x+1, curr_y, curr_z), (curr_x-1, curr_y, curr_z),
                    (curr_x, curr_y+1, curr_z), (curr_x, curr_y-1, curr_z),
                    (curr_x, curr_y, curr_z+1), (curr_x, curr_y, curr_z-1)
                ]
                for n in neighbors:
                    if n not in self.visited:
                        self.queue.append(n)
        except Exception as e:
            self.logger.error(f"Error procesando veta en ({curr_x}, {curr_y}, {curr_z}): {e}")
        
        await asyncio.sleep(0.05)
        return True
