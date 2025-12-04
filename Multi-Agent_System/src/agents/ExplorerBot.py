import asyncio
import time
from agents.BaseAgent import BaseAgent



class ExplorerBot(BaseAgent):
    """
    ExplorerBot:
    - Explora el entorno alrededor de una posición (x, z)
    - Devuelve mapas, altura del terreno, puntos de interés, biomasa o huecos
    - Informa al BuilderBot y MinerBot mediante el MessageBus
    - Sigue el ciclo PDA (Perception → Decision → Action)
    """

    def __init__(self, agent_id,mc,  bus):
        super().__init__(agent_id, mc, bus)     
        self.x = mc.player.getTilePos().x       # posición x por defecto
        self.z = mc.player.getTilePos().z       # posición z por defecto
        self.range = 100                        # rango por defecto
        self.scan_complete = False
        self.map_data = None

    async def perceive(self):
        pass

    async def decide(self):
        pass

    async def act(self):
        pass