import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from agents.BaseAgent import BaseAgent
from agents.state_model import State

# Implementación concreta para probar BaseAgent
class ConcreteAgent(BaseAgent):
    async def perceive(self):
        self.context["perceived"] = True

    async def decide(self):
        self.context["decided"] = True

    async def act(self):
        self.context["acted"] = True

@pytest.fixture
def mock_deps():
    return {
        "mc": MagicMock(),
        "bus": MagicMock(),
    }

@pytest.fixture
def agent(mock_deps):
    # Mockear Checkpoints y Logger
    # Usamos spec=False para que MockLogger acepte cualquier llamada, 
    # ya que si usamos spec=Logger real, tendríamos que importar la clase real
    # y si esta cambia, el test falla. MagicMock por defecto acepta todo.
    with patch("agents.BaseAgent.Checkpoints") as MockCheckpoints, \
         patch("agents.BaseAgent.Logger") as MockLoggerClass:
        
        MockCheckpoints.return_value.load.return_value = {}
        
        # Forzar que el return_value sea un MagicMock puro
        MockLoggerClass.return_value = MagicMock()
        
        ag = ConcreteAgent("TestAgent", mock_deps["mc"], mock_deps["bus"])
        
        print(f"DEBUG: Agent logger type: {type(ag.logger)}")
        print(f"DEBUG: Agent logger dir: {dir(ag.logger)}")
        
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

@pytest.mark.asyncio
async def test_handle_command_stop(agent):
    # Stop debe guardar checkpoint
    await agent.handle_command("stop")
    assert agent.state == State.STOPPED
    agent.checkpoint.save.assert_called()

@pytest.mark.asyncio
async def test_handle_command_update(agent):
    payload = {"param": 10}
    await agent.handle_command("update", payload)
    assert agent.context["param"] == 10
    assert agent.state == State.RUNNING

@pytest.mark.asyncio
async def test_run_cycle_execution(agent):
    """
    Verifica que en estado RUNNING se ejecuten perceive, decide y act.
    """
    # 1. Iniciamos el bucle principal en segundo plano
    # Nota: run() inicializa el estado a IDLE automáticamente
    task = asyncio.create_task(agent.run())
    
    # Damos un momento para que run() llegue al bucle while y se ponga en IDLE
    await asyncio.sleep(0.01)
    
    # 2. Cambiamos el estado a RUNNING (como si recibiera orden de empezar)
    await agent.set_state(State.RUNNING)
    
    # 3. Dejamos que corra al menos un ciclo (aumentamos tiempo)
    await asyncio.sleep(0.2)
    
    # 4. Verificaciones
    print(f"DEBUG: Agent State: {agent.state}, Context: {agent.context}")
    assert agent.state == State.RUNNING, f"Agent should be RUNNING but is {agent.state}"
    assert agent.context.get("perceived") is True
    assert agent.context.get("decided") is True
    assert agent.context.get("acted") is True
    
    # 5. Limpieza
    await agent.set_state(State.STOPPED)
    await task
