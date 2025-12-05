import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from messages.chat_listener import ChatListener

# Estructura simple para simular los objetos ChatPost de mcpi
class MockChatPost:
    def __init__(self, message):
        self.message = message

@pytest.fixture
def mock_mc():
    mc = MagicMock()
    # pollChatPosts debe devolver una lista vacía por defecto para no loopar infinito error
    mc.events.pollChatPosts.return_value = []
    return mc

@pytest.fixture
def mock_parser():
    parser = MagicMock()
    # process_chat_message es async
    parser.process_chat_message = AsyncMock()
    return parser

@pytest.fixture
def listener(mock_parser, mock_mc):
    # Parcheamos el Logger igual que antes para evitar issues
    with patch("messages.chat_listener.Logger") as MockLogger:
        MockLogger.return_value.info = MagicMock()
        MockLogger.return_value.debug = MagicMock()
        MockLogger.return_value.error = MagicMock()
        
        l = ChatListener(mock_parser, mock_mc)
        yield l

@pytest.mark.asyncio
async def test_initialization(listener, mock_parser, mock_mc):
    assert listener.parser == mock_parser
    assert listener.mc == mock_mc
    assert listener.is_running is True

@pytest.mark.asyncio
async def test_stop(listener):
    listener.stop()
    assert listener.is_running is False

@pytest.mark.asyncio
async def test_listen_processing_messages(listener, mock_mc, mock_parser):
    """
    Verifica que si mcpi devuelve mensajes, estos se envían al parser.
    """
    # Configuramos el mock para devolver mensajes la primera vez, y luego nada
    # Usamos side_effect iterando sobre las llamadas
    post1 = MockChatPost("Hello world")
    post2 = MockChatPost("/miner start")
    
    mock_mc.events.pollChatPosts.side_effect = [[post1, post2], [], [], []]
    
    # Lanzamos el listener
    task = asyncio.create_task(listener.listen_for_commands())
    
    # Dejamos que corra un par de ciclos
    await asyncio.sleep(0.1)
    
    # Detenemos
    listener.stop()
    await task
    
    # Verificaciones
    assert mock_parser.process_chat_message.call_count == 2
    
    # Verificamos las llamadas exactas
    calls = mock_parser.process_chat_message.call_args_list
    assert calls[0][0][0] == "Hello world"
    assert calls[1][0][0] == "/miner start"




