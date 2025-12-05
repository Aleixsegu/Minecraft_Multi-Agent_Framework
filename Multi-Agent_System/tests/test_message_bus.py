import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from messages.message_bus import MessageBus

@pytest.fixture(autouse=True)
def mock_deps(monkeypatch):
    monkeypatch.setattr("messages.message_bus.validate_message", lambda m: True)
    # Mockear Logger
    mock_logger = MagicMock()
    monkeypatch.setattr("messages.message_bus.Logger", MagicMock(return_value=mock_logger))

@pytest.fixture
def bus():
    return MessageBus()

@pytest.mark.asyncio
async def test_register_agent(bus):
    bus.register_agent("Agent1")
    assert "Agent1" in bus._queues

@pytest.mark.asyncio
async def test_subscribe_agent(bus):
    bus.register_agent("Agent1")
    bus.subscribe("Agent1", "topic.v1")
    assert "Agent1" in bus._subscriptions["topic.v1"]

@pytest.mark.asyncio
async def test_subscribe_unregistered_agent_raises_error(bus):
    with pytest.raises(ValueError, match="must be registered"):
        bus.subscribe("GhostAgent", "topic.v1")

@pytest.mark.asyncio
async def test_publish_subscribe_delivery(bus):
    """Verifica que un mensaje publicado llegue a los suscriptores."""
    bus.register_agent("Subscriber1")
    bus.subscribe("Subscriber1", "broadcast.v1")
    
    msg = {"type": "broadcast.v1", "payload": "data", "target": None}
    await bus.publish("Sender", msg)
    
    received = await bus.receive("Subscriber1")
    assert received == msg

@pytest.mark.asyncio
async def test_publish_direct_delivery(bus):
    """Verifica entrega punto a punto usando 'target'."""
    bus.register_agent("TargetAgent")
    
    msg = {"type": "generic.v1", "payload": "secret", "target": "TargetAgent"}
    await bus.publish("Sender", msg)
    
    received = await bus.receive("TargetAgent")
    assert received == msg

@pytest.mark.asyncio
async def test_receive_unregistered_raises_error(bus):
    with pytest.raises(ValueError, match="is not registered"):
        await bus.receive("GhostAgent")
