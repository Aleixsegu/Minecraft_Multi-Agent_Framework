import asyncio
import sys
import os

# Añadir el directorio 'src' al path de Python para que encuentre los módulos internos (utils, agents, etc.)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from mcpi.minecraft import Minecraft
from messages.message_bus import MessageBus
from messages.message_parser import MessageParser
from agents.agent_factory import AgentFactory
from messages.chat_listener import ChatListener
from utils.reflection import get_all_agents
from agents.agent_manager import AgentManager
from utils.logging import clear_prev_logs
from utils.checkpoints import clear_prev_checkpoints

# ---------------------------------------------------------------------
# Lanza el mundo de Minecraft
# ---------------------------------------------------------------------
def init_mc():
    try:
        mc = Minecraft.create("10.69.114.162", 4711)
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
    
    if not os.path.exists(agents_dir):
        print(f"[ERROR] Directorio de agentes no encontrado: {agents_dir}")
        return

    agents = get_all_agents(agents_dir)
    
    for name, cls in agents.items():
        factory.register_agent_class(name, cls)

# ---------------------------------------------------------------------
# LÓGICA PRINCIPAL
# ---------------------------------------------------------------------

async def main():

    print("=== Iniciando TAP Minecraft Agent Framework ===")

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
    agents_path = os.path.join(src_dir, "agents")
    register_agents(factory, agents_path)

    # Iniciar el AgentManager para gestionar la creación de agentes
    manager = AgentManager(mc, message_bus)
    asyncio.create_task(manager.run())
    
    print("[INFO] Framework iniciado correctamente. Esperando comandos en el chat...")
    
    while True:
        await asyncio.sleep(1)

# ---------------------------------------------------------------------
# EJECUCIÓN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma detenido por el usuario")
        sys.exit(0)