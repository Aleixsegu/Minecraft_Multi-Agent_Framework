import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from agents.miner_bot import MinerBot
from agents.state_model import State

class TestMinerBot:
    
    @pytest.fixture
    def bot(self, mock_mc, message_bus):
        bot = MinerBot("Miner_Test", mock_mc, message_bus)
        bot.logger = MagicMock()
        bot.strategy = MagicMock() 
        return bot

    @pytest.mark.asyncio
    async def test_process_bom_resets_inventory(self, bot):
        payload = {
            "requirements": {"stone": 10, "diamond": 1},
            "build_position": (10, 64, 10)
        }
        with patch('agents.miner_bot.get_block_id', return_value=1):
             bot._process_bom(payload)
             await asyncio.sleep(0) 
             
        assert bot.context['requirements']['stone'] == 10
        assert bot.context['inventory'] == {'stone': 0, 'diamond': 0}
        assert bot.context['mining_active'] is True

    @pytest.mark.asyncio
    async def test_process_bom_unknown_blocks(self, bot):
        payload = {
            "requirements": {"unknown_block": 5},
            "build_position": (0,0)
        }
        # get_block_id returns None for unknown
        with patch('agents.miner_bot.get_block_id', return_value=None):
             bot._process_bom(payload)
             await asyncio.sleep(0)
        
        # Should be in requirements but not in inventory_ids maybe?
        assert "unknown_block" in bot.context['requirements']
        # Implementation detail: logic might skip IDs if None
        assert bot.context['mining_active'] is True

    @pytest.mark.asyncio
    async def test_decide_priorities(self, bot):
        bot.state = State.RUNNING
        bot.context['mining_active'] = True
        bot.context['requirements'] = {'bedrock': 5, 'stone': 10}
        
        # Case 1: Not arrived
        bot.context['arrived_at_mine'] = False
        bot.context['target_x'] = 100
        await bot.decide()
        assert bot.context['next_action'] == 'initial_mine'
        
        # Case 2: Arrived, Creative
        bot.context['arrived_at_mine'] = True
        bot.context['tasks_physical'] = {}
        bot.context['tasks_creative'] = {'bedrock': 1}
        bot.context['inventory'] = {'bedrock': 0}
        await bot.decide()
        assert bot.context['next_action'] == 'mine_creative'

        # Case 3: Physical
        bot.context['tasks_creative'] = {}
        bot.context['tasks_physical'] = {'stone': 10}
        bot.context['inventory'] = {'stone': 0}
        
        bot.context['has_lock'] = True
        await bot.decide()
        assert bot.context['next_action'] == 'mine_physical'
        
        # Case 4: Finished
        bot.context['inventory'] = {'stone': 10, 'bedrock': 5}
        await bot.decide()
        assert bot.context['next_action'] == 'finish_delivery'

    @pytest.mark.asyncio
    async def test_act_mine_with_interrupt(self, bot):
        bot.context['next_action'] = 'mine_physical'
        bot.context['interrupt'] = True
        
        # If interrupted, act might return early or log
        await bot.act()
        # Verify no mining calls happened
        bot.strategy.mine.assert_not_called()

    @pytest.mark.asyncio
    async def test_act_mine_physical(self, bot):
        bot.context['next_action'] = 'mine_physical'
        bot.context['target_x'] = 0
        bot.context['target_z'] = 0
        bot.context['target_y'] = 64
        bot.context['interrupt'] = False
        bot.strategy.mine = AsyncMock(return_value=True)
        
        await bot.act()
        bot.strategy.mine.assert_called()

    @pytest.mark.asyncio
    async def test_act_initial_mine(self, bot):
        bot.context['next_action'] = 'initial_mine'
        bot.context['target_x'] = 100
        bot.context['target_z'] = 100
        bot.mc.getHeight.return_value = 70
        
        await bot.act()
        assert bot.context['target_y'] == 70
        assert bot.context['arrived_at_mine'] is True
        
    @pytest.mark.asyncio
    async def test_perceive_locks(self, bot):
        bot.bus.receive = AsyncMock()
        msg_lock = {"type": "region.lock.v1", "source": "Other", "payload": {"zone": {"x":0, "z":0, "radius":10}}}
        bot.bus.receive.return_value = msg_lock
        await bot.perceive()
        assert len(bot.context['forbidden_zones']) == 1

    @pytest.mark.asyncio
    async def test_act_mine_physical_grid_timeout(self, bot):
        bot.context['next_action'] = 'mine_physical'
        bot.strategy.__class__.__name__ = "GridStrategy"
        bot.context['mining_start_time'] = 1000
        bot.bus.publish = AsyncMock()
        
        with patch('time.time', return_value=1301):
            bot.context['requirements'] = {'stone': 10}
            bot.context['tasks_physical'] = {'stone': 10}
            bot.context['inventory'] = {}
            await bot.act()
            assert bot.context['inventory']['stone'] == 10
            bot.bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_act_mine_physical_vertical_limit(self, bot):
        bot.context['next_action'] = 'mine_physical'
        bot.strategy.__class__.__name__ = "VerticalStrategy"
        bot.context['target_y'] = 64
        bot.strategy.mine = AsyncMock(return_value=False)
        bot.bus.publish = AsyncMock()
        
        bot.context['mining_attempts'] = 4
        await bot.act()
        assert bot.context['mining_attempts'] == 5
        bot.bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_wait_zone(self, bot):
        bot.context['next_action'] = 'wait_zone'
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
             await bot.act()
             mock_sleep.assert_called()
             
    @pytest.mark.asyncio
    async def test_random_zone_calculation(self, bot):
        bot.context['home_x'] = 0
        bot.context['home_z'] = 0
        bot._calculate_random_zone()
        assert 50 <= abs(bot.context['target_x']) <= 100

    @pytest.mark.asyncio
    async def test_handle_command_fulfill(self, bot):
        bot.bom_received = True
        await bot.handle_command("fulfill")
        assert bot.state == State.RUNNING

    @pytest.mark.asyncio
    async def test_handle_command_start_manual(self, bot):
        bot.checkpoint = MagicMock()
        await bot.handle_command("start", {"x": 50, "z": 50})
        assert bot.context['target_x'] == 50

    @pytest.mark.asyncio
    async def test_handle_command_set_strategy(self, bot):
        with patch('agents.miner_bot.MinerBot.load_strategy_dynamically') as mock:
            await bot.handle_command("set", {"strategy": "Vertical"})
            mock.assert_called()
            
    def test_load_strategy_dynamically(self, bot):
        mock_cls = MagicMock()
        mock_cls.__name__ = "MockStrat"
        with patch('utils.reflection.get_all_strategies', return_value={"MockStrat": mock_cls}):
             bot.load_strategy_dynamically("Mock")
             assert isinstance(bot.strategy, MagicMock)