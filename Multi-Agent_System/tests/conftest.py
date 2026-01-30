import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Asegurar que el src es visible
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))

from messages.message_bus import MessageBus
from agents.agent_manager import AgentManager
from agents.state_model import State

@pytest.fixture
def mock_mc():
    """Simula la conexión a Minecraft para no necesitar el juego real."""
    mock = MagicMock()
    # Mockear player.getTilePos
    mock.player.getTilePos.return_value.x = 100
    mock.player.getTilePos.return_value.y = 64
    mock.player.getTilePos.return_value.z = 100
    # Mockear getHeight
    mock.getHeight.return_value = 63
    return mock

@pytest.fixture
def message_bus():
    """Bus de mensajes limpio para cada prueba."""
    return MessageBus()

@pytest.fixture
def agent_manager(mock_mc, message_bus):
    """Manager con dependencias mockeadas."""
    return AgentManager(mock_mc, message_bus)