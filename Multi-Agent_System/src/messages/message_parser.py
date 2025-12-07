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
            
            # Lógica de Routing actualizada
            
            # Siempre añadimos el tipo de agente al payload para el filtrado en el receptor
            class_name = f"{agent_name.capitalize()}Bot"
            payload["agent_type"] = class_name
            
            # Caso 1: CREACIÓN -> Target siempre es AgentManager
            if command.lower() == "create":
                target_agent = "AgentManager"
                msg_type = f"command.{command.lower()}.v1"

            # Caso 2: UNICAST -> Si hay un ID explícito en los parámetros (ej: ./explorer pause 1)
            elif "id" in payload:
                target_agent = payload["id"]
                msg_type = f"command.{command.lower()}.v1"

            # Caso 3: BROADCAST GENÉRICO -> Si NO hay ID (ej: ./explorer pause)
            # Ya no usamos command.ExplorerBot.pause.v1, sino command.pause.v1
            # El agente filtrará usando payload['agent_type']
            else:
                target_agent = "BROADCAST"
                msg_type = f"command.{command.lower()}.v1"

            self.logger.debug(f"Comando detectado: Target={target_agent}, Type={msg_type}, Payload={payload}")

            # 2. Creación del mensaje estandarizado
            control_message = self._create_control_message(target_agent=target_agent, msg_type=msg_type, payload=payload)
            
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

        # 2. Buscar palabras sueltas para casos especiales
        # a) Casos como "./explorer create MyBot" -> ID=MyBot
        # b) Casos como "./explorer set range 50" (el usuario no puso =)
        # c) Casos como "./explorer set range 1 50" (ID=1, range=50 o viceversa)
        
        tokens = param_str.split()
        
        tokens = param_str.split()
        
        # Lógica especial para 'range' posicional para resolver ambigüedad
        # ./explorer set range 1 10  (ID=1, Range=10) vs ./explorer set range 10 (Range=10)
        if "range" in tokens:
            idx = tokens.index("range")
            # Cuantos tokens quedan después de 'range'
            remaining = len(tokens) - (idx + 1)
            
            if remaining >= 2:
                # Asumimos formato: range <ID> <VALOR>
                # El token en idx+1 es el ID
                val_id = tokens[idx+1]
                if "=" not in val_id:
                     params["id"] = val_id
                     params["name"] = val_id
                
                # El token en idx+2 es el VALOR
                val_range = tokens[idx+2]
                try:
                    params["range"] = int(val_range)
                except ValueError:
                    params["range"] = val_range
                
                # Consumimos 'range', id y valor para que no molesten en el bucle general
                tokens.pop(idx+2)
                tokens.pop(idx+1)
                tokens.pop(idx)
                
            elif remaining == 1:
                # Asumimos formato: range <VALOR>
                val_range = tokens[idx+1]
                try:
                    params["range"] = int(val_range)
                except ValueError:
                    params["range"] = val_range
                    
                tokens.pop(idx+1)
                tokens.pop(idx)

        # Lógica especial para 'strategy' posicional
        # ./miner set strategy vertical
        # ./miner set strategy 1 vertical
        if "strategy" in tokens:
            idx = tokens.index("strategy")
            remaining = len(tokens) - (idx + 1)
            
            if remaining >= 2:
                # strategy <ID> <VALOR>
                val_id = tokens[idx+1]
                if "=" not in val_id and "id" not in params:
                     params["id"] = val_id
                     params["name"] = val_id
                
                val_strat = tokens[idx+2]
                params["strategy"] = val_strat
                
                tokens.pop(idx+2)
                tokens.pop(idx+1)
                tokens.pop(idx)
            
            elif remaining == 1:
                # strategy <VALOR>
                val_strat = tokens[idx+1]
                params["strategy"] = val_strat
                tokens.pop(idx+1)
                tokens.pop(idx)

        # Bucle genérico para lo que quede
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if "=" in token: # Ya procesado por regex
                i += 1
                continue
            
            # Si es un ID suelto que ha sobrevivido (ej: ./explorer set 1 range=50)
            if "id" not in params:
                 params["id"] = token
                 params["name"] = token
            
            i += 1
            
        return params

    def _create_control_message(self, target_agent: str, msg_type: str, payload: Dict) -> Dict[str, Any]:
        """
        Ensambla el mensaje JSON estandarizado.
        """
        return {
            "type": msg_type,
            "source": "USER_CHAT",
            "target": target_agent,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            "payload": payload,
            "status": "INITIATED"
        }
