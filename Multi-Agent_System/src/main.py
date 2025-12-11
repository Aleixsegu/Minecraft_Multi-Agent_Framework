from asyncio.tasks import gather
import asyncio
import importlib
import sys
import os

from mcpi.minecraft import Minecraft
from messages.message_bus import MessageBus
from messages.message_parser import MessageParser
from agents.base_agent import BaseAgent
from agents.agent_factory import AgentFactory
from messages.chat_listener import ChatListener
from utils.reflection import get_all_agents, get_all_strategies, get_all_structures
from agents.agent_manager import AgentManager
from utils.logging import clear_prev_logs
from utils.checkpoints import clear_prev_checkpoints

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
# MENSAJES CHAT DE PRUEBA
# ---------------------------------------------------------------------
async def chat_messages(mc, parser):
    
    tiempo = 0.5
    
    async def global_sequence():
        mc.postToChat("===============================")
        mc.postToChat("---TEST DE MENSAJES GLOBALES---")
        mc.postToChat("===============================")

        mc.postToChat("[TEST] > ./explorer create paco")
        await parser.process_chat_message("./explorer create paco")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer create juan")
        await parser.process_chat_message("./explorer create juan")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner create eustaquio")
        await parser.process_chat_message("./miner create eustaquio")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner create hermenigildo")
        await parser.process_chat_message("./miner create hermenigildo")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer status")
        await parser.process_chat_message("./explorer status")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner status hermenigildo")
        await parser.process_chat_message("./miner status hermenigildo")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner pause eustaquio")
        await parser.process_chat_message("./miner pause eustaquio")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer stop")
        await parser.process_chat_message("./explorer stop")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer status")
        await parser.process_chat_message("./explorer status")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner status")
        await parser.process_chat_message("./miner status")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer help")
        await parser.process_chat_message("./explorer help")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner help eustaquio")
        await parser.process_chat_message("./miner help eustaquio")
        await asyncio.sleep(tiempo)

    async def explorer_sequence():

        mc.postToChat("=============================")
        mc.postToChat("-----TEST DE EXPLORERBOT-----")
        mc.postToChat("=============================")

        mc.postToChat("[TEST] > ./explorer create 1")
        await parser.process_chat_message("./explorer create 1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer create 2")
        await parser.process_chat_message("./explorer create 2")
        await asyncio.sleep(tiempo)
        
        mc.postToChat("[TEST] > ./explorer set range 500")
        await parser.process_chat_message("./explorer set range 500")
        await asyncio.sleep(tiempo)
        
        mc.postToChat("[TEST] > ./explorer set range 1 10")
        await parser.process_chat_message("./explorer set range 1 10")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer start 1 x=0 z=0 range=10")
        await parser.process_chat_message("./explorer start 1 x=0 z=0 range=10")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./explorer start 2 (ejecutar el usuario)")
        await asyncio.sleep(tiempo)


    async def miner_sequence():

        mc.postToChat("============================")
        mc.postToChat("------TEST DE MINERBOT------")
        mc.postToChat("============================")

        mc.postToChat("[TEST] > ./miner create 1")
        await parser.process_chat_message("./miner create 1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner create 2")
        await parser.process_chat_message("./miner create 2")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner set strategy grid")
        await parser.process_chat_message("./miner set strategy grid")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner set strategy 1 vein")
        await parser.process_chat_message("./miner set strategy 1 vein")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner start 1 x=10 z=-20 y=50")
        await parser.process_chat_message("./miner start 1 x=10 z=-20 y=50")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner start 2 (ejecutar el usuario)")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./miner fulfill 1")
        await parser.process_chat_message("./miner fulfill 1")
        await asyncio.sleep(tiempo)

    async def builder_sequence():

        mc.postToChat("============================")
        mc.postToChat("-----TEST DE BUILDERBOT-----")
        mc.postToChat("============================")

        mc.postToChat("[TEST] > ./builder create 1")
        await parser.process_chat_message("./builder create 1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder create 2")
        await parser.process_chat_message("./builder create 2")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder plan list")
        await parser.process_chat_message("./builder plan list")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder plan set 1 villagehouse1")
        await parser.process_chat_message("./builder plan set 1 villagehouse1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder plan set villagehouse1")
        await parser.process_chat_message("./builder plan set villagehouse1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder bom 1")
        await parser.process_chat_message("./builder bom 1")
        await asyncio.sleep(tiempo)

        mc.postToChat("[TEST] > ./builder build 1")
        await parser.process_chat_message("./builder build 1")
        await asyncio.sleep(tiempo)

    print("[TEST] --- Iniciando secuencia de prueba ---")
    await asyncio.sleep(tiempo) 

    #await global_sequence()
    await explorer_sequence()
    #await miner_sequence()
    #await builder_sequence()

    print("[TEST] --- Fin secuencia de prueba ---")

# ---------------------------------------------------------------------
# LÓGICA PRINCIPAL
# ---------------------------------------------------------------------

async def main():

    # Limpiar logs y checkpoints anteriores
    clear_prev_logs()
    clear_prev_checkpoints()
    
    # Crear el sistema
    mc = init_mc()

    message_bus = MessageBus()
    parser = MessageParser(message_bus)
    listener = ChatListener(parser, mc)

    asyncio.create_task(listener.listen_for_commands())

    # Obtener la instancia Singleton del Factory
    factory = AgentFactory()

    register_agents(factory, os.path.join(os.path.dirname(os.path.abspath(__file__)), "agents"))

    # Iniciar el AgentManager para gestionar la creación de agentes
    manager = AgentManager(mc, message_bus)
    asyncio.create_task(manager.run())
    
    asyncio.create_task(chat_messages(mc, parser))

    while True:
        await asyncio.sleep(1)

# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Programa detenido por el usuario")
        sys.exit(0)