import pytest
import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from agents.base_agent import BaseAgent
from agents.state_model import State

class ConcreteAgent(BaseAgent):
    async def perceive(self): self.context["perceived"] = True
    async def decide(self): self.context["decided"] = True
    async def act(self): self.context["acted"] = True

@pytest.fixture
def agent():
    mc = MagicMock()
    bus = MagicMock()
    with patch("agents.base_agent.Checkpoints") as MockCkpt:
        mock_instance = MockCkpt.return_value
        mock_instance.load.return_value = {}
        ag = ConcreteAgent("TestAgent", mc, bus)
        ag.checkpoint = mock_instance
        yield ag

@pytest.mark.asyncio
async def test_initial_state(agent):
    assert agent.state == State.IDLE

@pytest.mark.asyncio
async def test_state_transition(agent):
    await agent.set_state(State.RUNNING, "start")
    assert agent.state == State.RUNNING

@pytest.mark.asyncio
async def test_handle_command_pause(agent):
    await agent.handle_command("pause")
    assert agent.state == State.PAUSED
    agent.checkpoint.save.assert_called()

@pytest.mark.asyncio
async def test_handle_command_stop(agent):
    await agent.handle_command("stop")
    assert agent.state == State.STOPPED

@pytest.mark.asyncio
async def test_handle_command_update(agent):
    payload = {"param": 10}
    await agent.handle_command("update", payload)
    assert agent.context["param"] == 10

@pytest.mark.asyncio
async def test_run_cycle_execution(agent):
    task = asyncio.create_task(agent.run())
    await asyncio.sleep(0.01)
    await agent.set_state(State.RUNNING)
    await asyncio.sleep(0.1)
    
    assert agent.state == State.RUNNING
    assert agent.context.get("perceived") is True
    
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

@pytest.mark.asyncio
async def test_handle_incoming_message_filtering(agent):
    # Test valid message for this agent
    msg = {"type": "command.pause.v1", "payload": {"id": agent.id}}
    agent.handle_command = AsyncMock()
    await agent.handle_incoming_message(msg)
    agent.handle_command.assert_awaited_with("pause", msg["payload"])
    
    # Test message for another agent ID
    agent.handle_command.reset_mock()
    msg = {"type": "command.pause.v1", "payload": {"id": "OtherAgent"}}
    await agent.handle_incoming_message(msg)
    agent.handle_command.assert_not_awaited()

    # Test message for mismatching agent_type
    agent.handle_command.reset_mock()
    msg = {"type": "command.pause.v1", "payload": {"agent_type": "OtherClass"}}
    await agent.handle_incoming_message(msg)
    agent.handle_command.assert_not_awaited()

    # Test unknown command format
    agent.logger.warning = MagicMock()
    msg = {"type": "command.invalid", "payload": {}}
    await agent.handle_incoming_message(msg)
    agent.logger.warning.assert_called()

@pytest.mark.asyncio
async def test_set_state_side_effects(agent):
    # PAUSED saves checkpoint
    await agent.set_state(State.PAUSED)
    agent.checkpoint.save.assert_called()
    
    # STOPPED does not save 
    agent.checkpoint.save.reset_mock()
    await agent.set_state(State.STOPPED)
    agent.checkpoint.save.assert_not_called()

@pytest.mark.asyncio
async def test_handle_command_status_help(agent):
    # Status
    agent.context = {"foo": "bar", "inventory": {"item": 1}}
    agent.logger.info = MagicMock()
    await agent.handle_command("status")
    agent.logger.info.assert_called()
    
    # Help
    agent.mc.postToChat = MagicMock()
    await agent.handle_command("help")
    agent.mc.postToChat.assert_called()

@pytest.mark.asyncio
async def test_handle_command_resume(agent):
    # Setup resume scenario
    agent.checkpoint.load.return_value = {"restored": True}
    await agent.handle_command("resume")
    assert agent.state == State.RUNNING
    assert agent.context["restored"] is True
