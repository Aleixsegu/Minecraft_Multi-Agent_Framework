from abc import ABC, abstractmethod
from typing import Dict, Any, List
from mcpi.minecraft import Minecraft
from utils.logging import Logger

class MiningStrategy(ABC):
    """
    Interfaz abstracta para todas las estrategias de minería.
    Define el contrato para ejecutar la lógica de extracción.
    """
    
    def __init__(self, mc: Minecraft, logger: Logger, agent_id: str):
        self.mc = mc
        self.logger = logger
        self.agent_id = agent_id

    @abstractmethod
    async def mine(self, target_bom: Dict[int, int], current_inventory: Dict[int, int], start_pos: Dict[str, int]) -> bool:
        """
        Ejecuta el algoritmo de minería.

        Args:
            target_bom (Dict[int, int]): Bill of Materials (Bloque ID -> Cantidad requerida).
            current_inventory (Dict[int, int]): Inventario actual del MinerBot.
            start_pos (Dict[str, int]): Posición (x, y, z) donde comenzar la minería.

        Returns:
            bool: True si la minería ha avanzado/tuvo éxito, False si está completa o bloqueada.
        """
        pass