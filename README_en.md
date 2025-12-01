# TAP-Minecraft-Agent-Framework

This project integrates a Minecraft server environment with a programmable multi-agent system in Python, designed for experimentation and development of intelligent agents within the Minecraft world.

## Project Structure

- **AdventuresInMinecraft-PC-master/**: Contains the preconfigured Minecraft server (version 1.12) and resources needed for agent connection.
  - `Server/`: Server files, configuration, and plugins (including RaspberryJuice for the Python API).
  - `StartServer.bat`: Script to easily start the Minecraft server on Windows.
- **Multi-Agent_System/**: Python platform for developing and running agents that interact with the Minecraft world.
  - `main.py`: Entry point for the multi-agent system.
  - `agents/`: Agent implementations (e.g., BuilderBot, ExplorerBot, MinerBot).
  - `mcpi/`: Python library to interact with Minecraft via RaspberryJuice.
  - `message_bus.py`: (To be implemented) Module for agent communication.
  - `commands/`, `strategies/`, `utils/`, `tests/`: Directories for commands, strategies, utilities, and tests for the multi-agent system.

## Requirements

- **Windows**
- **Java** (to run the Minecraft server)
- **Python 3.x** (for the multi-agent system)

## Usage Instructions

### 1. Start the Minecraft Server

1. Open a Windows terminal.
2. Navigate to the `AdventuresInMinecraft-PC-master` folder.
3. Run the script:
   ```powershell
   StartServer.bat
   ```
   This will start the Minecraft server with the RaspberryJuice plugin.

### 2. Run the Multi-Agent System

1. Open another terminal.
2. Navigate to the `Multi-Agent_System` folder.
3. Run your agent or the main system:
   ```powershell
   python main.py
   ```

## Credits and Licenses

- Based on the "Adventures in Minecraft" kit by David Whale and Martin O'Hanlon.
- The RaspberryJuice plugin and `mcpi` libraries are under their respective licenses.

---

For more details, check the README files in each subfolder or the source code documentation.
