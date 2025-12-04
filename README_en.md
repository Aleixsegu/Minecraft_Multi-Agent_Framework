# TAP-Minecraft-Agent-Framework

[Español](README.md)

This project integrates a Minecraft server environment with a programmable multi-agent system in Python, designed for experimentation and development of intelligent agents within the Minecraft world.

## Project Structure

- **AdventuresInMinecraft-PC/**: Contains the preconfigured Minecraft server (version 1.12) and resources needed for agent connection.
  - `README.md`: Server environment information.
  - `StartServer.bat`: Script to easily start the Minecraft server on Windows.
  - `Server/`: Server files, configuration, and plugins.
- **Multi-Agent_System/**: Python platform for developing and running agents that interact with the Minecraft world.
  - `checkpoints/`: Folder for checkpoints or saved states.
  - `logs/`: Execution logs for agents and the system.
  - `src/`: Main source code for the multi-agent system.
    - `main.py`: Main entry point.
    - `agents/`: Agent implementations (BuilderBot, ExplorerBot, MinerBot, etc.).
    - `mcpi/`: Python library to interact with Minecraft via RaspberryJuice.
    - `strategies/`: Folder for agent strategies.
    - `structures/`: Folder for structures.
    - `utils/`: System utilities (parser, logging, message bus, etc.).
  - `tests/`: Folder for additional tests.

## Requirements

- **Windows**
- **Java** (to run the Minecraft server)
- **Python 3.x** (for the multi-agent system)

## Usage Instructions

### 1. Start the Minecraft Server

1. Open a Windows terminal.
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
   python main.py
   ```

## Credits and Licenses

- Based on the "Adventures in Minecraft" kit by David Whale and Martin O'Hanlon.
- The RaspberryJuice plugin and `mcpi` libraries are under their respective licenses.

---

For more details, check the README files in each subfolder or the source code documentation.
