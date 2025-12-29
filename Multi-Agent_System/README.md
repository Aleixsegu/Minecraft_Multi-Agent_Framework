# Minecraft Multi-Agent Framework

[English](README_en.md)

Este directorio contiene el núcleo del **Sistema Multi-Agente** para Minecraft. Implementa una arquitectura basada en agentes autónomos (Explorer, Builder, Miner) que se comunican para colaborar en tareas de construcción y minería.

## 🎮 Comandos de Chat (In-Game)
Para ejecutar comandos, abre el chat de Minecraft (`T`) y escribe empezando por `./`.

### 🌍 Comandos Globales (Todos los Bots)
Comandos que funcionan para `ExplorerBot`, `BuilderBot` y `MinerBot`.

```text
./<AgentType> <command> [id=<AgentID>]
```
1.  **`start`**: Inicia el comportamiento principal (Varía según el bot).
    *   *Nota: BuilderBot no usa `start`, usa `plan set`.*
2.  **`stop`**: Detiene todas las operaciones inmediatamente.
    *   *Opcional:* `id=<AgentID>` para detener uno específico.
3.  **`pause`**: Pausa temporalmente la tarea (guarda estado exacto).
4.  **`resume`**: Reanuda la tarea desde el punto de pausa (carga checkpoint).
5.  **`status`**: Muestra el estado actual (`IDLE`, `RUNNING`, etc.) y la fase de la tarea.
6.  **`help`**: Muestra lista de comandos disponibles en el log.

---

### 🚀 Agente Especial: Workflow
Automatiza la coordinación de todos los bots (Exploración -> Diseño -> Minería -> Construcción).

```text
./workflow run [x=<int>] [z=<int>] [range=<int>] [template=<name>] [miner.strategy=<vertical|grid|vein>]
```
**Parámetros:**
*   `x`, `z`: *(Opcional)* Coordenadas centrales de exploración (Por defecto: posición actual).
*   `range`: *(Opcional)* Radio de escaneo del Explorer (Por defecto: `50`).
*   `template`: *(Opcional)* Nombre de la estructura a construir (ej: `small_medieval_hovel`).
*   `miner.strategy`: *(Opcional)* Estrategia de minería (`vertical`, `grid`, `vein`).

---

### �️ ExplorerBot
Responsable de escanear el terreno y reportar zonas planas.

1.  **`start`**
    ```text
    ./explorer start [x=<int>] [z=<int>] [range=<int>]
    ```
    *   `x`, `z`: *(Opcional)* Coordenadas. Por defecto: posición del jugador.
    *   `range`: *(Opcional)* Radio de escaneo. Por defecto: preconfigurado o 50.

2.  **`set`**
    ```text
    ./explorer set range <int>
    ```
    *   Actualiza el radio de escaneo sin reiniciar.

---

### 🏗️ BuilderBot
Responsable de gestionar planos y construir estructuras bloque a bloque.

1.  **`plan list`**
    ```text
    ./builder plan list
    ```
    *   Muestra en el chat todos los diseños (`.schem`) disponibles en `builder_structures/`.

2.  **`plan set`**
    ```text
    ./builder plan set <TemplateName>
    ```
    *   Asigna el diseño a construir.
    *   *Requiere* que el Explorer haya enviado un mapa válido previamente, o inicia espera.

3.  **`bom`** (Bill Of Materials)
    ```text
    ./builder bom
    ```
    *   Fuerza el cálculo y envío de la lista de materiales requeridos al MinerBot.

---

### 💎 MinerBot
Responsable de obtener recursos.

1.  **`start`**
    ```text
    ./miner start [x=<int> y=<int> z=<int>]
    ```
    *   Inicia la minería en la ubicación dada (o actual del jugador).

2.  **`set`**
    ```text
    ./miner set strategy <vertical|grid|vein>
    ```
    *   Cambia la estrategia de minería dinámicamente.

3.  **`fulfill`**
    ```text
    ./miner fulfill
    ```
    *   Inicia la recolección basada en la "Bill of Materials" (BOM) recibida del BuilderBot.

---

### ⚙️ Gestión del Sistema (AgentManager)

1.  **`create`**
    ```text
    ./create <AgentType> [id=<CustomID>]
    ```
    *   Crea una nueva instancia de un bot.
    *   `AgentType`: `ExplorerBot`, `BuilderBot`, `MinerBot`.
    *   `id`: *(Opcional)* Identificador único (ej: `Explorer2`).

---

## 📂 Estructura de Proyecto

*   `src/agents/`: Lógica de comportamiento de cada bot.
*   `src/managers/`: Gestores de alto nivel (`WorkflowManager`).
*   `builder_structures/`: Coloca aquí tus archivos `.schem`.
*   `logs/`: Archivos `.jsonl` y `.log` para depuración detallada.