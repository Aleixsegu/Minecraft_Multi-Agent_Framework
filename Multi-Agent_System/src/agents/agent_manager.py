import asyncio
from utils.logging import Logger
from agents.agent_factory import AgentFactory

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
        self.active_agents = set()
        self.running = True

    def setup_subscriptions(self):
        """Se suscribe a los eventos de creación."""

        self.bus.register_agent(self.__class__.__name__)
        self.bus.subscribe(self.__class__.__name__, "command.create.v1")
        self.logger.info("AgentManager suscrito a command.create.v1")

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
        """Procesa el mensaje de creación."""

        msg_type = msg.get("type")
        payload = msg.get("payload", {})
        target = msg.get("target") 

        if msg_type == "command.create.v1":
            await self.handle_create_command(target, payload)

    async def handle_create_command(self, target_type_str, payload):
        """
        Crea el agente solicitado.
        target_type_str: 'ExplorerBot', 'MinerBot', etc.
        """
        
        agent_type = target_type_str
        new_id = payload.get("id") or payload.get("name")
        
        if not new_id:
            import uuid
            new_id = f"{agent_type}_{str(uuid.uuid4())[:4]}"

        self.logger.info(f"Solicitud de creacion recibida: Tipo={agent_type}, ID={new_id}")

        # Comprobación de duplicados
        # Comprobación de duplicados
        if (agent_type, new_id) in self.active_agents:
            msg = f"El agente de tipo '{agent_type}' con ID '{new_id}' ya existe. Creacion cancelada."
            self.logger.info(msg)
            self.mc.postToChat(msg)
            return

        try:
            # Crear instancia usando agent_factory
            new_agent = self.factory.create_agent(agent_type, self.mc, self.bus, agent_id=new_id)
        
            asyncio.create_task(new_agent.run())
            
            success_msg = f"Agente creado exitosamente: {new_id} ({agent_type})"
            self.active_agents.add((agent_type, new_id))
            self.logger.info(success_msg)
            self.mc.postToChat(success_msg)
            
        except ValueError as ve:
            err_msg = f"No se pudo crear agente {agent_type}: {ve}"
            self.logger.error(err_msg)
            self.mc.postToChat(err_msg)
        except Exception as e:
            err_msg = f"Error crítico creando agente: {e}"
            self.logger.error(err_msg)
            self.mc.postToChat("Error interno al crear agente.")
