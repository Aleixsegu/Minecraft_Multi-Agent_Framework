import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock
import mcpi.block as block

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from strategies.grid_strategy import GridStrategy
from strategies.vertical_strategy import VerticalStrategy
from strategies.vein_strategy import VeinStrategy

@pytest.fixture
def mock_mc():
    return MagicMock()

@pytest.fixture
def mock_logger():
    return MagicMock()

class TestGridStrategy:
    
    @pytest.fixture
    def strategy(self, mock_mc, mock_logger):
        return GridStrategy(mock_mc, mock_logger, "Agent1")

    @pytest.mark.asyncio
    async def test_initialization(self, strategy):
        assert strategy.width == 5
        assert strategy.current_x == 0

    @pytest.mark.asyncio
    async def test_mine_normal_block(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.return_value = 1 # Stone
        inv = {1: 0}
        
        # Run one tick
        active = await strategy.mine({}, inv, start_pos)
        
        assert active is True
        mock_mc.setBlock.assert_called_with(10, 60, 10, block.AIR.id)
        assert inv[1] == 1
        assert strategy.current_x == 1

    @pytest.mark.asyncio
    async def test_mine_air_block(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.return_value = block.AIR.id
        inv = {}
        
        active = await strategy.mine({}, inv, start_pos)
        
        assert active is True
        mock_mc.setBlock.assert_not_called()
        assert len(inv) == 0
        assert strategy.current_x == 1

    @pytest.mark.asyncio
    async def test_loop_progression(self, strategy, mock_mc):
        start_pos = {'x': 0, 'y': 0, 'z': 0}
        mock_mc.getBlock.return_value = 0
        
        # Advance x to width-1
        strategy.current_x = strategy.width - 1
        strategy.current_z = 0
        strategy.current_y = 0
        
        await strategy.mine({}, {}, start_pos)
        assert strategy.current_x == 0
        assert strategy.current_z == 1
        assert strategy.current_y == 0
        
        # Advance z to length-1
        strategy.current_x = strategy.width - 1
        strategy.current_z = strategy.length - 1
        strategy.current_y = 0
        
        await strategy.mine({}, {}, start_pos)
        assert strategy.current_x == 0
        assert strategy.current_z == 0
        assert strategy.current_y == 1

    @pytest.mark.asyncio
    async def test_completion(self, strategy, mock_mc):
        strategy.current_y = strategy.height
        active = await strategy.mine({}, {}, {'x':0, 'y':0, 'z':0})
        assert active is False

    @pytest.mark.asyncio
    async def test_error_handling(self, strategy, mock_mc, mock_logger):
        mock_mc.getBlock.side_effect = Exception("Grid error")
        await strategy.mine({}, {}, {'x':0, 'y':0, 'z':0})
        mock_logger.error.assert_called()
        # Should continue
        assert strategy.current_x == 1


class TestVerticalStrategy:

    @pytest.fixture
    def strategy(self, mock_mc, mock_logger):
        return VerticalStrategy(mock_mc, mock_logger, "Agent1")

    @pytest.mark.asyncio
    async def test_mine_normal(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.return_value = 1
        inv = {}
        
        active = await strategy.mine({}, inv, start_pos)
        
        assert active is True
        mock_mc.setBlock.assert_called_with(10, 60, 10, block.AIR.id)
        assert inv[1] == 1
        assert strategy.current_depth == 1

    @pytest.mark.asyncio
    async def test_mine_bedrock(self, strategy, mock_mc):
        mock_mc.getBlock.return_value = block.BEDROCK.id
        active = await strategy.mine({}, {}, {'x':10,'y':10,'z':10})
        assert active is False
        assert strategy.bedrock_hit is True

    @pytest.mark.asyncio
    async def test_max_depth(self, strategy):
        strategy.current_depth = strategy.max_depth
        active = await strategy.mine({}, {}, {'x':0,'y':0,'z':0})
        assert active is False

    @pytest.mark.asyncio
    async def test_error_handling(self, strategy, mock_mc, mock_logger):
        mock_mc.getBlock.side_effect = Exception("Vert Error")
        active = await strategy.mine({}, {}, {'x':0,'y':0,'z':0})
        assert active is False
        mock_logger.error.assert_called()


class TestVeinStrategy:

    @pytest.fixture
    def strategy(self, mock_mc, mock_logger):
        return VeinStrategy(mock_mc, mock_logger, "Miner1")
    
    @pytest.mark.asyncio
    async def test_mine_found_immediately(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.return_value = 14 
        
        result = await strategy.mine({}, {}, start_pos)
        
        assert strategy.target_id == 14
        assert len(strategy.queue) == 6 
        assert strategy.searching is False
        assert result is True

    @pytest.mark.asyncio
    async def test_mine_found_adjacent(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        def side_effect(x, y, z):
            if x == 10 and y == 60 and z == 10: return block.AIR.id
            if x == 11: return 15
            return 0
        mock_mc.getBlock.side_effect = side_effect
        
        result = await strategy.mine({}, {}, start_pos)
        
        assert strategy.target_id == 15
        assert len(strategy.queue) == 6
        assert strategy.searching is False
        assert result is True

    @pytest.mark.asyncio
    async def test_mine_not_found(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.return_value = block.AIR.id
        result = await strategy.mine({}, {}, start_pos)
        assert strategy.target_id is None
        assert strategy.searching is False
        assert result is False

    @pytest.mark.asyncio
    async def test_mine_process_queue(self, strategy, mock_mc):
        strategy.searching = False
        strategy.target_id = 14
        strategy.queue = [(10, 60, 10)]
        mock_mc.getBlock.return_value = 14
        
        inv = {}
        result = await strategy.mine({}, inv, {})
        
        assert inv[14] == 1
        mock_mc.setBlock.assert_called_with(10, 60, 10, block.AIR.id)
        assert len(strategy.queue) == 6
        assert result is True

    @pytest.mark.asyncio
    async def test_mine_process_queue_visited(self, strategy, mock_mc):
        strategy.searching = False
        strategy.target_id = 14
        strategy.queue = [(10, 60, 10)]
        strategy.visited.add((10, 60, 10))
        
        result = await strategy.mine({}, {}, {})
        

    @pytest.mark.asyncio
    async def test_mine_exception_at_start(self, strategy, mock_mc, mock_logger):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        mock_mc.getBlock.side_effect = Exception("Connection error")
        
        result = await strategy.mine({}, {}, start_pos)
        
        mock_logger.error.assert_called()
        assert result is False

    @pytest.mark.asyncio
    async def test_mine_process_queue_exception(self, strategy, mock_mc, mock_logger):
        strategy.searching = False
        strategy.target_id = 14
        strategy.queue = [(10, 60, 10)]
        mock_mc.getBlock.side_effect = Exception("Mining error")
        
        result = await strategy.mine({}, {}, {})
        
        mock_logger.error.assert_called()
        assert result is True

    @pytest.mark.asyncio
    async def test_mine_finished(self, strategy):
        strategy.searching = False
        strategy.queue = []
        
        result = await strategy.mine({}, {}, {})
        
        assert result is False

    @pytest.mark.asyncio
    async def test_mine_bom_filtering(self, strategy, mock_mc):
        start_pos = {'x': 10, 'y': 60, 'z': 10}
        # Center is AIR
        # Adjacent block 15 (e.g. Iron)
        def side_effect(x, y, z):
            if x == 10 and y == 60 and z == 10: return block.AIR.id
            if x == 11: return 15
            return 0
        mock_mc.getBlock.side_effect = side_effect
        
        # BOM searching only for Gold (14)
        target_bom = {14: 10}
        
        result = await strategy.mine(target_bom, {}, start_pos)
        
        # Should not pick Iron (15) because it's not in BOM
        assert strategy.target_id is None
        assert result is False
