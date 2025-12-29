# TAP-Minecraft-Agent-Framework

[Español](README.md)

This project integrates a Minecraft server environment with a programmable multi-agent system in Python, geared towards experimentation and development of intelligent agents within the Minecraft world.

## Project Structure

- **AdventuresInMinecraft-PC/**: Contains the pre-configured Minecraft server (version 1.12) and necessary resources for connecting with external agents.
  - `README.md`: Specific information about the server environment.
  - `StartServer.bat`: Script to easily start the server on Windows.
  - `Server/`: Server files, configuration, and plugins.
- **Multi-Agent_System/**: Python platform for developing and running agents.
  - `README.md`: Detailed documentation on commands and system usage.
  - `src/`: Main source code.
    - `main.py`: Main entry point.
    - `agents/`: Bot implementations (`ExplorerBot`, `BuilderBot`, `MinerBot`) and managers (`WorkflowManager`, `AgentManager`).
    - `strategies/`: Mining logic and specific behaviors.
    - `messages/`: Communication system (MessageBus and Parsers).
    - `utils/`: Utilities (block translator, logger, schematic reader).
    - `mcpi/`: Library for connecting with Minecraft.
  - `builder_structures/`: `.schem` files with building designs.
  - `checkpoints/`: Agent state persistence.
  - `logs/`: Execution and debug logs.
  - `tests/`: Unit and integration tests.

## Requirements

- **Windows**
- **Java** (to run the Minecraft server)
- **Python 3.x** (for the multi-agent system)

## Usage Instructions

### 1. Start the Minecraft Server

1. Open a terminal in Windows.
2. Navigate to the `AdventuresInMinecraft-PC` folder.
3. Run the script:
   ```powershell
   StartServer.bat
   ```
   This will start the Minecraft server with the RaspberryJuice plugin.

### 2. Run the Multi-Agent System

1. Open another terminal.
2. Navigate to the `Multi-Agent_System/src` folder.
3. Run the main system:
   ```powershell
   python StartFramework.py
   ```

## Credits and Licenses

- Based on the "Adventures in Minecraft" kit by David Whale and Martin O'Hanlon.
- The RaspberryJuice plugin and `mcpi` libraries are under their respective licenses.

---

For more details, check the README files in each subfolder or the source code documentation.
