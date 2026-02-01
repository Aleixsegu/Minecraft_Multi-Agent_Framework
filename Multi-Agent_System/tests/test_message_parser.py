import pytest
from unittest.mock import MagicMock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from messages.message_parser import MessageParser

@pytest.fixture
def mock_message_bus():
    mock = MagicMock()
    mock.publish = AsyncMock()
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

@pytest.mark.asyncio
async def test_workflow_command(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command_str = "./workflow start template=wall"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    
    assert control_msg['type'] == "command.workflow.start"
    assert control_msg['target'] == "AgentManager"
    assert control_msg['payload']['command_str'] == "template=wall"

@pytest.mark.asyncio
async def test_create_command(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command_str = "./explorer create name=Explorer2"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    
    assert control_msg['type'] == "command.create.v1"
    assert control_msg['target'] == "AgentManager"
    assert control_msg['payload']['name'] == "Explorer2"

@pytest.mark.asyncio
async def test_unicast_with_explicit_id(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    command_str = "./miner stop id=MinerBot_1"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    
    assert control_msg['type'] == "command.stop.v1"
    assert control_msg['target'] == "MinerBot_1"
    assert control_msg['payload']['id'] == "MinerBot_1"

@pytest.mark.asyncio
async def test_positional_range_two_args(mock_message_bus):
    # ./explorer scan range <ID> <VALOR>
    parser = MessageParser(mock_message_bus)
    command_str = "./explorer scan range Bot1 50"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['range'] == 50
    assert payload['id'] == "Bot1"
    assert control_msg['target'] == "Bot1"

@pytest.mark.asyncio
async def test_positional_range_one_arg(mock_message_bus):
    # ./explorer scan range <VALOR>
    parser = MessageParser(mock_message_bus)
    command_str = "./explorer scan range 50"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['range'] == 50
    # No ID, so broadcast
    assert control_msg['target'] == "BROADCAST"

@pytest.mark.asyncio
async def test_positional_strategy_two_args(mock_message_bus):
    # ./miner set strategy <ID> <VALOR>
    parser = MessageParser(mock_message_bus)
    command_str = "./miner set strategy Bot2 Grid"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['strategy'] == "Grid"
    assert payload['id'] == "Bot2"
    assert control_msg['target'] == "Bot2"

@pytest.mark.asyncio
async def test_positional_strategy_one_arg(mock_message_bus):
    # ./miner set strategy <VALOR>
    parser = MessageParser(mock_message_bus)
    command_str = "./miner set strategy Vein"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['strategy'] == "Vein"
    assert control_msg['target'] == "BROADCAST"

@pytest.mark.asyncio
async def test_loose_id_argument(mock_message_bus):
    # ./builder stop Bot3
    parser = MessageParser(mock_message_bus)
    command_str = "./builder stop Bot3"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['id'] == "Bot3"
    assert control_msg['target'] == "Bot3"

@pytest.mark.asyncio
async def test_loose_ignored_id_argument(mock_message_bus):
    # ./builder plan list - 'list' is in ignored_ids
    parser = MessageParser(mock_message_bus)
    command_str = "./builder plan list"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    # 'list' should NOT be taken as an ID
    assert 'id' not in payload
    assert control_msg['target'] == "BROADCAST"
    assert 'list' in payload['args']

@pytest.mark.asyncio
async def test_parse_range_value_error(mock_message_bus):
    parser = MessageParser(mock_message_bus)
    # range with string instead of int
    command_str = "./explorer scan range big"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['range'] == "big"

@pytest.mark.asyncio
async def test_parse_range_two_args_no_equals(mock_message_bus):
    # Testing branch: if "=" not in val_id
    parser = MessageParser(mock_message_bus)
    command_str = "./explorer scan range Bot1=X 50"
    
    await parser.process_chat_message(command_str)
    
    args = mock_message_bus.publish.call_args[0]
    control_msg = args[1]
    payload = control_msg['payload']
    
    assert payload['range'] == 50
    assert 'id' not in payload
    assert payload.get('Bot1') == 'X'