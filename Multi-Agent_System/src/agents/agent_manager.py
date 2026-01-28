import asyncio
from utils.logging import Logger
from agents.agent_factory import AgentFactory
from agents.workflow_manager import WorkflowManager

class AgentManager:
    """
    Gestiona el ciclo de vida de los agentes (creación, etc.)
    escuchando comandos del MessageBus.
    """

    def __init__(self, mc, message_bus):
        self.mc = mc
        self.bus = message_bus
        self.logger = Logger(self.__class__.__name__)
        self.logger.info("AgentManager inicializado.")
        self.factory = AgentFactory()
        
        self.agents_map = {} 
        
        self.workflow_manager = WorkflowManager(self)
        
        self.running = True

    def setup_subscriptions(self):
        """Se suscribe a los eventos de creación."""
        self.bus.register_agent(self.__class__.__name__)
        self.bus.subscribe(self.__class__.__name__, "command.create.v1")
        self.bus.subscribe(self.__class__.__name__, "command.workflow.run")

    async def run(self):
        """Bucle principal de escucha."""

        self.setup_subscriptions()

        while self.running:
            try:
                msg = await self.bus.receive(self.__class__.__name__)
                await self.handle_message(msg)
            except Exception as e:
                self.logger.error(f"Error en AgentManager loop: {e}")
                await asyncio.sleep(1)

    async def handle_message(self, msg):
        """Procesa el mensaje."""
        msg_type = msg.get("type")
        payload = msg.get("payload", {})
        target = msg.get("target") 

        if msg_type == "command.create.v1":
            await self.handle_create_command(target, payload)
        elif msg_type == "command.workflow.run":
             command_str = payload.get("command_str", "")
             await self.workflow_manager.execute_workflow(command_str)

    def get_agent(self, agent_id):
        return self.agents_map.get(agent_id)

    async def create_agent(self, agent_type, agent_id):
        """Public method to create agent programmatically."""
        if agent_id in self.agents_map:
            self.logger.info(f"Agent {agent_id} already exists.")
            return self.agents_map[agent_id]

        try:
            new_agent = self.factory.create_agent(agent_type, self.mc, self.bus, agent_id=agent_id)
            asyncio.create_task(new_agent.run())
            
            self.agents_map[agent_id] = new_agent
            
            success_msg = f"Agente creado: {agent_id} ({agent_type})"
            self.logger.info(success_msg)
            self.mc.postToChat(success_msg)
            return new_agent
        except Exception as e:
            self.logger.error(f"Failed to create agent {agent_id}: {e}")
            return None

    async def handle_create_command(self, target_type_str, payload):
        """
        Wrapper for command-based creation.
        """
        agent_type = payload.get("agent_type", target_type_str)
        new_id = payload.get("id") or payload.get("name")
        
        if not new_id:
            import uuid
            new_id = f"{agent_type}_{str(uuid.uuid4())[:4]}"

        self.logger.info(f"Solicitud de creacion recibida: Tipo={agent_type}, ID={new_id}")

        await self.create_agent(agent_type, new_id)
