import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from agents.agent_manager import AgentManager

@pytest.fixture
def manager():
    mc = MagicMock()
    bus = MagicMock()
    bus.register_agent = MagicMock()
    bus.subscribe = MagicMock()
    
    # Mockear WorkflowManager para que no intente instanciar cosas reales
    with patch("agents.agent_manager.WorkflowManager") as MockWF:
        mgr = AgentManager(mc, bus)
        mgr.factory = MagicMock() 
        yield mgr

@pytest.mark.asyncio
async def test_initialization(manager):
    assert manager.running is True
    assert manager.agents_map == {}

@pytest.mark.asyncio
async def test_setup_subscriptions(manager):
    manager.setup_subscriptions()
    manager.bus.register_agent.assert_called_with("AgentManager")
    assert manager.bus.subscribe.call_count >= 2

@pytest.mark.asyncio
async def test_create_agent_success(manager):
    # Setup Factory Mock
    mock_agent = AsyncMock()
    manager.factory.create_agent.return_value = mock_agent
    
    result = await manager.create_agent("MinerBot", "miner_1")
    
    assert result == mock_agent
    assert "miner_1" in manager.agents_map
    manager.factory.create_agent.assert_called_once()
    # Verifica que se lanzó la tarea run() del agente
    # (AsyncMock retorna corutina por defecto, create_task la consume)

@pytest.mark.asyncio
async def test_create_agent_already_exists(manager):
    # Pre-llenar map
    manager.agents_map["existing"] = "OLD_AGENT"
    
    result = await manager.create_agent("AnyBot", "existing")
    
    assert result == "OLD_AGENT"
    manager.factory.create_agent.assert_not_called()

@pytest.mark.asyncio
async def test_create_agent_failure(manager):
    # Factory lanza excepción
    manager.factory.create_agent.side_effect = Exception("Factory Failed")
    
    result = await manager.create_agent("MinerBot", "fail_id")
    
    assert result is None
    assert "fail_id" not in manager.agents_map

@pytest.mark.asyncio
async def test_handle_create_command(manager):
    # Mock create_agent interno
    manager.create_agent = AsyncMock()
    
    payload = {"agent_type": "ExplorerBot", "id": "exp_1"}
    await manager.handle_create_command("Unknown", payload)
    
    manager.create_agent.assert_awaited_with("ExplorerBot", "exp_1")

@pytest.mark.asyncio
async def test_handle_message_create(manager):
    manager.handle_create_command = AsyncMock()
    
    msg = {
        "type": "command.create.v1",
        "target": "AgentManager",
        "payload": {"agent_type": "BuilderBot"}
    }
    
    await manager.handle_message(msg)
    manager.handle_create_command.assert_awaited_with("AgentManager", msg["payload"])

@pytest.mark.asyncio
async def test_handle_message_workflow(manager):
    manager.workflow_manager.execute_workflow = AsyncMock()
    
    msg = {
        "type": "command.workflow.run",
        "payload": {"command_str": "run stuff"}
    }
    
    await manager.handle_message(msg)
    manager.workflow_manager.execute_workflow.assert_awaited_with("run stuff")

@pytest.mark.asyncio
async def test_run_loop(manager):
    # Mockear receive para retornar un mensaje y luego lanzar excepción para salir del loop 
    # O mejor, usar manager.running = False dentro de un side_effect
    
    msg = {"type": "command.create.v1", "payload": {}}
    
    async def side_effect(agent_id):
        manager.running = False # Detener loop después del primer mensaje
        return msg
        
    manager.bus.receive.side_effect = side_effect
    manager.handle_message = AsyncMock()
    
    await manager.run()
    
    manager.handle_message.assert_awaited_once_with(msg)
