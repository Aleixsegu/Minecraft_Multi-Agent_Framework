import pytest
from unittest.mock import MagicMock
from agents.AgentFactory import AgentFactory
from agents.BaseAgent import BaseAgent

# Mock concreto para usar en los tests
class MockAgent(BaseAgent):
    async def perceive(self): pass
    async def decide(self): pass
    async def act(self): pass

@pytest.fixture
def factory():
    # Reiniciar el singleton para cada test si es necesario, 
    # o simplemente limpiar el registro
    f = AgentFactory()
    f._agent_registry.clear()
    return f

def test_singleton_behavior():
    f1 = AgentFactory()
    f2 = AgentFactory()
    assert f1 is f2

def test_register_valid_agent(factory):
    factory.register_agent_class("MockAgent", MockAgent)
    assert "MockAgent" in factory.list_available_agents()

def test_register_invalid_agent_raises_error(factory):
    class InvalidClass: pass
    with pytest.raises(ValueError):
        factory.register_agent_class("Invalid", InvalidClass)

def test_create_agent(factory):
    factory.register_agent_class("MockAgent", MockAgent)
    
    mc_mock = MagicMock()
    bus_mock = MagicMock()
    
    agent = factory.create_agent("MockAgent", mc_mock, bus_mock, agent_id="MyAgent1")
    
    assert isinstance(agent, MockAgent)
    assert agent.id == "MyAgent1"
    assert agent.mc == mc_mock
    assert agent.bus == bus_mock

def test_create_unregistered_agent_raises_error(factory):
    with pytest.raises(ValueError, match="Tipo de Agente no registrado"):
        factory.create_agent("GhostAgent", None, None)
