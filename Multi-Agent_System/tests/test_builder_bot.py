import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))
from agents.builder_bot import BuilderBot
from agents.state_model import State

@pytest.fixture
def mock_structure_class():
    m = MagicMock()
    m.width = 10
    m.length = 10
    m.get_bom.return_value = {"stone": 5}
    m.get_blocks.return_value = [
        {'x': 0, 'y': 0, 'z': 0, 'block': "minecraft:stone"},
        {'x': 1, 'y': 0, 'z': 1, 'block': "minecraft:dirt"}  
    ]
    return m

@pytest.fixture
def bot(mock_mc, message_bus):
    bot = BuilderBot("Builder_Test", mock_mc, message_bus)
    bot.logger = MagicMock()
    return bot

@pytest.mark.asyncio
async def test_initialization(bot):
    assert bot.context['task_phase'] == 'IDLE'

@pytest.mark.asyncio
async def test_handle_command_plan_list(bot):
    with patch('agents.builder_bot.get_all_structures') as mock_get:
        mock_get.return_value = {"house": 1, "tower": 2}
        
        await bot.handle_command("plan", {"args": ["list"], "id": bot.id})
        bot.mc.postToChat.assert_called()
        assert "house" in bot.mc.postToChat.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_command_plan_set_success(bot):
    with patch('agents.builder_bot.get_all_structures') as mock_get:
        mock_get.return_value = {"house": 1}
        
        await bot.handle_command("plan", {"args": ["set", "house"]})
        assert bot.context['current_plan'] == "house"
        assert "Plan establecido" in bot.logger.info.call_args[0][0]

@pytest.mark.asyncio
async def test_handle_command_build(bot):
    # Sin plan
    bot.context['current_plan'] = None
    await bot.handle_command("build")
    bot.mc.postToChat.assert_called_with(f"[{bot.id}] No hay plan. Usa 'plan set' primero.")
    
    # Con plan pero sin mapa
    bot.context['current_plan'] = "house"
    bot.context['latest_map'] = None
    await bot.handle_command("build")
    assert "Esperando el mapa" in bot.mc.postToChat.call_args[0][0]
    
    # Con plan y mapa
    bot.context['latest_map'] = {"ready": True}
    await bot.handle_command("build")
    assert bot.context['task_phase'] == 'ANALYZING_MAP'

@pytest.mark.asyncio
async def test_perceive_map(bot):
    bot.context['current_plan'] = "house"
    bot.context['task_phase'] = "IDLE"
    
    msg = {
        "type": "map.v1", 
        "source": "ExplorerBot", 
        "payload": {"center": [0,0]},
        "target": "BROADCAST"
    }
    
    bot.bus.receive = AsyncMock(return_value=msg)
    
    # Simulate perceive loop one iteration
    with patch('asyncio.wait_for', side_effect=[msg, asyncio.TimeoutError()]):
        await bot.perceive()
    
    assert bot.context['latest_map'] == msg['payload']
    assert bot.context['task_phase'] == "ANALYZING_MAP"

@pytest.mark.asyncio
async def test_decide_analyzing_map(bot, mock_structure_class):
    bot.state = State.RUNNING
    bot.context['task_phase'] = 'ANALYZING_MAP'
    bot.context['current_plan'] = "house"
    bot.context['latest_map'] = {"size": (20, 20), "origin": (100, 100), "average_height": 64}
    
    with patch('agents.builder_bot.get_all_structures', return_value={"house": mock_structure_class}):
        await bot.decide()
        
    assert bot.context['target_position'] == (100, 100)
    assert bot.context['next_action'] == 'request_materials'
    assert len(bot.context['blocks_to_build']) == 2
    
@pytest.mark.asyncio
async def test_decide_waiting_materials(bot):
    bot.context['task_phase'] = 'WAITING_MATERIALS'
    bot.context['requirements'] = {"stone": 5}
    
    # Materiales insuficientes
    bot.context['inventory'] = {"stone": 2}
    await bot.decide()
    assert bot.context['next_action'] == 'wait_materials'
    
    # Materiales suficientes
    bot.context['inventory'] = {"stone": 10}
    await bot.decide()
    assert bot.context['next_action'] == 'start_building'

@pytest.mark.asyncio
async def test_act_start_building(bot):
    bot.context['next_action'] = 'start_building'
    bot.context['blocks_to_build'] = [{'x':0, 'y':0, 'z':0, 'block': 'stone'}]
    bot.context['target_position'] = (10, 10)
    bot.context['target_height'] = 64
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with patch('agents.builder_bot.get_block_id', return_value=1):
             with patch.object(bot, '_build_structure_task') as mock_task:
                 await bot.act()
                 # Task should be launched. We need to verify task_phase change if it happens synchronously or via task
                 # Here we only test that it branches correctly.

@pytest.mark.asyncio
async def test_act_wait_materials(bot):
    bot.context['next_action'] = 'wait_materials'
    with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        await bot.act()
        # act does not sleep itself, it just returns
        pass

@pytest.mark.asyncio
async def test_act_request_materials(bot):
    bot.context['next_action'] = 'request_materials'
    bot.context['requirements'] = {"stone": 5}
    bot.context['target_position'] = (100, 100)
    
    bot.bus.publish = AsyncMock()
    await bot.act()
    
    bot.bus.publish.assert_called()
    assert bot.context['task_phase'] == 'WAITING_MATERIALS'

@pytest.mark.asyncio
async def test_build_structure_task_logic(bot):
    bot.context['blocks_to_build'] = [{'x':0, 'y':0, 'z':0, 'block': 'stone'}]
    bot.context['target_position'] = (0, 0)
    bot.context['target_height'] = 10
    bot.context['build_index'] = 0
    bot.context['building_in_progress'] = True # Must set this true to enter loop
    
    with patch('asyncio.sleep', new_callable=AsyncMock):
        with patch('agents.builder_bot.get_block_id', return_value=1):
             await bot._build_structure_task()
    
    bot.mc.setBlock.assert_called_with(0, 10, 0, 1)
    assert bot.context['task_phase'] == 'IDLE'

@pytest.mark.asyncio
async def test_build_structure_task_pause(bot):
    bot.context['blocks_to_build'] = [
        {'x':0, 'y':0, 'z':0, 'block': 'stone'}, 
        {'x':1, 'y':0, 'z':0, 'block': 'stone'}
    ]
    bot.context['target_position'] = (0, 0)
    bot.context['target_height'] = 10
    
    # Scenario 1: Pause triggered during build
    bot.context['build_index'] = 0
    bot.context['building_in_progress'] = True
    
    with patch('agents.builder_bot.get_block_id', return_value=1):
        # We simulate pause setting via side effect or just mocking state check inside loop?
        # The loop checks `if self.context.get('paused'): ...`
        
        # We'll make the first setBlock trigger a pause change? No, it's async loop.
        # We can just test that if paused is True, it waits.
        pass
    
    # Scenario 2: Started paused
    bot.context['paused'] = True
    bot.context['build_index'] = 0
    bot.context['building_in_progress'] = True
    bot.mc.setBlock.reset_mock()
    
    # We need to break the loop or it will run forever. 
    # Force building_in_progress = False after some sleep?
    async def side_effect_sleep(*args):
        bot.context['building_in_progress'] = False
    
    with patch('asyncio.sleep', side_effect=side_effect_sleep):
         await bot._build_structure_task()
         
    bot.mc.setBlock.assert_not_called()

@pytest.mark.asyncio
async def test_bom_command(bot, mock_structure_class):
    # Invalid plan
    bot.context['current_plan'] = "nonexistent"
    with patch('agents.builder_bot.get_all_structures', return_value={}):
        await bot.handle_command("bom")
        # Ensure postToChat was called
        if bot.mc.postToChat.called:
             args = bot.mc.postToChat.call_args[0][0]
             assert "no tiene BOM" in args or "No hay plan" in args

    # Valid plan (reset mock if needed)
    bot.context['current_plan'] = "house"
    with patch('agents.builder_bot.get_all_structures', return_value={"house": mock_structure_class}):
         await bot.handle_command("bom")
         bot.mc.postToChat.assert_called()
         args = bot.mc.postToChat.call_args[0][0]
         assert "BOM para house" in args

@pytest.mark.asyncio
async def test_handle_command_overrides(bot):
    # Stop
    bot.context['building_in_progress'] = False 
    await bot.handle_command("stop")
    assert bot.state == State.STOPPED
    assert bot.context['interrupt'] is True
    
    # Pause
    await bot.handle_command("pause")
    assert bot.state == State.PAUSED
    assert bot.context['paused'] is True
    
    # Resume
    bot.checkpoint = MagicMock()
    bot.checkpoint.load.return_value = {"current_plan": "castle"}
    await bot.handle_command("resume")
    assert bot.state == State.RUNNING
    assert bot.context['paused'] is False
    assert bot.context['current_plan'] == "castle"

@pytest.mark.asyncio
async def test_process_inventory_msg(bot):
    bot.bus.receive = AsyncMock()
    msg = {
        "type": "inventory.v1",
        "source": "MinerBot",
        "payload": {"stone": 10},
        "target": bot.id
    }
    
    bot.context['task_phase'] = 'WAITING_MATERIALS'
    
    # Simulate one message then stop
    bot.bus.receive.return_value = msg
    with patch('asyncio.wait_for', side_effect=[msg, asyncio.TimeoutError()]):
         await bot.perceive()
         
    assert bot.context['inventory'] == {"stone": 10}

@pytest.mark.asyncio
async def test_decide_idle(bot):
    bot.context['task_phase'] = 'IDLE'
    await bot.decide()
    assert bot.context['next_action'] == 'idle'
    
    bot.context['task_phase'] = 'BUILDING'
    bot.context['building_in_progress'] = True
    await bot.decide()
    assert bot.context['next_action'] == 'wait_for_build'
