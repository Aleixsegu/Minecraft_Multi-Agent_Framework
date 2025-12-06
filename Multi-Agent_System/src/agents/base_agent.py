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
    # Bucle principal
    # --------------------------------------------------------
    async def run(self):
        """Bucle principal del agente, controlado por el estado FSM."""
        
        await self.set_state(State.IDLE, reason="initialization")

        while self.state != State.STOPPED:

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
        """Maneja comandos externos."""

        if command == "pause":
            await self.set_state(State.PAUSED, "paused by command")

        elif command == "resume":
            self.context = self.checkpoint.load()
            await self.set_state(State.RUNNING, "resumed")

        elif command == "stop":
            await self.set_state(State.STOPPED, "stopped by command")

        elif command == "update":
            if payload:
                self.context.update(payload)
            await self.set_state(State.RUNNING, "updated configuration")

        else:
            self.logger.error("unknown_command", context={"command": command})
