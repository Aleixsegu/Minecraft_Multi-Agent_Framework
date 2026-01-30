import pytest
from unittest.mock import MagicMock, AsyncMock  # <--- FALTABA ESTO
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from messages.message_parser import MessageParser

@pytest.fixture
def mock_message_bus():
    mock = MagicMock()
    mock.publish = AsyncMock() # Ahora sí funcionará
    return mock

@pytest.mark.asyncio
async def test_parse_valid_command_with_params(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command_str = "./miner start x=100 y=-5 z=200"

    await parser.process_chat_message(command_str)

    mock_message_bus.publish.assert_called_once()
    call_args = mock_message_bus.publish.call_args
    _, control_message = call_args[0]

    assert control_message['type'] == "command.start.v1"
    assert control_message['target'] in ["MinerBot", "BROADCAST"]

@pytest.mark.asyncio
async def test_parse_command_with_string_and_int_params(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command_str = "./miner set strategy=grid limit=50"

    await parser.process_chat_message(command_str)

    _, control_message = mock_message_bus.publish.call_args[0]

    assert control_message['type'] == "command.set.v1"
    assert control_message['target'] in ["MinerBot", "BROADCAST"]

@pytest.mark.asyncio
async def test_parse_invalid_command_formatting(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    invalid_command = "invalid command string"
    await parser.process_chat_message(invalid_command)
    mock_message_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_parse_unknown_agent(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command = "./unknown agent command"
    await parser.process_chat_message(command)
    mock_message_bus.publish.assert_not_called()