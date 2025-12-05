import pytest
import datetime
from utils.json_schema import validate_message, SchemaError

def get_valid_message():
    """Helper para crear un mensaje válido base."""
    return {
        "type": "test.v1",
        "source": "AgentA",
        "target": "AgentB",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": {"key": "value"},
        "status": "SUCCESS"
    }

def test_validate_valid_message():
    msg = get_valid_message()
    assert validate_message(msg) is True

def test_validate_missing_fields():
    msg = get_valid_message()
    del msg["type"]
    with pytest.raises(SchemaError, match="Falta el campo obligatorio: type"):
        validate_message(msg)

def test_validate_invalid_types():
    msg = get_valid_message()
    msg["payload"] = "not a dict" 
    with pytest.raises(SchemaError, match="El campo 'payload' debe ser un diccionario"):
        validate_message(msg)

def test_validate_invalid_timestamp():
    msg = get_valid_message()
    msg["timestamp"] = "invalid-date"
    with pytest.raises(SchemaError, match="El campo 'timestamp' debe ser una cadena con formato ISO8601"):
        validate_message(msg)

def test_validate_invalid_status():
    msg = get_valid_message()
    msg["status"] = "UNKNOWN_STATUS"
    # El mensaje de error en json_schema.py parece genérico en la línea 69-70 según vi antes,
    # pero verificamos que lance SchemaError.
    with pytest.raises(SchemaError):
        validate_message(msg)
