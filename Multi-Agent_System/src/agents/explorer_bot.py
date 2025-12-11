import asyncio
import asyncio
import datetime
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
        try:
            # Checkeo rápido de mensajes
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            if msg:
                await self.handle_incoming_message(msg)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error en perceive (mensajes): {e}")
    async def decide(self):
        """
        Decide la siguiente acción basándose en el contexto y estado.
        """
        # Si estamos en RUNNING, verificamos el progreso de la misión
        if self.state == State.RUNNING:
            if "target_x" in self.context and "target_z" in self.context:
                
                # 1. Si no hemos escaneado, decidimos ESCANEAR
                if not self.context.get("scan_complete", False):
                    self.context["next_action"] = "scan_environment"
                    self.logger.info("Decisión: Escanear entorno.")
                
                # 2. Si ya escaneamos pero no hemos reportado, decidimos REPORTAR
                elif not self.context.get("report_sent", False):
                    self.context["next_action"] = "report_findings"
                    self.logger.info("Decisión: Reportar hallazgos.")
                
                # 3. Datos enviados, terminar misión
                else:
                    self.context["next_action"] = "finish_mission"
                    self.logger.info("Decisión: Finalizar misión.")
            else:
                self.context["next_action"] = "idle"
    async def act(self):
        """Ejecuta la acción decidida."""
        action = self.context.get("next_action")
        
        if action == "scan_environment":
            self.logger.info("Ejecutando exploración...")
            await self._scan_surroundings()
            self.context["scan_complete"] = True
            
        elif action == "report_findings":
            self.logger.info("Reportando hallazgos...")
            await self._publish_map()
            self.context["report_sent"] = True
            
        elif action == "finish_mission":
            self.logger.info("Misión finalizada. Volviendo a IDLE.")
            await self.set_state(State.IDLE, "mission_completed")
            # Limpieza opcional de contexto
            self.context["next_action"] = "idle"
    async def _scan_surroundings(self):
        """Escanea el terreno alrededor del objetivo."""
        center_x = int(self.context.get('target_x', self.posX))
        center_z = int(self.context.get('target_z', self.posZ))
        radius = 5 # Radio pequeño para demo (evitar lag)
        
        height_map = []
        # Escaneo simple de elevación
        for dx in range(-radius, radius + 1):
            row = []
            for dz in range(-radius, radius + 1):
                # mc.getHeight es sincrono, cuidado con radios grandes
                h = self.mc.getHeight(center_x + dx, center_z + dz)
                self.mc.setBlock(center_x + dx, h, center_z + dz, 57)
                row.append(h)
            height_map.append(row)
            
        self.context["latest_map"] = {
            "center": (center_x, center_z),
            "radius": radius,
            "data": height_map
        }
        await asyncio.sleep(0.5) # Simular tiempo de escaneo
    async def _publish_map(self):
        """Publica el mapa generado al bus."""
        map_data = self.context.get("latest_map", {})
        msg = {
            "type": "map.v1",
            "source": self.id,
            "target": "BROADCAST", 
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            "status": "SUCCESS",
            "payload": map_data
        }
        await self.bus.publish(self.id, msg)
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
                    x = int(pos.x)
                    z = int(pos.z)
                except Exception as e:
                    self.logger.error(f"Error obteniendo posición del jugador: {e}")
                    self.posX = 0
                    self.posZ = 0
                    x = 0
                    z = 0
            # 2. Determinar Rango (opcional)
            if "range" in payload:
                self.range = payload["range"]
            # 3. Ejecutar
            msg = f"{self.id}: Iniciando exploracion en ({x}, {z}) con Rango={self.range}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            # Actualizar estado y contexto
            # Actualizar estado y contexto
            self.context.update({
                'target_x': x, 
                'target_z': z, 
                'range': self.range,
                'scan_complete': False, # Reset flags
                'report_sent': False
            })
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