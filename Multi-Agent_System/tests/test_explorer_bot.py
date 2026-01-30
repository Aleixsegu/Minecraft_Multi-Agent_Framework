import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, call
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from agents.explorer_bot import ExplorerBot
from agents.state_model import State

@pytest.fixture
def bot(mock_mc, message_bus):
    bot = ExplorerBot("Explorer_Test", mock_mc, message_bus)
    bot.logger = MagicMock()
    return bot

class TestExplorerBot:
    
    def test_decompose_to_rectangles(self, bot):
        coords = [(0,0), (1,0), (2,0), (0,1), (1,1), (2,1), (0,2), (1,2), (2,2)]
        rects = bot._decompose_to_rectangles(coords, 0, 0, 2, 2)
        assert len(rects) == 1
        assert rects[0]['size'] == (3,3)

    @pytest.mark.asyncio
    async def test_handle_command_start(self, bot):
        bot.mc.player.getTilePos.return_value = MagicMock(x=10, y=64, z=10)
        await bot.handle_command("start", {"x": 100, "z": 100, "range": 5})
        assert bot.context['target_x'] == 100
        assert bot.state == State.RUNNING

    @pytest.mark.asyncio
    async def test_handle_command_set(self, bot):
        await bot.handle_command("set", {"range": 50})
        assert bot.range == 50
        await bot.handle_command("set", {}) 
        bot.mc.postToChat.assert_called()

    @pytest.mark.asyncio
    async def test_decide_logic(self, bot):
        bot.state = State.RUNNING
        bot.context['target_x'] = 0
        bot.context['target_z'] = 0
        bot.context['scan_complete'] = False
        await bot.decide()
        assert bot.context['next_action'] == 'scan_environment'
        
        bot.context['scan_complete'] = True
        bot.context['report_sent'] = False
        await bot.decide()
        assert bot.context['next_action'] == 'report_zones'
        
        bot.context['report_sent'] = True
        await bot.decide()
        assert bot.context['next_action'] == 'finish_mission'

    @pytest.mark.asyncio
    async def test_act_execution(self, bot):
        bot.context['next_action'] = 'scan_environment'
        with patch.object(bot, '_scan_task_wrapper') as mock_scan:
            await bot.act()
        
        bot.context['next_action'] = 'finish_mission'
        await bot.act()
        assert bot.state == State.IDLE

    @pytest.mark.asyncio
    async def test_scan_and_find_zones_mocked(self, bot):
        bot.context['target_x'] = 0
        bot.context['target_z'] = 0
        bot.range = 2 
        bot.mc.getHeight.return_value = 64
        bot.bus.publish = AsyncMock()
        await bot._scan_and_find_zones()
        assert bot.context['scan_complete'] is True
        bot.bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_scan_pausing(self, bot):
        bot.context['target_x'] = 0
        bot.context['target_z'] = 0
        bot.range = 10
        bot.mc.getHeight.return_value = 64
        bot.context['paused'] = True
        await bot._scan_and_find_zones()
        assert 'scan_state' in bot.context
        assert bot.context['scan_state']['has_state'] is True
        
    @pytest.mark.asyncio
    async def test_resume_command(self, bot):
        state_data = {
            "state": "PAUSED",
            "task_state": {},
            "context": {"scan_state": {"has_state": True}}
        }
        bot.checkpoint = MagicMock()
        bot.checkpoint.load.return_value = state_data
        await bot.handle_command("resume")
        assert bot.state == State.RUNNING
        assert bot.context['paused'] is False
        
    @pytest.mark.asyncio
    async def test_load_scan_state_complex(self, bot):
        # Setup complex state data in context to test _load_scan_state logic
        complex_state = {
            "has_state": True,
            "stats": {
                "0,0": {"coords": [[0,0], [1,1]]} # Str key -> list
            },
            "parent": {
                "1,1": "0,0" # Str key -> Str val
            },
            "prev_col_labels": {
                "10": "5,5" # Int key as str -> Str val
            },
            "active_roots": ["0,0", "1,1"], # List of strs
            "curr_col_labels": {"5": "2,2"},
            "active_roots_this_col": ["2,2"],
            "resume_x": 10,
            "resume_z": 20
        }
        bot.context['scan_state'] = complex_state
        
        # We can call internal method directly to verify
        # (Assuming it's not private-private, but it is _load...)
        result = bot._load_scan_state()
        
        assert result is not None
        stats, parent, active_roots, prev_col_labels, curr_col_labels, active_roots_col, rx, rz = result
        
        assert (0,0) in stats
        assert isinstance(stats[(0,0)]['coords'][0], tuple)
        assert parent[(1,1)] == (0,0)
        assert prev_col_labels[10] == (5,5)
        assert (0,0) in active_roots
        assert curr_col_labels[5] == (2,2)
        assert rx == 10

    @pytest.mark.asyncio
    async def test_handle_command_stop(self, bot):
        bot.context["scanning_in_progress"] = True
        async def stop_bg():
             await asyncio.sleep(0.01)
             bot.context["scanning_in_progress"] = False
        asyncio.create_task(stop_bg())
        await bot.handle_command("stop")
        assert bot.state == State.STOPPED
        assert bot.context['interrupt'] is True

    @pytest.mark.asyncio
    async def test_handle_command_misc(self, bot):
        bot.mc.postToChat = MagicMock()
        await bot.handle_command("help")
        bot.mc.postToChat.assert_called()
        await bot.handle_command("status")
        bot.mc.postToChat.assert_called()
        bot.state = State.RUNNING
        await bot.handle_command("start")
        assert "Ya estoy en ejecucion" in bot.mc.postToChat.call_args[0][0]

    @pytest.mark.asyncio
    async def test_scan_task_wrapper_error(self, bot):
        bot.context['scanning_in_progress'] = True
        with patch.object(bot, '_scan_and_find_zones', side_effect=Exception("Scan Crash")):
             await bot._scan_task_wrapper()
        assert bot.context['scanning_in_progress'] is False

    @pytest.mark.asyncio
    async def test_perceive_ignores(self, bot):
        bot.bus.receive = AsyncMock()
        bot.bus.receive.side_effect = asyncio.TimeoutError()
        await bot.perceive() 
        
        msg = {"source": bot.id, "target": "BROADCAST"}
        bot.bus.receive.side_effect = None
        bot.bus.receive.return_value = msg
        with patch('asyncio.wait_for', return_value=msg):
             await bot.perceive()
        
        msg = {"source": "Unknown", "target": "BROADCAST", "type": "test"}
        with patch('asyncio.wait_for', return_value=msg):
             await bot.perceive()