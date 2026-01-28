# Minecraft Multi-Agent Framework

[English](README_en.md)

Este directorio contiene el núcleo del **Sistema Multi-Agente** para Minecraft. Implementa una arquitectura basada en agentes autónomos (Explorer, Builder, Miner) que se comunican para colaborar en tareas de construcción y minería.

## Agentes

### ExplorerBot
Analiza el terreno e identifica zonas óptimas de construcción.

### MinerBot
Extrae o simula materiales necesarios para la construcción utilizando diferentes estrategias de minería.

### BuilderBot
Construye la estructura utilizando materiales proporcionados por MinerBot, siguiendo los planos derivados del análisis del terreno de ExplorerBot.

## Comandos de Chat (In-Game)
Para ejecutar comandos, abre el chat de Minecraft (`T`) y escribe empezando por `./`.

### Gestión del Sistema (AgentManager)

1.  **`create`**
    ```text
    ./create <AgentType> [id=<CustomID>]
    ```
    Crea una nueva instancia de un bot.
    *   `AgentType`: `explorer`, `builder`, `miner`.
    *   `id`: *(Opcional)* Identificador único (ej: `explorer1`). Por defecto: Identificador aleatorio.

---

### Comandos Globales (Todos los Bots)
Comandos que funcionan para `ExplorerBot`, `BuilderBot` y `MinerBot`.

```text
./<AgentType> <command> [id=<AgentID>]
```
*   `AgentType`: `explorer`, `builder`, `miner`.
*   `command`: **`stop`**: Detiene todas las operaciones inmediatamente.
*   `command`: **`pause`**: Pausa temporalmente la tarea (guarda estado exacto).
*   `command`: **`resume`**: Reanuda la tarea desde el punto de pausa (carga checkpoint).
*   `command`: **`status`**: Muestra el estado actual y información de la tarea.
*   `command`: **`help`**: Muestra lista de comandos disponibles globales y específicos.
*   `id`: *(Opcional)* Identificador único (ej: `explorer1`) para ejecutar el comando sobre una instancia específica. Por defecto: El mensaje se muestra para todas las instancias.

---

### Comandos Específicos de ExplorerBot
Responsable de escanear el terreno y reportar zonas planas.

1.  **`start`**
    ```text
    ./explorer start [x=<int>] [z=<int>] [range=<int>] [id=<AgentID>]
    ```
    Inicia la exploración.
    *   `x`, `z`: *(Opcional)* Coordenadas. Por defecto: posición del jugador.
    *   `range`: *(Opcional)* Radio de escaneo. Por defecto: 15.
    *   `id`: *(Opcional)* Identificador único (ej: `explorer1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

2.  **`set range`**
    ```text
    ./explorer set range <int> [id=<AgentID>]
    ```
    Actualiza el radio de escaneo sin reiniciar.
    *   `int`: valor del nuevo radio de escaneo.
    *   `id`: *(Opcional)* Identificador único (ej: `explorer1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

---

### Comandos Específicos de MinerBot
Responsable de obtener recursos.

1.  **`start`**
    ```text
    ./miner start [x=<int>] [y=<int>] [z=<int>] [id=<AgentID>]
    ```
    Inicia la minería.
    *   `x`, `y`, `z`: *(Opcional)* Coordenadas. Por defecto: posición del jugador.
    *   `id`: *(Opcional)* Identificador único (ej: `miner1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.
    *   Estrategia por defecto: gridStrategy

2.  **`set strategy`**
    ```text
    ./miner set strategy <vertical|grid|vein> [id=<AgentID>]
    ```
    Cambia la estrategia de minería dinámicamente.
    *   `vertical`: Minería vertical.
    *   `grid`: Minería en cuadrícula.
    *   `vein`: Minería por vetas.
    *   `id`: *(Opcional)* Identificador único (ej: `miner1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

3.  **`fulfill`**
    ```text
    ./miner fulfill [id=<AgentID>]
    ```
    Inicia la recolección basada en la "Bill of Materials" (BOM) recibida del BuilderBot.
    *   `id`: *(Opcional)* Identificador único (ej: `miner1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

---

### Comandos Específicos de BuilderBot
Responsable de gestionar planos y construir estructuras bloque a bloque.

1.  **`build`**
    ```text
    ./builder build [id=<AgentID>]
    ```
    Inicia la construccion en la posicion encontrada por el explorerbot. 
    *   `id`: *(Opcional)* Identificador único (ej: `builder1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

2.  **`plan list`**
    ```text
    ./builder plan list [id=<AgentID>]
    ```
    Muestra en el chat todos los diseños (`.schem`) disponibles en `builder_structures/`.
    *   `id`: *(Opcional)* Identificador único (ej: `builder1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

3.  **`plan set`**
    ```text
    ./builder plan set <Template> [id=<AgentID>]
    ```
    Asigna el diseño a construir.
    *   `<Template>`: Nombre del diseño a construir (ej: `small_medieval_hovel`).
    *   `id`: *(Opcional)* Identificador único (ej: `builder1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.
   

4.  **`bom`** (Bill Of Materials)
    ```text    
    ./builder bom [id=<AgentID>]
    ```
    Fuerza el cálculo y envío de la lista de materiales requeridos al MinerBot.
    *   `id`: *(Opcional)* Identificador único (ej: `builder1`) para ejecutar el comando sobre una instancia específica. Por defecto: El comando se ejecuta para todas las instancias.

---

### Ejecución del Workflow
Automatiza la coordinación de todos los bots (Exploración -> Diseño -> Minería -> Construcción).

```text
./workflow run [x=<int>] [z=<int>] [range=<int>] [template=<name>] [miner.strategy=<vertical|grid|vein>]
```
*   `x`, `z`: *(Opcional)* Coordenadas centrales de exploración. Por defecto: posición actual.
*   `range`: *(Opcional)* Radio de escaneo del Explorer. Por defecto: `15`.
*   `template`: *(Opcional)* Nombre de la estructura a construir (ej: `small_medieval_hovel`). Por defecto: `small_ovni`
*   `miner.strategy`: *(Opcional)* Estrategia de minería (`vertical`, `grid`, `vein`). Por defecto: `gridStrategy`.
