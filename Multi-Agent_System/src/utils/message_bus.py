# utils.message_bus.py

import asyncio
from utils.logging import Logger
from utils.json_schema import validate_message


class MessageBus:
    """
    Comunicación asíncrona central para todos los agentes.
    Los agentes se comunican usando mensajes JSON validados con json_schema.
    """

    def __init__(self):
        self.queues = {}  # agent_id → asyncio.Queue
        self.logger = Logger("MessageBus")

    # ------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------
    def register_agent(self, agent_id: str):
        """Registers a new agent and creates its inbox queue."""
        if agent_id not in self.queues:
            self.queues[agent_id] = asyncio.Queue()

    # ------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------
    async def send(self, source: str, target: str, msg: dict):
        """Send a validated message from source to target."""

        # validate JSON structure
        validate_message(msg)

        # log outgoing message
        self.logger.log_message("SENT", "direct", source, target, msg)

        if target not in self.queues:
            raise ValueError(f"Target agent '{target}' is not registered.")

        await self.queues[target].put(msg)

    # ------------------------------------------------------------
    # Broadcast messages
    # ------------------------------------------------------------
    async def broadcast(self, source: str, msg: dict):
        """Sends a message to all registered agents."""

        validate_message(msg)

        for target in self.queues:
            self.logger.log_message("SENT", "broadcast", source, target, msg)
            await self.queues[target].put(msg)

    # ------------------------------------------------------------
    # Receiving messages
    # ------------------------------------------------------------
    async def receive(self, agent_id: str):
        """
        Waits for the next message for this agent.
        The function suspends until a message arrives.
        """

        if agent_id not in self.queues:
            raise ValueError(f"Agent '{agent_id}' is not registered.")

        msg = await self.queues[agent_id].get()

        # Extract source if available in msg, otherwise unknown
        source = msg.get('from', 'unknown')
        self.logger.log_message("RECEIVED", "any", source, agent_id, msg)

        return msg
