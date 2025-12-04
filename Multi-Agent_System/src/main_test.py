import time
from mcpi.minecraft import Minecraft
import mcpi.block as block

#MAIN DE TEST PARA PROBAR LA CONECTIVIDAD CON EL SERVIDOR DE MINECRAFT

# --- Configuración ---
# La conexión debe ser a 'localhost' si el servidor se ejecuta en la misma máquina.
SERVER_HOST = "localhost"
# El puerto 4711 es el que utiliza por defecto RaspberryJuice para la API[cite: 317].
SERVER_PORT = 4711

def run_connectivity_test():
    """
    Establece la conexión con el servidor de Minecraft y realiza una
    operación simple (chat y colocación de bloque) para verificar la API mcpi.
    """
    print(f"🌍 Intentando conectar con el servidor Minecraft en {SERVER_HOST}:{SERVER_PORT}...")

    try:
        # 1. Conexión al juego
        # Minecraft.create() establece la conexión con la dirección y puerto por defecto (localhost:4711)
        mc = Minecraft.create(address=SERVER_HOST, port=SERVER_PORT)
        print("✅ Conexión establecida con éxito.")

        # 2. Interacción básica (Chat)
        chat_message = "Hello Minecraft World! (Test OK)"
        mc.postToChat(chat_message)
        print(f"💬 Mensaje enviado al chat del juego: '{chat_message}'")

        # 3. Colocación de un Bloque
        # Obtener la posición actual del jugador
        pos = mc.player.getTilePos()
        
        # Coordenadas de prueba: 3 bloques en la dirección X positiva,
        # a la misma altura (Y) y profundidad (Z) del jugador.
        x = pos.x + 3
        y = pos.y
        z = pos.z
        
        # Colocar un bloque de PIEDRA (STONE.id = 1) [cite: 347, 332]
        block_type = block.STONE.id
        mc.setBlock(x, y, z, block_type)
        
        print(f"🧱 Bloque de Piedra colocado en: ({x}, {y}, {z})")
        print("\nPrueba de conectividad API completada con éxito.")
        print("📢 Ve a tu posición en Minecraft para verificar el bloque colocado.")

    except ConnectionRefusedError:
        print("❌ Error de Conexión: La conexión fue rechazada.")
        print("Asegúrate de que el servidor de Minecraft (usando CraftBukkit/RaspberryJuice) esté corriendo en el host especificado.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    # Asegúrate de que el servidor esté listo
    print("🚀 Iniciando prueba de conectividad...")
    print("Asegúrate de que el servidor esté iniciado (StartServer.{bat|sh|command}) y de que estés conectado al mundo.")
    time.sleep(2) # Pequeña pausa
    run_connectivity_test()