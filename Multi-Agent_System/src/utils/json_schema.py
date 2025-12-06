# schema.py
import datetime


class SchemaError(Exception):
    """Se lanza cuando un mensaje no tiene el formato requerido"""
    pass


def is_iso8601(timestamp: str) -> bool:
    """Comprueba si el timestamp sigue el formato ISO 8601."""
    try:
        datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_message(msg: dict):
    """
    Valida un mensaje según la especificación.
    
    Campos obligatorios:
    - type: str
    - source: str
    - target: str
    - timestamp: ISO8601 string
    - payload: dict
    - status: str
    - context: optional dict
    """

    if not isinstance(msg, dict):
        raise SchemaError("El mensaje debe ser un diccionario.")

    required = ["type", "source", "target", "timestamp", "payload", "status"]

    for field in required:
        if field not in msg:
            raise SchemaError(f"Falta el campo obligatorio: {field}")

    # type
    if not isinstance(msg["type"], str):
        raise SchemaError("El campo 'type' debe ser una cadena.")

    # source
    if not isinstance(msg["source"], str):
        raise SchemaError("El campo 'source' debe ser una cadena.")

    # target
    if not isinstance(msg["target"], str):
        raise SchemaError("El campo 'target' debe ser una cadena.")

    # timestamp
    if not isinstance(msg["timestamp"], str) or not is_iso8601(msg["timestamp"]):
        raise SchemaError("El campo 'timestamp' debe ser una cadena con formato ISO8601.")

    # payload
    if not isinstance(msg["payload"], dict):
        raise SchemaError("El campo 'payload' debe ser un diccionario.")

    # status
    valid_status = {"SUCCESS", "ERROR", "RUNNING", "PROCESSING", "WAITING", "INITIATED"}

    if not isinstance(msg["status"], str):
        raise SchemaError("El campo 'status' debe ser una cadena.")

    if msg["status"] not in valid_status:
        raise SchemaError(
            f"Valor de 'status' inválido: {msg['status']}. Esperado: {valid_status}")

    # context (opcional)
    if "context" in msg and not isinstance(msg["context"], dict):
        raise SchemaError("El campo 'context' debe ser un diccionario si está presente.")

    # Si todo pasa, el mensaje es válido
    return True
