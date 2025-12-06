import asyncio
import time
from agents.base_agent import BaseAgent


class ExplorerBot(BaseAgent):
    """
    ExplorerBot:
    - Explora el entorno alrededor de una posición (x, z)
    - Devuelve mapas, altura del terreno, puntos de interés, biomasa o huecos
    - Informa al BuilderBot y MinerBot mediante el MessageBus
    - Sigue el ciclo PDA (Perception → Decision → Action)
    """

    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)     
        #self.x = mc.player.getTilePos().x       # posición x por defecto
        #self.z = mc.player.getTilePos().z       # posición z por defecto
        self.range = 100                        # rango por defecto
        self.scan_complete = False
        self.map_data = None

    async def perceive(self):
        pass

    async def decide(self):
        pass

    async def act(self):
        pass

    async def run(self):
        self.logger.info("ExplorerBot iniciado")
        await super().run()

    def setup_subscriptions(self):
        """Suscripciones específicas del ExplorerBot."""

        super().setup_subscriptions()
        
        # Comandos específicos: start, set
        for cmd in ["start", "set"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")

    async def handle_command(self, command: str, payload=None):
        """Manejo de comandos específicos (start, set) + base."""
        
        await super().handle_command(command, payload)
        payload = payload or {}

        if command == "start":
            # ./explorer start x=100 z=100 range=50
            if "x" in payload and "z" in payload:
                x = payload["x"]
                z = payload["z"]
                if "range" in payload:
                    self.range = payload["range"]
                
                msg = f"{self.id}: Start exploración en ({x}, {z}) Rango={self.range}"
                self.logger.info(msg)
                self.mc.postToChat(msg)
                
                # Actualizar estado y contexto
                self.context.update({'target_x': x, 'target_z': z, 'range': self.range})
                await self.set_state(State.RUNNING, "start command")
            else:
                self.mc.postToChat(f"{self.id}: Faltan parametros x, z para start.")

        elif command == "set":
            # ./explorer set range=50
            if "range" in payload:
                self.range = payload["range"]
                msg = f"{self.id}: Rango actualizado a {self.range}"
                self.logger.info(msg)
                self.mc.postToChat(msg)
                self.context['range'] = self.range
            else:
                 self.mc.postToChat(f"{self.id}: El comando set requiere 'range'.")