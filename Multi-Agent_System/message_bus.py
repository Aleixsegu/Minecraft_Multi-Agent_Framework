# message_bus.py

import asyncio
from utils.logging import log_event
from json_schema import validate_message


class MessageBus:
    """
    Central asynchronous communication system for all agents.
    Agents communicate using JSON messages validated against a schema.

    Features:
    - Each agent has its own inbox (async Queue)
    - Messages are validated before delivery
    - All traffic is logged (sent + received)
    - Supports direct sending and broadcast
    """

    def __init__(self):
        self.queues = {}  # agent_id → asyncio.Queue

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
        await log_event({
            "event": "message_sent",
            "source": source,
            "target": target,
            "message": msg
        })

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
            await log_event({
                "event": "broadcast_sent",
                "source": source,
                "target": target,
                "message": msg
            })
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

        await log_event({
            "event": "message_received",
            "target": agent_id,
            "message": msg
        })

        return msg
