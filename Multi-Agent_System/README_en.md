# Minecraft Multi-Agent Framework

[Español](README.md)

This directory contains the core of the **Multi-Agent System** for Minecraft. It implements an architecture based on autonomous agents (Explorer, Builder, Miner) that communicate to collaborate on construction and mining tasks.

## Agents 

### ExplorerBot
Analyzes the terrain and identifies optimal zones for construction.

### MinerBot
Extracts or simulates materials needed for construction using different mining strategies.

### BuilderBot
Builds the structure using materials provided by MinerBot, following plans derived from ExplorerBot's terrain analysis.

## Chat Commands (In-Game)
To execute commands, open the Minecraft chat (`T`) and type starting with `./`.

### System Management (AgentManager)

1.  **`create`**
    ```text
    ./create <AgentType> [id=<CustomID>]
    ```
    Creates a new instance of a bot.
    *   `AgentType`: `explorer`, `builder`, `miner`.
    *   `id`: *(Optional)* Unique identifier (e.g., `explorer1`). Default: Random identifier.

---

### Global Commands (All Bots)
Commands that work for `ExplorerBot`, `BuilderBot`, and `MinerBot`.

```text
./<AgentType> <command> [id=<AgentID>]
```
*   `AgentType`: `explorer`, `builder`, `miner`.
*   `command`: **`stop`**: Stops all operations immediately.
*   `command`: **`pause`**: Temporarily pauses the task (saves exact state).
*   `command`: **`resume`**: Resumes the task from the pause point (loads checkpoint).
*   `command`: **`status`**: Shows the current state and task information.
*   `command`: **`help`**: Shows a list of available global and specific commands.
*   `id`: *(Optional)* Unique identifier (e.g., `explorer1`) to execute the command on a specific instance. Default: The message is shown for all instances.

---

### ExplorerBot Specific Commands
Responsible for scanning the terrain and reporting flat zones.

1.  **`start`**
    ```text
    ./explorer start [x=<int>] [z=<int>] [range=<int>] [id=<AgentID>]
    ```
    Starts exploration.
    *   `x`, `z`: *(Optional)* Coordinates. Default: player's position.
    *   `range`: *(Optional)* Scanning radius. Default: 15.
    *   `id`: *(Optional)* Unique identifier (e.g., `explorer1`) to execute the command on a specific instance. Default: The command executes for all instances.

2.  **`set range`**
    ```text
    ./explorer set range <int> [id=<AgentID>]
    ```
    Updates the scanning radius without restarting.
    *   `int`: value of the new scanning radius.
    *   `id`: *(Optional)* Unique identifier (e.g., `explorer1`) to execute the command on a specific instance. Default: The command executes for all instances.

---

### MinerBot Specific Commands
Responsible for obtaining resources.

1.  **`start`**
    ```text
    ./miner start [x=<int>] [y=<int>] [z=<int>] [id=<AgentID>]
    ```
    Starts mining.
    *   `x`, `y`, `z`: *(Optional)* Coordinates. Default: player's position.
    *   `id`: *(Optional)* Unique identifier (e.g., `miner1`) to execute the command on a specific instance. Default: The command executes for all instances.
    *   Default strategy: gridStrategy

2.  **`set strategy`**
    ```text
    ./miner set strategy <vertical|grid|vein> [id=<AgentID>]
    ```
    Dynamically changes the mining strategy.
    *   `vertical`: Vertical mining.
    *   `grid`: Grid mining.
    *   `vein`: Vein mining.
    *   `id`: *(Optional)* Unique identifier (e.g., `miner1`) to execute the command on a specific instance. Default: The command executes for all instances.

3.  **`fulfill`**
    ```text
    ./miner fulfill [id=<AgentID>]
    ```
    Starts gathering based on the "Bill of Materials" (BOM) received from BuilderBot.
    *   `id`: *(Optional)* Unique identifier (e.g., `miner1`) to execute the command on a specific instance. Default: The command executes for all instances.

---

### BuilderBot Specific Commands
Responsible for managing plans and building structures block by block.

1.  **`build`**
    ```text
    ./builder build [id=<AgentID>]
    ```
    Starts construction at the position found by ExplorerBot.
    *   `id`: *(Optional)* Unique identifier (e.g., `builder1`) to execute the command on a specific instance. Default: The command executes for all instances.

2.  **`plan list`**
    ```text
    ./builder plan list [id=<AgentID>]
    ```
    Shows all available designs (`.schem`) in `builder_structures/` in the chat.
    *   `id`: *(Optional)* Unique identifier (e.g., `builder1`) to execute the command on a specific instance. Default: The command executes for all instances.


3.  **`plan set`**
    ```text
    ./builder plan set <Template> [id=<AgentID>]
    ```
    Assigns the design to build.
    *   `<Template>`: Name of the design to build (e.g., `small_medieval_hovel`).
    *   `id`: *(Optional)* Unique identifier (e.g., `builder1`) to execute the command on a specific instance. Default: The command executes for all instances.
   

4.  **`bom`** (Bill Of Materials)
    ```text    
    ./builder bom [id=<AgentID>]
    ```
    Forces calculation and sending of the required materials list to MinerBot.
    *   `id`: *(Optional)* Unique identifier (e.g., `builder1`) to execute the command on a specific instance. Default: The command executes for all instances.

---

### Workflow Execution
Automates the coordination of all bots (Exploration -> Design -> Mining -> Construction).

```text
./workflow run [x=<int>] [z=<int>] [range=<int>] [template=<name>] [miner.strategy=<vertical|grid|vein>]
```
*   `x`, `z`: *(Optional)* Central exploration coordinates. Default: current position.
*   `range`: *(Optional)* Explorer scanning radius. Default: `15`.
*   `template`: *(Optional)* Name of the structure to build (e.g., `small_medieval_hovel`). Default: `small_ovni`
*   `miner.strategy`: *(Optional)* Mining strategy (`vertical`, `grid`, `vein`). Default: `gridStrategy`.
