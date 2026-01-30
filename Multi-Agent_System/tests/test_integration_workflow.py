import pytest
from unittest.mock import AsyncMock, MagicMock
from agents.workflow_manager import WorkflowManager
from agents.state_model import State

@pytest.mark.integration
@pytest.mark.asyncio
class TestIntegrationWorkflow:

    async def test_workflow_execution_flow(self, agent_manager):
        """
        Prueba que el WorkflowManager orqueste la creación y configuración
        de los 3 agentes principales.
        """
        # Mockear la creación de agentes para no instanciar lógica real compleja
        mock_explorer = AsyncMock()
        mock_explorer.state = State.IDLE # Importante para evitar esperas infinitas
        
        mock_builder = AsyncMock()
        mock_miner = AsyncMock()
        
        # Override del método create_agent del manager real
        agent_manager.create_agent = AsyncMock(side_effect=[
            mock_explorer, mock_builder, mock_miner
        ])
        # Override de get_agent para simular que no existen al principio
        agent_manager.get_agent = MagicMock(return_value=None)

        wf_manager = WorkflowManager(agent_manager)
        
        # Ejecutar comando
        cmd = "x=100 z=200 range=50 template=house miner.strategy=grid"
        await wf_manager.execute_workflow(cmd)

        # Validaciones de Integración
        # 1. Se configuró el Minero?
        # Aceptamos cualqier llamada o especificamos silent=True si es lo que ocurre
        mock_miner.handle_command.assert_any_call("set", {"strategy": "grid", "silent": True})
        # 2. Se configuró el Builder?
        mock_builder.handle_command.assert_any_call("plan", {"args": ["set", "house"], "silent": True})
        # 3. Se disparó el Explorer al final?
        # Verificar que recibió un DICCIONARIO y no una lista (el fix que hicimos)
        call_args = mock_explorer.handle_command.call_args[0]
        assert call_args[0] == "start"
        assert isinstance(call_args[1], dict)
        assert call_args[1]["x"] == 100