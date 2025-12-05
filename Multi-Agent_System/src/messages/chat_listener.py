import asyncio
import time
from mcpi.minecraft import Minecraft
from messages.message_parser import MessageParser
from utils.logging import Logger

class ChatListener:
    """
    Clase dedicada a la conexión con Minecraft y a la escucha asíncrona continua 
    de mensajes de chat (polling). Pasa los mensajes sin procesar al CommandParser.
    """

    def __init__(self, message_parser: MessageParser, mc):
        """
        Inicializa el Listener. Recibe el MessageParser como dependencia.
        """
        
        self.parser = message_parser
        self.logger = Logger(self.__class__.__name__)
        self.is_running = True
        self.mc = mc

    async def listen_for_commands(self):
        """
        Bucle asíncrono que sondea (poll) el chat de Minecraft de forma no bloqueante.
        Este es el bucle de "espera" continua.
        """

        self.logger.info("ChatListener iniciado.")
        
        while self.is_running:
            try:
                # Leer posts de chat desde mcpi
                chat_posts = self.mc.events.pollChatPosts()               
                for post in chat_posts:
                    chat_message = post.message.strip()
                    self.logger.debug(f"Mensaje sin procesar detectado: {chat_message}")

                    # El Listener solo PIDE al Parser que procese la cadena
                    await self.parser.process_chat_message(chat_message)
                
                # Pausa asíncrona para liberar el bucle principal (0.1s)
                await asyncio.sleep(0.1) 
                
            except Exception as e:
                self.logger.error(f"Error grave en el bucle de escucha de chat: {e}")
                await asyncio.sleep(5) 

    def stop(self):
        """Detiene la escucha."""

        self.is_running = False
        self.logger.info("Escucha de chat detenida.")