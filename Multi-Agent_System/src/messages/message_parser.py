import re
import asyncio
import datetime
from messages.message_bus import MessageBus
from utils.logging import Logger
from typing import Dict, Any, Optional
import os
from utils.reflection import get_all_agents

# Regex para analizar comandos como ./<agente> <comando> <parametro>
COMMAND_PATTERN = re.compile(r"^\./([a-zA-Z]+) ([a-zA-Z]+)(?:\s+(.*))?$")
# Regex para analizar parámetros del tipo x=10 z=5 range=20
PARAM_PATTERN = re.compile(r"(\w+)=(\S+)")

class MessageParser:
    """
    Analiza comandos de chat de Minecraft y los convierte en mensajes de 
    control estandarizados (command.*.v1) para el MessageBus.
    """
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.logger = Logger(self.__class__.__name__)
        
        # Cargar dinámicamente los tipos de agentes válidos
        agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
        self.valid_agents = set(name.lower().replace('bot', '') for name in get_all_agents(agents_dir).keys())
        self.valid_agents.add("workflow")
        
        self.logger.info(f"MessageParser inicializado.")

    async def process_chat_message(self, command_str: str):
        """
        Método principal: Recibe la cadena de texto, la analiza y publica el mensaje.
        """
        command_str = command_str.strip()
        
        # Logueamos todo mensaje recibido para depuración
        self.logger.info(f"Analizando mensaje: {command_str}")
        
        # 1. Análisis del comando usando la Regex
        match = COMMAND_PATTERN.match(command_str)
        
        if match:
            agent_name, command, params_str = match.groups()
            
            # Validar que el agente sea uno de los permitidos (dinámicamente)
            if agent_name.lower() not in self.valid_agents:
                self.logger.info(f"Agente no reconocido: {agent_name}. Se ignorará el comando.")
                return

            # Análisis de parámetros
            payload = self._parse_chat_params(params_str)
            
            # Determinación del agente objetivo (ej: "ExplorerBot")
            target_agent = f"{agent_name.capitalize()}Bot" 
            
            self.logger.debug(f"Comando detectado: Agente={target_agent}, Accion={command}, Parametros={payload}")

            # 2. Creación del mensaje estandarizado
            control_message = self._create_control_message(target_agent=target_agent, command_type=command, payload=payload)
            
            # 3. Publicación en el log
            self.logger.log_agent_message(direction="SENT", message_type=control_message['type'], source="USER_CHAT", target=target_agent, payload=control_message['payload'])
            
            # Publicar el mensaje para que el agente objetivo lo reciba
            await self.message_bus.publish("USER_CHAT", control_message)
            
        else:
            self.logger.error(f"Mensaje ignorado (no coincide con formato comando): {command_str}")

    def _parse_chat_params(self, param_str: Optional[str]) -> Dict[str, Any]:
        """
        Convierte una cadena de parámetros 'key=value key2=value2' en un diccionario.
        Si hay un primer argumento posicional sin clave, lo asigna a 'name' (o 'id').
        """
        if not param_str:
            return {}
        
        params = {}
        
        # 1. Extraer key=value pairs
        for match in PARAM_PATTERN.finditer(param_str):
            key = match.group(1)
            value_str = match.group(2)
            try:
                params[key] = int(value_str)
            except ValueError:
                params[key] = value_str.strip()

        # 2. Buscar si hay una palabra "suelta" al principio que NO es key=value
        # Esto es para casos como: ./explorer create MyBot
        # Dividimos string y vemos el primer token
        tokens = param_str.split()
        if tokens:
            first = tokens[0]
            if "=" not in first:
                # Asumimos que es el ID o Nombre
                params["id"] = first
                params["name"] = first 

        return params

    def _create_control_message(self, target_agent: str, command_type: str, payload: Dict) -> Dict[str, Any]:
        """
        Ensambla el mensaje JSON estandarizado command.*.v1.
        """
        return {
            "type": f"command.{command_type.lower()}.v1",
            "source": "USER_CHAT",
            "target": target_agent,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            "payload": payload,
            "status": "INITIATED"
        }
