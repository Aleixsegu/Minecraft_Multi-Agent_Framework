from agents.base_agent import BaseAgent
from agents.state_model import State
from strategies.mining_strategy import MiningStrategy
from strategies.vertical_strategy import VerticalStrategy

class MinerBot(BaseAgent):
 
    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)
        self.bom_received = False
        self.strategy = VerticalStrategy(self.mc, self.logger, self.id)

    async def perceive(self):
        self.mc.postToChat(f"MinerBot {self.id}: En fase de run (percepcion) al haber hecho el comando start")

    async def decide(self):
        self.mc.postToChat(f"MinerBot {self.id}: En fase de run (decision) al haber hecho el comando start")

    async def act(self):
        self.mc.postToChat(f"MinerBot {self.id}: En fase de run (accion) al haber hecho el comando start")

    async def run(self):
        self.logger.info("MinerBot iniciado")
        await super().run()

    def setup_subscriptions(self):
        """Suscripciones específicas del MinerBot."""
        super().setup_subscriptions()
        
        # Comandos: start, set, fulfill
        for cmd in ["start", "set", "fulfill"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")

        self.bus.subscribe(self.id, f"materials.requirements.v1")

    async def handle_command(self, command: str, payload=None):
        payload = payload or {}
        
        # Verificar ID si está presente en el payload (depende del parser, pero asumimos que puede venir)
        # El comando ./miner start <id> implica que el parser dirige esto o lo pone en payload.
        target_id = payload.get("id") or payload.get("target_id")
        if target_id and target_id != self.id:
            return

        if command == "start":
            # ./miner start <id> [x=.. z=.. y=..]
            
            x = payload.get("x")
            y = payload.get("y")
            z = payload.get("z")

            if x is None or z is None:
                try:
                    pos = self.mc.player.getTilePos()
                    x = pos.x
                    y = pos.y
                    z = pos.z
                except Exception as e:
                    self.logger.error(f"Error obteniendo posición del jugador: {e}")
                    x = 0; y = 0; z = 0

            msg = f"{self.id}: Iniciando mineria en ({x}, {y}, {z})"
            if self.strategy:
                msg += f" con estrategia {self.strategy.__class__.__name__}"
            
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            self.context.update({'target_x': x, 'target_y': y, 'target_z': z})
            return

        elif command == "set":
            # ./miner set strategy <id> <vertical|grid|vein>
            
            if "strategy" in payload:
                strat_name = payload["strategy"]
                
                # Importar dinamicamente para evitar ciclos o cargas innecesarias
                from utils.reflection import get_all_strategies
                import os
                
                # Asumimos path relativo desde este archivo: ../strategies
                # Pero reflection pide el path absoluto o correcto.
                # src/agents -> src/strategies
                current_dir = os.path.dirname(os.path.abspath(__file__))
                strategies_dir = os.path.join(os.path.dirname(current_dir), "strategies")
                
                available_strategies = get_all_strategies(strategies_dir)
                
                # Buscar coincidencia (ej: "vertical" match "VerticalStrategy")
                selected_cls = None
                for name, cls in available_strategies.items():
                    if strat_name.lower() in name.lower():
                        selected_cls = cls
                        break
                
                if selected_cls:
                    self.strategy = selected_cls(self.mc, self.logger, self.id)
                    msg = f"{self.id}: Estrategia establecida a {selected_cls.__name__}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                else:
                    self.mc.postToChat(f"{self.id}: Estrategia '{strat_name}' no encontrada.")
            return

        elif command == "fulfill":
            # ./miner fulfill <id>
            if self.bom_received:
                await self.set_state(State.RUNNING, "fulfill command")
                self.mc.postToChat(f"{self.id}: BOM recibido. Iniciando mineria.")
            else:
                self.mc.postToChat(f"{self.id}: No se puede iniciar. BOM no recibido.")
            return

        await super().handle_command(command, payload)
