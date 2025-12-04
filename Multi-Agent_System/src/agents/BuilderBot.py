import asyncio
import time
from agents.BaseAgent import BaseAgent



class BuilderBot(BaseAgent):
 
    def __init__(self, agent_id,mc,  bus):
        super().__init__(agent_id, mc, bus)     
        self.x = mc.player.getTilePos().x       # posición x por defecto
        self.z = mc.player.getTilePos().z       # posición z por defecto
        self.range = 100                        # rango por defecto

    async def perceive(self):
        pass

    async def decide(self):
        pass

    async def act(self):
        pass
