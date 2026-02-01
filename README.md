# TAP-Minecraft-Agent-Framework

[English](README_en.md)

Este proyecto integra un entorno de servidor Minecraft con un sistema multi-agente programable en Python, orientado a la experimentación y desarrollo de agentes inteligentes dentro del mundo de Minecraft.

## Estructura del Proyecto

- **AdventuresInMinecraft-PC/**: Contiene el servidor de Minecraft preconfigurado (versión 1.12) y los recursos necesarios para la conexión con agentes externos.
  - `README.md`: Información específica del entorno del servidor.
  - `StartServer.bat`: Script para iniciar el servidor fácilmente en Windows.
  - `Server/`: Archivos del servidor, configuración y plugins.
- **Multi-Agent_System/**: Plataforma en Python para el desarrollo y ejecución de agentes.
  - `StartFramework.py`: Punto de entrada principal.
  - `README.md`: Documentación detallada de comandos y uso del sistema.
  - `src/`: Código fuente principal.
    - `main.py`: Punto de entrada con pequeños juegos de pruebas.
    - `agents/`: Implementaciones de bots (`ExplorerBot`, `BuilderBot`, `MinerBot`) y gestores (`WorkflowManager`, `AgentManager`).
    - `strategies/`: Lógica de minería y comportamiento específico.
    - `messages/`: Sistema de comunicación (MessageBus y Parsers).
    - `utils/`: Utilidades (traductor de bloques, logger, lector de esquemáticos).
    - `mcpi/`: Librería de conexión con Minecraft.
  - `builder_structures/`: Archivos `.schem` con diseños de construcción.
  - `checkpoints/`: Persistencia de estado de los agentes.
  - `logs/`: Registros de ejecución y depuración.
  - `tests/`: Tests unitarios y de integración.

## Requisitos

- **Windows**
- **Java** (para ejecutar el servidor Minecraft)
- **Python 3.x** (para el sistema multi-agente)

## Instrucciones de Uso

### 1. Iniciar el Servidor de Minecraft

1. Abre una terminal en Windows.
2. Navega a la carpeta `AdventuresInMinecraft-PC`.
3. Ejecuta el script:
   ```powershell
   StartServer.bat
   ```
   Esto iniciará el servidor Minecraft con el plugin RaspberryJuice.

### 2. Ejecutar el Sistema Multi-Agente

1. Abre otra terminal.
2. Navega a la carpeta `Multi-Agent_System/src`.
3. Ejecuta el sistema principal:
   ```powershell
   python StartFramework.py
   ```

### 3. Ejecutar los tests unitarios del sistema Multi-Agente

1. Abre otra terminal.
2. Crea un entorno virtual:
   ```powershell
   python -m venv venv
   ```
3. Activa el entorno virtual:
   ```powershell
   .\venv\Scripts\activate
   ```
4. Instala las dependencias:
   ```powershell
   pip install --upgrade pip
   pip install pytest pytest-cov pytest-asyncio mock 
   ```
5. Ejecuta los tests:
   ```powershell
   pytest
   ```

## Créditos y Licencias

- Basado en el kit de "Adventures in Minecraft" de David Whale y Martin O'Hanlon.
- El plugin RaspberryJuice y las librerías `mcpi` están bajo sus respectivas licencias.

---

Para más detalles, consulta los archivos README de cada subcarpeta o la documentación del código fuente.
- En el readme de la subcarpeta `Multi-Agent_System/` se encuentran los comandos disponibles para ejecutar en el chat de Minecraft.
- En el readme de la subcarpeta `AdventuresInMinecraft-PC/` se encuentran las instrucciones para iniciar y configurar el servidor de Minecraft.
