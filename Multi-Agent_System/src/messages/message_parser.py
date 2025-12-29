import re
import asyncio
import datetime
from messages.message_bus import MessageBus
from utils.logging import Logger
from typing import Dict, Any, Optional
import os
from utils.reflection import get_all_agents, get_all_structures

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
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
        agents_dir = os.path.join(self.root_dir, "agents")
        self.valid_agents = set(name.lower().replace('bot', '') for name in get_all_agents(agents_dir).keys())
        self.valid_agents.add("workflow")
        
        # Cargar estructuras para incluirlas en IGNORED_IDS (para que el parser no las confunda con IDs)
        structures_dir = os.path.join(self.root_dir, "builder_structures")  # Asumiendo path paralelo a src/agents
        # Como estamos en messages/ (dentro de src), root_dir es src. NO! root_dir es Multi-Agent_System/src
        # Re-calculando path correcto:
        # __file__ = .../Multi-Agent_System/src/messages/message_parser.py
        # root_dir = .../Multi-Agent_System/src
        # builder_structures = .../Multi-Agent_System/builder_structures
        
        base_root = os.path.dirname(self.root_dir) # .../Multi-Agent_System
        self.structures_dir = os.path.join(base_root, "builder_structures")

        self.structures = list(get_all_structures(self.structures_dir).keys())
        
        # Definir IDs que ignoraremos (verbos, keywords, y nombres de estructuras)
        self.ignored_ids = {'list', 'set', 'plan', 'bom', 'build'}
        self.ignored_ids.update(self.structures)

        self.logger.info(f"MessageParser inicializado. Estructuras cargadas: {self.structures}")

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
            
            # Lógica de Routing normal
            
            # Siempre añadimos el tipo de agente al payload para el filtrado en el receptor
            class_name = f"{agent_name.capitalize()}Bot"
            payload["agent_type"] = class_name
            
            # Caso 0: Workflow
            if agent_name.lower() == "workflow":
                target_agent = "AgentManager"
                msg_type = f"command.workflow.{command.lower()}"
                payload["command_str"] = params_str # Pass raw params for specialized parsing

            # Caso 1: CREACIÓN -> Target siempre es AgentManager
            elif command.lower() == "create":
                target_agent = "AgentManager"
                msg_type = f"command.{command.lower()}.v1"

            # Caso 2: UNICAST -> Si hay un ID explícito
            elif "id" in payload:
                target_agent = payload["id"]
                msg_type = f"command.{command.lower()}.v1"

            # Caso 3: BROADCAST GENÉRICO
            else:
                target_agent = "BROADCAST"
                msg_type = f"command.{command.lower()}.v1"

            self.logger.debug(f"Comando detectado: Target={target_agent}, Type={msg_type}, Payload={payload}")

            # 2. Creación del mensaje estandarizado
            control_message = self._create_control_message(target_agent=target_agent, msg_type=msg_type, payload=payload)
            
            # 3. Publicación
            # Publish directly to 'broadcast' topic if target is broadcast, or 'USER_CHAT' if complex routing?
            # If I stick to USER_CHAT, I rely on the bus.
            # But maybe the bus uses the 'target' field to route?
            # Let's trust 'broadcast' (lowercase) is better.
            
            self.logger.log_agent_message(direction="SENT", message_type=control_message['type'], source="USER_CHAT", target=target_agent, payload=control_message['payload'])
            
            await self.message_bus.publish("USER_CHAT", control_message)
            
        else:
            self.logger.error(f"Mensaje ignorado (no coincide con formato comando): {command_str}")

    def _parse_chat_params(self, param_str: Optional[str]) -> Dict[str, Any]:
        """
        Convierte una cadena de parámetros 'key=value key2=value2' en un diccionario.
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

        tokens = param_str.split()
        
        # Lógica especial para 'range' posicional 
        if "range" in tokens:
            idx = tokens.index("range")
            remaining = len(tokens) - (idx + 1)
            
            if remaining >= 2:
                # range <ID> <VALOR>
                val_id = tokens[idx+1]
                if "=" not in val_id:
                     params["id"] = val_id
                     params["name"] = val_id
                
                val_range = tokens[idx+2]
                try:
                    params["range"] = int(val_range)
                except ValueError:
                    params["range"] = val_range
                
                tokens.pop(idx+2)
                tokens.pop(idx+1)
                tokens.pop(idx)
                
            elif remaining == 1:
                # range <VALOR>
                val_range = tokens[idx+1]
                try:
                    params["range"] = int(val_range)
                except ValueError:
                    params["range"] = val_range
                    
                tokens.pop(idx+1)
                tokens.pop(idx)

        # Lógica especial para 'strategy' posicional
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
        extra_args = []
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if "=" in token: # Ya procesado por regex
                i += 1
                continue
            
            # Si es un ID suelto que ha sobrevivido
            if "id" not in params:
                 # Solo lo tratamos como ID si NO está en la lista de ignorados
                 if token not in self.ignored_ids:
                     params["id"] = token
                     params["name"] = token
            
            extra_args.append(token)
            
            i += 1
            
        params["args"] = extra_args
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
