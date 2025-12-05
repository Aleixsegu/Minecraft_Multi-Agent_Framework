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
from utils.reflection import get_all_agents

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

# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programa detenido por el usuario")
        sys.exit(0)