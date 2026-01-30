import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from strategies.grid_strategy import GridStrategy
from strategies.vertical_strategy import VerticalStrategy
from strategies.vein_strategy import VeinStrategy

class TestStrategies:
    
    @pytest.fixture
    def mock_agent_deps(self):
        mc = MagicMock()
        logger = MagicMock()
        return mc, logger

    @pytest.mark.asyncio
    async def test_grid_mine(self, mock_agent_deps):
        mc, logger = mock_agent_deps
        st = GridStrategy(mc, logger, "TestAgent")
        
        # mine signature: mine(self, requirements, inventory, start_pos)
        # It's async
        reqs = {1: 10}
        inv = {1: 0}
        pos = {'x': 0, 'y': 60, 'z': 0}
        
        # Mocking actions
        mc.getBlock.return_value = 1 # Found block
        
        await st.mine(reqs, inv, pos)
        
        # Verify it did something
        # GridStrategy usually digs or moves
        assert mc.getBlock.called or mc.setBlock.called

    @pytest.mark.asyncio
    async def test_vertical_mine(self, mock_agent_deps):
        mc, logger = mock_agent_deps
        st = VerticalStrategy(mc, logger, "TestAgent")
        
        reqs = {1: 10}
        inv = {1: 0}
        pos = {'x': 0, 'y': 60, 'z': 0}
        
        mc.getBlock.return_value = 0 # Air
        
        await st.mine(reqs, inv, pos)
        
    @pytest.mark.asyncio
    async def test_vein_mine(self, mock_agent_deps):
        mc, logger = mock_agent_deps
        st = VeinStrategy(mc, logger, "TestAgent")
        
        reqs = {1: 10}
        inv = {1: 0}
        pos = {'x': 0, 'y': 60, 'z': 0}
        
        await st.mine(reqs, inv, pos)