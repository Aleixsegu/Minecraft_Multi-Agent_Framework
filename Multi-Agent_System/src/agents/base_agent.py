import asyncio
import time
from abc import ABC, abstractmethod
from agents.state_model import State
from utils.logging import Logger
from utils.checkpoints import Checkpoints
class BaseAgent(ABC):
    """
    Clase base para todos los agentes.
    Implementa:
    - Ciclo Percepción → Decisión → Acción
    - FSM Unificado (IDLE, RUNNING, PAUSED, WAITING, STOPPED, ERROR)
    - Manejo de comandos (pause/resume/stop/update)
    - Logging estructurado
    - Checkpointing para recuperación
    - Ejecución asíncrona
    """
    def __init__(self, agent_id: str, mc, message_bus):
        self.mc = mc
        self.id = agent_id
        self.bus = message_bus
        self.state = State.IDLE
        self.context = {}
        self.logger = Logger(agent_id, log_file_name=self.__class__.__name__)
        self.checkpoint = Checkpoints(agent_id)
    # --------------------------------------------------------
    # Métodos abstractos PDA
    # --------------------------------------------------------
    @abstractmethod
    async def perceive(self):
        """Lee el entorno o mensajes entrantes."""
        pass
    @abstractmethod
    async def decide(self):
        """Computa la próxima acción basada en la percepción."""
        pass    
    @abstractmethod
    async def act(self):
        """Ejecuta la acción seleccionada."""
        pass
    # --------------------------------------------------------
    # Gestión de Mensajes (Suscripciones y Proceso)
    # --------------------------------------------------------
    def setup_subscriptions(self):
        """
        Configura las suscripciones a eventos del bus.
        Las subclases deben llamar a super().setup_subscriptions().
        """
        self.bus.register_agent(self.id)
        
        # Comandos comunes a todos los agentes (Suscripción GENÉRICA)
        common_commands = ["pause", "resume", "stop", "status", "help", "update"]
        
        for cmd in common_commands:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")
    async def handle_incoming_message(self, msg):
        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        
        # 1. FILTRADO DE SEGURIDAD (Aunque el Bus ya hace Unicast, verificamos Broadcasts)
        
        # A) Check ID (Si el mensaje trae ID específico y no es el mio, lo ignoro)
        # Esto ocurre si se hace Broadcast de un comando destinado a un ID específico (raro, pero posible)
        if "id" in payload and str(payload["id"]) != str(self.id):
             return
        # B) Check TIPO DE AGENTE (Si el mensaje es para 'MinerBot' y yo soy 'ExplorerBot')
        target_type = payload.get("agent_type")
        if target_type and target_type != self.__class__.__name__:
             return
        # 2. PROCESAMIENTO
        # Detectar comandos: command.algo.v1 (Formato Genérico)
        if msg_type.startswith("command."):
            parts = msg_type.split(".")
            
            if len(parts) == 3: # command.pause.v1
                command = parts[1]
                await self.handle_command(command, payload)
            else:
                 self.logger.warning(f"Formato de mensaje desconocido: {msg_type}")
    # --------------------------------------------------------
    # Bucle principal
    # --------------------------------------------------------
    async def run(self):
        """Bucle principal del agente."""
        
        # Inicializar suscripciones
        self.setup_subscriptions()
        
        await self.set_state(State.IDLE, reason="initialization")
        while True:
            # 1. Perceive: Incluye recibir mensajes en todos los estados
            await self.perceive()
            
            if self.state == State.STOPPED:
                await asyncio.sleep(0.5)
                continue
                
            if self.state == State.PAUSED:
                await asyncio.sleep(0.2)
                continue
            if self.state == State.IDLE:
                await asyncio.sleep(0.1)
                continue
            if self.state == State.RUNNING:
                try:
                    # Perceive ya fue llamado arriba
                    await self.decide()
                    await self.act()
                except Exception as e:
                    self.logger.error(f"Error en ciclo PDA: {e}")
                    await self.set_state(State.ERROR, reason=str(e))
            await asyncio.sleep(0) 
    # --------------------------------------------------------
    # Máquina de estados
    # --------------------------------------------------------
    async def set_state(self, new_state: State, reason=""):
        """Cambia el estado del agente."""
        prev_state = self.state
        self.state = new_state
        # log de la transición
        self.logger.log_agent_transition(prev_state, new_state, reason)
        # si es STOPPED o ERROR, save checkpoint
        if new_state in (State.ERROR, State.PAUSED):
            self.checkpoint.save(self.context)
        elif new_state == State.STOPPED:
             # User Request: Stop does NOT save context to allow fresh start
             pass
    # --------------------------------------------------------
    # Manejo de comandos
    # --------------------------------------------------------
    async def handle_command(self, command: str, payload=None):
        """Maneja comandos comunes. Las subclases deben overridear y llamar a super()."""
        if command == "pause":
            await self.set_state(State.PAUSED, "paused by command")
            self.mc.postToChat(f"[{self.id}] Pausado")
        elif command == "resume":
            self.context = self.checkpoint.load()
            await self.set_state(State.RUNNING, "resumed")
            self.mc.postToChat(f"[{self.id}] Reanudado")
        elif command == "stop":
            await self.set_state(State.STOPPED, "stopped by command")
            self.mc.postToChat(f"[{self.id}] Detenido")
        elif command == "update":
            if payload:
                self.context.update(payload)
            await self.set_state(State.RUNNING, "updated configuration")
            self.mc.postToChat(f"[{self.id}] Config actualizado")
            
        elif command == "status":
            import json
            # Filter large objects for summary
            summary_ctx = {k: v for k, v in self.context.items() if k not in ['scan_state', 'latest_map', 'requirements', 'tasks_physical', 'tasks_creative']}
            
            # If inventory is present, summarize it count
            if 'inventory' in self.context:
                inv_count = len(self.context['inventory'])
                summary_ctx['inventory'] = f"<{inv_count} items>"
                
            status_msg = f"[{self.id}] Status [{self.state.name}]: {json.dumps(summary_ctx)}"
            self.logger.info(status_msg[:200] + "...") 
            # self.mc.postToChat(status_msg[:100]) # Silent in base to avoid spam, subclasses handle it
            pass
            
        elif command == "help":
            # Reflection-ish: List all handle_command strings if we could, 
            # but here we hardcode the base + hint at subclass
            cmds = ["pause", "resume", "stop", "status", "help"]
            msg = f"Comandos globales: {', '.join(cmds)}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
        else:
            self.logger.error("unknown_command", context={"command": command})
