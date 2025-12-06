import inspect
from agents.base_agent import BaseAgent

class AgentFactory:
    """
    Patrón Factory con Singleton para gestionar el registro y la creación dinámica de instancias de BaseAgent.
    """
    _instance = None
    _agent_registry = {} 

    def __new__(cls):
        """
        Implementación del Patrón Singleton para asegurar una única instancia del factory.
        """
        if cls._instance is None:
            cls._instance = super(AgentFactory, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_agent_class(cls, agent_name: str, agent_class):
        """
        Registra una clase de agente en el diccionario interno. 
        Usada por el mecanismo de Reflexión en main.py.
        """
        if not inspect.isclass(agent_class) or not issubclass(agent_class, BaseAgent):
             raise ValueError(f"{agent_class} no es una subclase válida de BaseAgent.")
        
        cls._agent_registry[agent_name] = agent_class

    def create_agent(self, agent_type: str, mc, message_bus, agent_id: str = None):
        """
        Crea una instancia de agente basada en el tipo solicitado.
        Si no se especifica agent_id, se usa el agent_type (cuidado con duplicados).
        """
        agent_class = self._agent_registry.get(agent_type)
        
        if agent_class is None:
            raise ValueError(f"Tipo de Agente no registrado: {agent_type}")
        
        # Usar el ID proporcionado o el tipo por defecto
        final_id = agent_id if agent_id else agent_type
        
        return agent_class(final_id, mc, message_bus)

    def list_available_agents(self):
        """Retorna una lista de agentes registrados (ej: para el comando /agent help)."""
        return list(self._agent_registry.keys())
