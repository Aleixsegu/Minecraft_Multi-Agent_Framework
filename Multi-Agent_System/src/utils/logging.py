import logging
import json
import datetime
import sys
import os
from typing import Any, Dict, Optional
from agents.state_model import State

from pathlib import Path
LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

def clear_prev_logs():
    """
    Elimina todos los archivos de log en el directorio de logs.
    """

    if os.path.exists(LOGS_DIR):
        for filename in os.listdir(LOGS_DIR):
            file_path = os.path.join(LOGS_DIR, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

class Json_log_formatter(logging.Formatter):
    """
    Formateador personalizado para transformar los registros de log en JSON.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Transforma el LogRecord en una cadena JSON.
        """

        # Creación del diccionario base
        log_data: Dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": record.levelname,
            "object": getattr(record, 'object', 'SYSTEM'),
            "module": record.name,
            "message": record.getMessage(),
        }

        # Añadir campos extra si existen (como 'event', 'prev_state', 'next_state', etc.)
        if hasattr(record, 'extra_context') and isinstance(record.extra_context, dict):
            log_data.update(record.extra_context)

        # Si hay excepciones, añadirlas
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Retornar la cadena JSON
        return json.dumps(log_data)

class Logger:
    """
    Clase de interfaz simple para que los agentes realicen logs estructurados.
    """

    def __init__(self, object: str, log_file_name: str = None, level=logging.DEBUG):
        """
        Inicializa el logger para un agente específico.
        :param object: Identificador único del objeto
        :param log_file_name: Nombre del archivo de log. Si es None, usa object.
        """

        self.object = object
        
        # Usamos el nombre del archivo como nombre del logger para agrupar handlers
        logger_name = log_file_name if log_file_name else object
        
        self.logger = logging.getLogger(f"group.{logger_name}")
        self.logger.setLevel(level)

        # Configuración única del handler y formatter (solo si no existe)
        if not self.logger.handlers:

            os.makedirs(LOGS_DIR, exist_ok=True)

            # Configurar el Handler de Archivo
            file_handler = logging.FileHandler(f"{LOGS_DIR}/{logger_name}.jsonl", mode='w', encoding='utf-8')
            file_handler.setFormatter(Json_log_formatter())
            self.logger.addHandler(file_handler)
            
            # Evitar que los logs se propaguen al logger root
            self.logger.propagate = False

    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Registra un mensaje de nivel INFO."""

        extra = {'object': self.object, 'extra_context': context or {}}
        self.logger.info(message, extra=extra)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Registra un mensaje de nivel DEBUG."""

        extra = {'object': self.object, 'extra_context': context or {}}
        self.logger.debug(message, extra=extra)

    def error(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Registra un mensaje de nivel ERROR."""

        extra = {'object': self.object, 'extra_context': context or {}}
        self.logger.error(message, extra=extra)

    #logs específicos para los agentes

    def log_agent_transition(self, prev_state: State, next_state: State, reason: str = "Transition"):
        """
        Función clave para loguear transiciones de estado
        """

        context = {
            "event_type": "STATE_TRANSITION",
            "prev_state": prev_state.name,
            "next_state": next_state.name,
            "reason": reason
        }
        self.info(f"State changed from {prev_state.name} to {next_state.name}", context=context)

    def log_agent_message(self, direction: str, message_type: str, source: str, target: str, payload: Dict):
        """
        Función para loguear mensajes enviados o recibidos 
        """

        context = {
            "event_type": "MESSAGE_TRACE",
            "direction": direction, # 'SENT' o 'RECEIVED'
            "message_type": message_type,
            "source": source,
            "target": target,
            "payload_summary": payload
        }
        self.info(f"Message {direction}: {message_type} from {source} to {target}", context=context)