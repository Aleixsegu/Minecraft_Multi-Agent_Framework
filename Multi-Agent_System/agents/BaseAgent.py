# base/base_agent.py

import asyncio
import time
from abc import ABC, abstractmethod
from state import StateModel
from utils.logging import log_event
from utils.checkpoints import save_checkpoint, load_checkpoint


class BaseAgent(ABC):
    """
    Base class for all Minecraft agents.
    Implements:
    - Perception → Decision → Action cycle
    - Unified FSM (IDLE, RUNNING, PAUSED, WAITING, STOPPED, ERROR)
    - Control command handling (pause/resume/stop/update)
    - Structured logging
    - Checkpointing for recovery
    - Async execution
    """

    def __init__(self, agent_id: str, message_bus):
        self.id = agent_id
        self.bus = message_bus
        self.state = AgentState.IDLE
        self.context = {}

        # checkpoint file
        self.checkpoint_file = f"checkpoints/{self.id}.json"

    # --------------------------------------------------------
    # Abstract PDA methods
    # --------------------------------------------------------
    @abstractmethod
    async def perceive(self):
        """Reads environment or incoming messages."""
        pass

    @abstractmethod
    async def decide(self):
        """Computes next action based on perception."""
        pass

    @abstractmethod
    async def act(self):
        """Executes the chosen action."""
        pass

    # --------------------------------------------------------
    # Main execution loop
    # --------------------------------------------------------
    async def run(self):
        """Main agent loop, driven by FSM state."""
        await self.set_state(AgentState.IDLE, reason="initialization")

        while self.state != AgentState.STOPPED:

            if self.state == AgentState.PAUSED:
                await asyncio.sleep(0.2)
                continue

            if self.state == AgentState.IDLE:
                await asyncio.sleep(0.1)
                continue

            if self.state == AgentState.RUNNING:
                try:
                    await self.perceive()
                    await self.decide()
                    await self.act()
                except Exception as e:
                    await self.set_state(AgentState.ERROR, reason=str(e))

            await asyncio.sleep(0)  # yield to event loop

    # --------------------------------------------------------
    # State machine
    # --------------------------------------------------------
    async def set_state(self, new_state: AgentState, reason=""):
        prev_state = self.state
        self.state = new_state

        await log_event({
            "event": "state_transition",
            "agent": self.id,
            "previous": prev_state.value,
            "next": new_state.value,
            "reason": reason,
            "timestamp": time.time(),
        })

        # STOPPED / ERROR → save checkpoint
        if new_state in (AgentState.STOPPED, AgentState.ERROR):
            save_checkpoint(self.checkpoint_file, self.context)

    # --------------------------------------------------------
    # Command handling
    # --------------------------------------------------------
    async def handle_command(self, command: str, payload=None):

        if command == "pause":
            await self.set_state(AgentState.PAUSED, "paused by command")

        elif command == "resume":
            self.context = load_checkpoint(self.checkpoint_file)
            await self.set_state(AgentState.RUNNING, "resumed")

        elif command == "stop":
            await self.set_state(AgentState.STOPPED, "stopped by command")

        elif command == "update":
            if payload:
                self.context.update(payload)
            await self.set_state(AgentState.RUNNING, "updated configuration")

        else:
            await log_event({
                "event": "unknown_command",
                "agent": self.id,
                "command": command
            })
