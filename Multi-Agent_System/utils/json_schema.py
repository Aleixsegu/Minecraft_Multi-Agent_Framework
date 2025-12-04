# schema.py
import datetime


class SchemaError(Exception):
    """Raised when a message does not satisfy the required schema."""
    pass


def is_iso8601(timestamp: str) -> bool:
    """Checks that the timestamp follows ISO 8601 format."""
    try:
        datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_message(msg: dict):
    """
    Validates a message according to the TAP Minecraft Framework specification.

    Required fields:
    - type: str
    - source: str
    - target: str
    - timestamp: ISO8601 string
    - payload: dict
    - status: str
    - context: optional dict
    """

    if not isinstance(msg, dict):
        raise SchemaError("Message must be a dictionary.")

    required = ["type", "source", "target", "timestamp", "payload", "status"]

    for field in required:
        if field not in msg:
            raise SchemaError(f"Missing required field: {field}")

    # type
    if not isinstance(msg["type"], str):
        raise SchemaError("Field 'type' must be a string.")

    # source
    if not isinstance(msg["source"], str):
        raise SchemaError("Field 'source' must be a string.")

    # target
    if not isinstance(msg["target"], str):
        raise SchemaError("Field 'target' must be a string.")

    # timestamp
    if not isinstance(msg["timestamp"], str) or not is_iso8601(msg["timestamp"]):
        raise SchemaError("Field 'timestamp' must be a valid ISO8601 string.")

    # payload
    if not isinstance(msg["payload"], dict):
        raise SchemaError("Field 'payload' must be a dict.")

    # status
    valid_status = {"SUCCESS", "ERROR", "RUNNING", "PROCESSING", "WAITING"}

    if not isinstance(msg["status"], str):
        raise SchemaError("Field 'status' must be a string.")

    if msg["status"] not in valid_status:
        raise SchemaError(
            f"Invalid status '{msg['status']}'. Must be one of: {valid_status}"
        )

    # context (optional)
    if "context" in msg and not isinstance(msg["context"], dict):
        raise SchemaError("Field 'context' must be a dictionary if present.")

    # If everything passed, message is valid
    return True
