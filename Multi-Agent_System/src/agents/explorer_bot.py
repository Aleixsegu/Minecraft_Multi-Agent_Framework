import asyncio
import time
from agents.base_agent import BaseAgent
from agents.state_model import State


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
        self.posX = 0
        self.posZ = 0     
        self.range = 50                        # rango por defecto

    async def perceive(self):
        self.mc.postToChat(f"ExplorerBot {self.id}: En fase de run (percepcion) al haber hecho el comando start")

    async def decide(self):
        self.mc.postToChat(f"ExplorerBot {self.id}: En fase de run (decide) al haber hecho el comando start")

    async def act(self):
        self.mc.postToChat(f"ExplorerBot {self.id}: En fase de run (actuar) al haber hecho el comando start")

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
        payload = payload or {}

        # 1. Intentar manejar comandos específicos de ExplorerBot
        if command == "start":
            # ./explorer start <id> [x=.. z=..] [range=..]
            
            # 1. Determinar Objetivos (x, z)
            if "x" in payload and "z" in payload:
                x = payload["x"]
                z = payload["z"]
            else:
                # Si no se dan coordenadas, usar la posición del jugador
                try:
                    pos = self.mc.player.getTilePos()
                    self.posX = pos.x
                    self.posZ = pos.z
                except Exception as e:
                    self.logger.error(f"Error obteniendo posición del jugador: {e}")
                    self.posX = 0
                    self.posZ = 0

            # 2. Determinar Rango (opcional)
            if "range" in payload:
                self.range = payload["range"]

            # 3. Ejecutar
            msg = f"{self.id}: Iniciando exploracion en ({x}, {z}) con Rango={self.range}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            # Actualizar estado y contexto
            self.context.update({'target_x': x, 'target_z': z, 'range': self.range})
            await self.set_state(State.RUNNING, "start command")
            
            return

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
            return

        # 2. Si no es específico, delegar al BaseAgent
        await super().handle_command(command, payload)