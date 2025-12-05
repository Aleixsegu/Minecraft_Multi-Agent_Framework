from asyncio.tasks import gather
import asyncio
import importlib
import importlib.util
import inspect
import sys
import os

from mcpi.minecraft import Minecraft
from messages.message_bus import MessageBus
from messages.message_parser import MessageParser
from agents.BaseAgent import BaseAgent
from agents.AgentFactory import AgentFactory
from messages.chat_listener import ChatListener
from utils.reflection_get_agents import get_all_agents

# ---------------------------------------------------------------------
# Lanza el mundo de Minecraft
# ---------------------------------------------------------------------
def init_mc():
    try:
        mc = Minecraft.create("localhost", 4711)
        print("[INFO] Conectado a Minecraft.")
        return mc
    except Exception as e:
        print("[ERROR] No se ha podido conectar a Minecraft:", e)
        sys.exit(1)


# ---------------------------------------------------------------------
# REGISTRO DE AGENTES
# ---------------------------------------------------------------------
def register_agents(factory, agents_dir):
    """
    Usa la utilidad de descubrimiento para encontrar clases de agentes y registrarlas.
    """
    
    agents = get_all_agents(agents_dir)
    for name, cls in agents.items():
        factory.register_agent_class(name, cls)

# ---------------------------------------------------------------------
# LÓGICA PRINCIPAL
# ---------------------------------------------------------------------

async def main():

    # Crear el sistema
    mc = init_mc()

    message_bus = MessageBus()
    parser = MessageParser(message_bus)
    listener = ChatListener(parser, mc)

    asyncio.create_task(listener.listen_for_commands())

    # Obtener la instancia Singleton del Factory
    factory = AgentFactory()

    register_agents(factory, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))
    print(factory.list_available_agents())

    # Creación de agentes con factory
    explorerBot = factory.create_agent("ExplorerBot", mc, message_bus, agent_id="ExplorerBot1")
    explorerBot2 = factory.create_agent("ExplorerBot", mc, message_bus, agent_id="ExplorerBot2")
    minerBot = factory.create_agent("MinerBot", mc, message_bus, agent_id="MinerBot1")
    builderBot = factory.create_agent("BuilderBot", mc, message_bus, agent_id="BuilderBot1")

    # Registrar en el bus
    message_bus.register_agent(explorerBot.id)
    message_bus.register_agent(explorerBot2.id)
    message_bus.register_agent(minerBot.id)
    message_bus.register_agent(builderBot.id)

    # Iniciar agentes
    
    await asyncio.gather(
        explorerBot.run(),
        explorerBot2.run(),
        minerBot.run(),
        builderBot.run()
    )

    listener.stop()


# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programa detenido por el usuario")
        sys.exit(0)