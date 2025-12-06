import asyncio
from typing import Dict, List, Any, Set
from utils.logging import Logger
from utils.json_schema import validate_message 
#from agents.BaseAgent import BaseAgent

class MessageBus:
    """
    Implementa el Patrón Observer (Publish-Subscribe) de forma asíncrona.
    Permite la comunicación punto-a-punto y basada en tipo de mensaje (broadcast selectivo).
    """

    def __init__(self):
        # agent_id → asyncio.Queue (Buzón de entrada del agente)
        self._queues: Dict[str, asyncio.Queue] = {} 
        # message_type → Set[str] de agent_ids suscritos (Núcleo del Observer)
        self._subscriptions: Dict[str, Set[str]] = {} 
        self.logger = Logger(self.__class__.__name__)
        
        self.logger.info("MessageBus inicializado.")

    # ------------------------------------------------------------
    # Observer Registration (Sujeto y Observadores)
    # ------------------------------------------------------------
    
    def register_agent(self, agent_id: str):
        """
        Registra un nuevo agente y crea su cola de entrada asíncrona.
        """
        if agent_id not in self._queues:
            self._queues[agent_id] = asyncio.Queue()
            self.logger.info(f"Agente '{agent_id}' registrado en el bus.")

    def subscribe(self, agent_id: str, message_type: str):
        """
        Patrón Observer: Registra el interés de un agente por un tipo de mensaje.
        Ej: BuilderBot se suscribe a 'map.v1'.
        """
        if agent_id not in self._queues:
            self.logger.error(f"Error al suscribir: Agente '{agent_id}' no registrado.")
            raise ValueError(f"Agent '{agent_id}' must be registered before subscribing.")

        if message_type not in self._subscriptions:
            self._subscriptions[message_type] = set()
            
        self._subscriptions[message_type].add(agent_id)
        self.logger.info(f"'{agent_id}' suscrito al tipo de mensaje: {message_type}.")


    # ------------------------------------------------------------
    # Publishing Messages
    # ------------------------------------------------------------
    
    async def publish(self, source_id: str, msg: Dict[str, Any]):
        """
        Método central de publicación que distribuye mensajes basados en 'type' 
        (Observer) o 'target' (Punto-a-Punto).
        """
        # Validación de msg
        try:
            validate_message(msg) 
        except Exception as e:
            self.logger.error(f"Mensaje inválido publicado por '{source_id}': {e}", context={"message_payload": msg})
            return

        message_type = msg.get('type', 'generic.v1')
        target_id = msg.get('target')
        
        # Log de envío del mensaje
        self.logger.log_agent_message(
            direction="SENT",
            message_type=message_type,
            source=source_id,
            target=target_id or 'BROADCAST',
            payload=msg
        )

        # Distribución (Patrón Observer)
        # Distribución (Patrón Observer vs Point-to-Point)
        recipients_found = 0
        
        # CASO 1: UNICAST (Target específico y NO Broadcast)
        if target_id and target_id != "BROADCAST":
             # Entrega exclusiva al target
             if target_id in self._queues:
                 await self._deliver(target_id, msg)
                 recipients_found += 1
             else:
                 self.logger.error(f"Target '{target_id}' no encontrado para mensaje unicast.")
        
        # CASO 2: BROADCAST (Target es None o "BROADCAST")
        else:
             # Entrega a todos los suscritos al TIPO
             if message_type in self._subscriptions:
                 for recipient_id in self._subscriptions[message_type]:
                     await self._deliver(recipient_id, msg)
                     recipients_found += 1
            
        if recipients_found == 0 and not target_id:
             self.logger.debug(f"Mensaje '{message_type}' publicado pero no tenía receptores suscritos ni un target definido.")


    async def _deliver(self, target_id: str, msg: Dict[str, Any]):
        """Función interna para colocar el mensaje en la cola de un agente."""
        if target_id in self._queues:
            await self._queues[target_id].put(msg)
            # El log de RECEPCIÓN se hará cuando el agente lo extraiga de la cola.
        else:
            self.logger.error(f"Intento de entrega fallido: Agente '{target_id}' no está registrado.")


    # ------------------------------------------------------------
    # Receiving Messages
    # ------------------------------------------------------------
    
    async def receive(self, agent_id: str):
        """
        Espera el próximo mensaje para este agente. La función se suspende 
        hasta que un mensaje llega a su cola (Buzón de entrada).
        """
        if agent_id not in self._queues:
            self.logger.error(f"Intento de recibir mensaje: Agente '{agent_id}' no está registrado.")
            raise ValueError(f"Agent '{agent_id}' is not registered.")

        # Espera asíncrona por un mensaje
        msg = await self._queues[agent_id].get() 

        # 4. Log de recepción del mensaje (traza de entrada)
        # Extraemos el origen del mensaje del payload para la trazabilidad
        source = msg.get('source', 'SYSTEM') 
        message_type = msg.get('type', 'unknown.v1')

        self.logger.log_agent_message(
            direction="RECEIVED", 
            message_type=message_type, 
            source=source, 
            target=agent_id, 
            payload=msg
        )

        return msg