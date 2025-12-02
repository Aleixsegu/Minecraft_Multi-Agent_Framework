# TAP-Minecraft-Agent-Framework

[🇬🇧 English](README.en.md)

Este proyecto integra un entorno de servidor Minecraft con un sistema multi-agente programable en Python, orientado a la experimentación y desarrollo de agentes inteligentes dentro del mundo de Minecraft.

## Estructura del Proyecto

- **AdventuresInMinecraft-PC-master/**: Contiene el servidor de Minecraft preconfigurado (versión 1.12) y los recursos necesarios para la conexión con agentes externos.
  - `Server/`: Archivos del servidor, configuración y plugins (incluyendo RaspberryJuice para la API de Python).
  - `StartServer.bat`: Script para iniciar el servidor de Minecraft fácilmente en Windows.
- **Multi-Agent_System/**: Plataforma en Python para el desarrollo y ejecución de agentes que interactúan con el mundo de Minecraft.
  - `main.py`: Punto de entrada para el sistema multi-agente.
  - `agents/`: Implementaciones de agentes (por ejemplo, BuilderBot, ExplorerBot, MinerBot).
  - `mcpi/`: Librería Python para interactuar con Minecraft a través de RaspberryJuice.
  - `message_bus.py`: (Por implementar) Módulo para la comunicación entre agentes.
  - `commands/`, `strategies/`, `utils/`, `tests/`: Directorios para comandos, estrategias, utilidades y pruebas del sistema multi-agente.

## Requisitos

- **Windows**
- **Java** (para ejecutar el servidor Minecraft)
- **Python 3.x** (para el sistema multi-agente)

## Instrucciones de Uso

### 1. Iniciar el Servidor de Minecraft

1. Abre una terminal en Windows.
2. Navega a la carpeta `AdventuresInMinecraft-PC-master`.
3. Ejecuta el script:
   ```powershell
   StartServer.bat
   ```
   Esto iniciará el servidor Minecraft con el plugin RaspberryJuice.

### 2. Ejecutar el Sistema Multi-Agente

1. Abre otra terminal.
2. Navega a la carpeta `Multi-Agent_System`.
3. Ejecuta tu agente o el sistema principal:
   ```powershell
   python main.py
   ```

## Créditos y Licencias

- Basado en el kit de "Adventures in Minecraft" de David Whale y Martin O'Hanlon.
- El plugin RaspberryJuice y las librerías `mcpi` están bajo sus respectivas licencias.

---

Para más detalles, consulta los archivos README de cada subcarpeta o la documentación del código fuente.
