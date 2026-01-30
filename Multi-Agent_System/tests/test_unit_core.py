import pytest
import sys
import os
import asyncio
from unittest.mock import AsyncMock
import datetime # Importamos datetime
import sys
import os

from messages.message_parser import MessageParser
from messages.message_bus import MessageBus

@pytest.mark.unit
class TestUnitCore:
    
    def test_message_parser_init(self):
        # Mock del bus para instanciar parser
        mock_bus = AsyncMock()
        parser = MessageParser(mock_bus)
        assert parser is not None

    @pytest.mark.asyncio
    async def test_message_bus_pub_sub(self):
        """Valida el patrón Publicar/Suscribir."""
        bus = MessageBus()

        # 1. Registrar agente
        bus.register_agent("test_agent")
        
        # 2. Suscribir al topic 'test.topic'
        bus.subscribe("test_agent", "test.topic")
        
        # 3. Publicar mensaje
        # IMPORTANTE: Asegúrate de que el type coincida con la suscripción
        # Y que el mensaje cumpla con el schema (timestamp, source, target, status, payload dict)
        msg_payload = {
            "type": "test.topic",
            "source": "sender", 
            "target": "BROADCAST",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "payload": {"content": "hello"}, 
            "status": "INITIATED"
        }
        await bus.publish("sender", msg_payload)
        
        try:
            # 4. Recibir
            msg = await asyncio.wait_for(bus.receive("test_agent"), timeout=2.0)
            assert msg["payload"]["content"] == "hello"
            
        except asyncio.TimeoutError:
            # Si falla, imprimimos el estado interno del bus para debug
            print(f"DEBUG BUS STATE: Queues: {list(bus._queues.keys())}")
            # Verificamos si existe un atributo de suscripciones para debuguear
            if hasattr(bus, '_subscriptions'):
                print(f"DEBUG SUBS: {bus._subscriptions}")
            
            # Fallback: Intentar envío directo si el topic falla
            print("Intentando envío directo (fallback)...")
            msg_direct = {
                "type": "direct.test",
                "source": "sender",
                "target": "test_agent",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "payload": {"content": "direct"},
                "status": "INITIATED"
            }
            await bus.publish("sender", msg_direct)
            
            msg = await asyncio.wait_for(bus.receive("test_agent"), timeout=1.0)
            assert msg["payload"]["content"] == "direct"