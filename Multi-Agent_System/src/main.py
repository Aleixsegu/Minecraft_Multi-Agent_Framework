import asyncio
import importlib
import importlib.util
import inspect
import sys
import os

from mcpi.minecraft import Minecraft
from utils.message_bus import MessageBus
from utils.command_parser import CommandParser
from agents.BaseAgent import BaseAgent
from agents.AgentFactory import AgentFactory

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
    Escanea el directorio 'agents/' para encontrar e importar clases que
    hereden de BaseAgent y las registra en AgentFactory con Reflexión.
    """
    for filename in os.listdir(agents_dir):
        # Filtra archivos Python válidos (ej: explorer.py, miner.py)
        if filename.endswith('.py') and filename not in ('__init__.py', 'base_agent.py', 'agent_factory.py', 'state_model.py'):
            module_name = filename[:-3] # Quita la extensión .py
            module_path = os.path.join(agents_dir, filename)

            # Usa importlib para cargar el módulo dinámicamente
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Inspecciona los miembros del módulo en busca de la clase de agente
            for name, obj in inspect.getmembers(module):
                # Comprueba si es una clase, hereda de BaseAgent, y no es la propia BaseAgent
                if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                    # 2. Registra la clase encontrada
                    # Usamos el nombre de la clase (ej: 'ExplorerBot') como clave
                    factory.register_agent_class(obj.__name__, obj)

# ---------------------------------------------------------------------
# LÓGICA PRINCIPAL
# ---------------------------------------------------------------------

async def main():

    # Crear el sistema
    mc = init_mc()

    message_bus = MessageBus()
    parser = CommandParser(message_bus)

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

    explorerBot.start()



# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programa detenido por el usuario")
        sys.exit(0)