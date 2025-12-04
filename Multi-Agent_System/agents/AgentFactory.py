import inspect
from agents.BaseAgent import BaseAgent

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

    def create_agent(self, agent_type: str, mc, message_bus):
        """
        Crea una instancia de agente basada en el tipo solicitado.
        """
        agent_class = self._agent_registry.get(agent_type)
        
        if agent_class is None:
            raise ValueError(f"Tipo de Agente no registrado: {agent_type}")
        
        return agent_class(agent_type, mc, message_bus)

    def list_available_agents(self):
        """Retorna una lista de agentes registrados (ej: para el comando /agent help)."""
        return list(self._agent_registry.keys())
