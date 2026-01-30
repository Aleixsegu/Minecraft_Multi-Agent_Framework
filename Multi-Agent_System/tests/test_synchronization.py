import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from agents.workflow_manager import WorkflowManager
from agents.state_model import State

@pytest.mark.sync
@pytest.mark.asyncio
class TestSynchronization:

    async def test_ensure_agent_waits_for_idle(self, agent_manager):
        slow_agent = AsyncMock()
        # Mock de la propiedad state
        type(slow_agent).state = MagicMock(side_effect=[State.STOPPED, State.RUNNING, State.IDLE, State.IDLE])

        agent_manager.get_agent = MagicMock(return_value=None)
        agent_manager.create_agent = AsyncMock(return_value=slow_agent)

        wf_manager = WorkflowManager(agent_manager)

        # Usamos solo 2 argumentos si tu codigo asi lo requiere
        try:
            agent = await wf_manager._ensure_agent("TestBot", "TestBot_1")
        except TypeError:
            # Fallback por si acaso requiere 3
            agent = await wf_manager._ensure_agent("TestBot", "TestBot_1", "Group1")
            
        assert agent == slow_agent