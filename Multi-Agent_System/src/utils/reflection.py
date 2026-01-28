import os
import importlib.util
import inspect
from agents.base_agent import BaseAgent
from strategies.mining_strategy import MiningStrategy
from utils.logging import Logger
from utils.schematic_parser import SchematicParser


# Inicializar logger compartido
logger = Logger("Reflection")

def get_all_agents(agents_dir):
    """
    Escanea el directorio 'agents/' para encontrar e importar clases que
    hereden de BaseAgent.
    Devuelve un diccionario {nombre_clase: objeto_clase}.
    """
    found_agents = {}
    
    if not os.path.exists(agents_dir):
        logger.error(f"Directorio de agentes no encontrado: {agents_dir}")
        return found_agents

    for filename in os.listdir(agents_dir):
        # Filtra archivos Python válidos
        if filename.endswith('.py') and filename not in ('__init__.py', 'base_agent.py', 'agent_factory.py', 'state_model.py'):
            module_name = filename[:-3] # Quita la extensión .py
            module_path = os.path.join(agents_dir, filename)

            try:
                # Usa importlib para cargar el módulo dinámicamente
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Inspecciona los miembros del módulo en busca de la clase de agente
                for name, obj in inspect.getmembers(module):
                    # Comprueba si es una clase, hereda de BaseAgent, y no es la propia BaseAgent
                    if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                        found_agents[obj.__name__] = obj
            except Exception as e:
                logger.error(f"Error cargando agente desde {filename}: {e}")
    
    logger.info(f"Agentes cargados exitosamente: {len(found_agents)} desde {agents_dir}")
    return found_agents

def get_all_strategies(strategies_dir):
    """
    Escanea el directorio 'strategies/' para encontrar e importar clases que
    hereden de MiningStrategy.
    Devuelve un diccionario {nombre_clase: objeto_clase}.
    """
    found_strategies = {}
    
    if not os.path.exists(strategies_dir):
        logger.error(f"Directorio de estrategias no encontrado: {strategies_dir}")
        return found_strategies

    for filename in os.listdir(strategies_dir):
        # Filtra archivos Python válidos
        if filename.endswith('.py') and filename not in ('__init__.py', 'mining_strategy.py'):
            module_name = filename[:-3] # Quita la extensión .py
            module_path = os.path.join(strategies_dir, filename)

            try:
                # Usa importlib para cargar el módulo dinámicamente
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Inspecciona los miembros del módulo en busca de la clase de estrategia
                for name, obj in inspect.getmembers(module):
                    # Comprueba si es una clase, hereda de MiningStrategy, y no es la propia MiningStrategy
                    if inspect.isclass(obj) and issubclass(obj, MiningStrategy) and obj is not MiningStrategy:
                        found_strategies[obj.__name__] = obj
            except Exception as e:
                logger.error(f"Error cargando estrategia desde {filename}: {e}")
    
    logger.info(f"Estrategias cargadas exitosamente: {len(found_strategies)} desde {strategies_dir}")
    return found_strategies

def get_all_structures(structures_dir):
    """
    Escanea el directorio dado (ej: 'builder_structures/') para encontrar archivos .schem.
    Utiliza SchematicTranslator para cargarlos.
    Devuelve un diccionario {nombre_estructura: objeto_translator}.
    """
    found_structures = {}
    if not os.path.exists(structures_dir):
        logger.error(f"Directorio de estructuras no encontrado: {structures_dir}")
        return found_structures

    for filename in os.listdir(structures_dir):
        # Filtra archivos .schem
        if filename.endswith('.schem'):
            name = filename[:-6] # Quita la extensión .schem
            path = os.path.join(structures_dir, filename)
            
            try:
                parser = SchematicParser(path)
                found_structures[name] = parser
            except Exception as e:
                logger.error(f"Error cargando estructura {filename}: {e}")
    
    logger.info(f"Estructuras cargadas exitosamente: {len(found_structures)} desde {structures_dir}")
    return found_structures
