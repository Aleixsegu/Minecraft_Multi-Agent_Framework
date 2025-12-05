import pytest
from unittest.mock import AsyncMock, MagicMock
import asyncio
import datetime
import json
import sys

# Ajustamos las importaciones
from messages.message_parser import MessageParser
from messages.message_bus import MessageBus

# --- MOCKING DE DEPENDENCIAS ---

# 1. Mock para el MessageBus
@pytest.fixture
def mock_message_bus():
    """Fixture que provee un MessageBus mockeado."""
    bus = MagicMock(spec=MessageBus)
    bus.publish = AsyncMock()
    return bus

# 2. Mockeamos la validación de JSON Schema
@pytest.fixture(autouse=True)
def mock_validation(monkeypatch):
    """Asegura que la validación JSON no falle durante los tests."""
    def mock_validate(*args, **kwargs):
        return True
    
    # MessageBus importa validate_message de utils.json_schema
    monkeypatch.setattr("utils.json_schema.validate_message", mock_validate)

# 3. Mockeamos la reflexión de agentes (CRUCIAL para MessageParser)
@pytest.fixture(autouse=True)
def mock_agents_reflection(monkeypatch):
    """
    Simula que existen ciertos agentes (MinerBot, BuilderBot) para que
    MessageParser los considere válidos sin leer el disco real.
    """
    def mock_get_agents(*args, **kwargs):
        # Devolvemos un diccionario falso simulando las clases de los agentes
        return {
            "MinerBot": MagicMock(),
            "BuilderBot": MagicMock(),
            "ExplorerBot": MagicMock()
        }
    
    # MessageParser importa get_all_agents de utils.reflection
    monkeypatch.setattr("utils.reflection.get_all_agents", mock_get_agents)


# --- TESTS DE LA CLASE MessageParser ---

@pytest.mark.asyncio
async def test_parse_valid_command_with_params(mock_message_bus):
    """
    Verifica que un comando válido con parámetros se analice correctamente 
    y se publique en el MessageBus.
    """
    parser = MessageParser(mock_message_bus)
    
    # Comando de ejemplo: /miner start x=100 y=-5 z=200
    # Nota: MessageParser espera "./miner" o verifica si maneja "/" inicial según tu regex
    # Tu regex es: r"^\.?/([a-zA-Z]+) ([a-zA-Z]+)(?:\s+(.*))?$" o similar.
    # Mirando el código original: r"^\./([a-zA-Z]+) ([a-zA-Z]+)(?:\s+(.*))?$"
    # Requiere "./" al inicio.
    command_str = "./miner start x=100 y=-5 z=200"
    
    await parser.process_chat_message(command_str)
    
    # 1. Verificar que el método 'publish' del MessageBus fue llamado
    mock_message_bus.publish.assert_called_once()
    
    # 2. Extraer los argumentos con los que fue llamado publish
    # Argumento 0: source_id ("USER_CHAT")
    # Argumento 1: el mensaje JSON completo (control_message)
    call_args = mock_message_bus.publish.call_args
    _, control_message = call_args[0]
    
    # 3. Realizar aserciones sobre el mensaje JSON creado
    assert control_message['type'] == "command.start.v1"
    assert control_message['target'] == "MinerBot"
    assert control_message['source'] == "USER_CHAT"
    assert control_message['payload'] == {"x": 100, "y": -5, "z": 200}
    
    # Verificar que los tipos de datos se parsearon correctamente
    assert isinstance(control_message['payload']['x'], int)


@pytest.mark.asyncio
async def test_parse_command_with_string_and_int_params(mock_message_bus):
    """
    Verifica que los parámetros string y int se manejen correctamente.
    Ejemplo: ./miner set strategy=grid limit=50
    """
    parser = MessageParser(mock_message_bus)
    command_str = "./miner set strategy=grid limit=50"
    
    await parser.process_chat_message(command_str)
    
    _, control_message = mock_message_bus.publish.call_args[0]
    
    assert control_message['type'] == "command.set.v1"
    assert control_message['target'] == "MinerBot"
    assert control_message['payload'] == {"strategy": "grid", "limit": 50}
    assert isinstance(control_message['payload']['limit'], int)
    assert isinstance(control_message['payload']['strategy'], str)


@pytest.mark.asyncio
async def test_parse_invalid_command_formatting(mock_message_bus):
    """
    Verifica que los mensajes que no coinciden con el patrón sean ignorados.
    """
    parser = MessageParser(mock_message_bus)
    
    # Caso 1: Estructura incorrecta (falta ./ o espacio)
    await parser.process_chat_message("miner start_now") 
    
    # Caso 2: Solo chat
    await parser.process_chat_message("Hola mundo")

    mock_message_bus.publish.assert_not_called()

@pytest.mark.asyncio
async def test_parse_unknown_agent(mock_message_bus):
    """
    Verifica que si el agente no existe, se ignora el comando.
    """
    parser = MessageParser(mock_message_bus)
    
    # 'CheaterBot' no está en nuestro mock de agentes
    await parser.process_chat_message("./cheater godmode on=true")
    
    mock_message_bus.publish.assert_not_called()