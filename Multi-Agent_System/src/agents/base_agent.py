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
        
        # Comandos comunes a todos los agentes
        common_commands = ["pause", "resume", "stop", "status", "help", "update"]
        
        for cmd in common_commands:
            # 1. Suscripción Directa (command.pause.v1 -> ID)
            self.bus.subscribe(self.id, f"command.{cmd}.v1")
            
            # 2. Suscripción por Tipo (command.ExplorerBot.pause.v1 -> Todos los Explorers)
            my_type = self.__class__.__name__
            self.bus.subscribe(self.id, f"command.{my_type}.{cmd}.v1")

    async def process_messages(self):
        """
        Procesa mensajes entrantes del bus de forma no bloqueante (polling).
        """
        try:
            # Checkeo rápido de mensajes
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            
            if msg:
                await self._handle_incoming_message(msg)

        except asyncio.TimeoutError:
            pass 
        except Exception as e:
            self.logger.error(f"Error procesando mensajes: {e}")

    async def _handle_incoming_message(self, msg):
        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        
        # Detectar comandos: command.algo.v1
        if msg_type.startswith("command."):
            parts = msg_type.split(".")
            # Formatos: command.pause.v1 OR command.ExplorerBot.pause.v1
            # Si es broadcast de tipo, el comando está en la 3a posición (index 2)
            # Si es directo, está en la 2a (index 1)
            
            command = "unknown"
            if len(parts) == 3: # command.pause.v1
                command = parts[1]
            elif len(parts) == 4: # command.ExplorerBot.pause.v1
                command = parts[2]
                
            await self.handle_command(command, payload)

    # --------------------------------------------------------
    # Bucle principal
    # --------------------------------------------------------
    async def run(self):
        """Bucle principal del agente."""
        
        # Inicializar suscripciones
        self.setup_subscriptions()
        
        await self.set_state(State.IDLE, reason="initialization")

        while self.state != State.STOPPED:

            # 1. Procesar Mensajes (Siempre, incluso en pausa o idle)
            await self.process_messages()

            if self.state == State.PAUSED:
                await asyncio.sleep(0.2)
                continue

            if self.state == State.IDLE:
                await asyncio.sleep(0.1)
                continue

            if self.state == State.RUNNING:
                try:
                    await self.perceive()
                    await self.decide()
                    await self.act()
                except Exception as e:
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
        if new_state in (State.STOPPED, State.ERROR):
            self.checkpoint.save(self.context)

    # --------------------------------------------------------
    # Manejo de comandos
    # --------------------------------------------------------
    async def handle_command(self, command: str, payload=None):
        """Maneja comandos comunes. Las subclases deben overridear y llamar a super()."""

        if command == "pause":
            await self.set_state(State.PAUSED, "paused by command")
            self.mc.postToChat(f"{self.__class__.__name__} {self.id} pausado")

        elif command == "resume":
            self.context = self.checkpoint.load()
            await self.set_state(State.RUNNING, "resumed")
            self.mc.postToChat(f"{self.__class__.__name__} {self.id} reanudado")

        elif command == "stop":
            await self.set_state(State.STOPPED, "stopped by command")
            self.mc.postToChat(f"{self.__class__.__name__} {self.id} detenido")

        elif command == "update":
            if payload:
                self.context.update(payload)
            await self.set_state(State.RUNNING, "updated configuration")
            self.mc.postToChat(f"{self.__class__.__name__} {self.id} actualizado")
            
        elif command == "status":
            status_msg = f"Status {self.id}: STATE={self.state.name}"
            self.logger.info(status_msg)
            self.mc.postToChat(status_msg)
            
        elif command == "help":
            help_msg = f"Help {self.id}: pause, resume, stop, update, status"
            self.logger.info(help_msg)
            self.mc.postToChat(help_msg)

        else:
            self.logger.error("unknown_command", context={"command": command})

