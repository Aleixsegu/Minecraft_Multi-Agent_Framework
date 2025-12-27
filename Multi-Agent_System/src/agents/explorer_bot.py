import asyncio
import asyncio
import datetime
from agents.base_agent import BaseAgent
from agents.state_model import State
class ExplorerBot(BaseAgent):
    """
    ExplorerBot:
    - Explora el entorno alrededor de una posición (x, z)
    - Devuelve mapas, altura del terreno, puntos de interés, biomasa o huecos
    - Informa al BuilderBot y MinerBot mediante el MessageBus
    - Sigue el ciclo PDA (Perception → Decision → Action)
    """
    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)
        self.posX = 0
        self.posZ = 0     
        self.range = 50                        # rango por defecto

    async def perceive(self):
        try:
            # Checkeo rápido de mensajes
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            if msg:
                await self.handle_incoming_message(msg)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error en perceive (mensajes): {e}")
            
    async def decide(self):
        """
        Decide la siguiente acción basándose en el contexto y estado.
        """
        # Si estamos en RUNNING, verificamos el progreso de la misión
        if self.state == State.RUNNING:
            # Check if a background task is already running
            if self.context.get("scanning_in_progress", False):
                self.context["next_action"] = "wait_for_scan"
                return

            if "target_x" in self.context and "target_z" in self.context:
                
                # 1. Si no hemos escaneado, decidimos ESCANEAR
                if not self.context.get("scan_complete", False):
                    self.context["next_action"] = "scan_environment"
                    self.logger.info("Decisión: Iniciar tarea de escaneo (segundo plano).")
                
                # 2. Si ya escaneamos pero no hemos reportado, decidimos REPORTAR
                # Note: Scanning task also reports, so this is just for state consistency
                elif not self.context.get("report_sent", False):
                    self.context["next_action"] = "report_zones"
                    self.logger.info("Decisión: Finalizar reporte.")
                
                # 3. Datos enviados, terminar misión
                else:
                    self.context["next_action"] = "finish_mission"
                    self.logger.info("Decisión: Finalizar misión.")
            else:
                self.context["next_action"] = "idle"

    async def _scan_task_wrapper(self):
        """Wrapper para ejecutar escaneo en segundo plano y manejar estado."""
        try:
            await self._scan_and_find_zones()
        except Exception as e:
            self.logger.error(f"Error en tarea de escaneo: {e}")
        finally:
            self.context["scanning_in_progress"] = False

    async def act(self):
        """Ejecuta la acción decidida."""
        action = self.context.get("next_action")
        
        if action == "scan_environment":
            self.logger.info("Lanzando escaneo en background...")
            self.context["scanning_in_progress"] = True
            asyncio.create_task(self._scan_task_wrapper())
            
        elif action == "report_zones":
            self.logger.info("Marcando reporte como completado...")
            # Scanning task handles logic, we just update state
            await self._publish_zones() # Deprecated call, does nothing
            self.context["report_sent"] = True
            
        elif action == "finish_mission":
            self.logger.info("Misión finalizada. Volviendo a IDLE.")
            await self.set_state(State.IDLE, "mission_completed")
            self.context["next_action"] = "idle"
            
        elif action == "wait_for_scan":
            # Do nothing, just wait for background task
            pass

    def _decompose_to_rectangles(self, coords_list, min_x, min_z, max_x, max_z):
        """
        Descompone una lista de coordenadas en el menor número de rectángulos maximales (>=2x2).
        """
        width_map = max_x - min_x + 1
        length_map = max_z - min_z + 1
        
        # Grid construction
        grid = [[0 for _ in range(width_map)] for _ in range(length_map)]
        for (gx, gz) in coords_list:
            grid[gz - min_z][gx - min_x] = 1
            
        rects = []
        
        while True:
            best_rect = None # (r_start, c_start, r_len, c_len)
            best_area = 0
            
            # Histogram for each row
            heights = [0] * width_map
            
            for r in range(length_map):
                for c in range(width_map):
                    if grid[r][c] == 1:
                        heights[c] += 1
                    else:
                        heights[c] = 0
                
                # Largest Rectangle in Histogram
                stack = [] # (index, height)
                for i, h in enumerate(heights + [0]):
                    start_index = i
                    while stack and stack[-1][1] > h:
                        index, height = stack.pop()
                        w = i - index
                        
                        if w >= 2 and height >= 2:
                            area = w * height
                            if area > best_area:
                                best_area = area
                                # Store: r_start is r - height + 1
                                best_rect = (r - height + 1, index, height, w)
                        start_index = index
                    stack.append((start_index, h))

            if best_rect:
                r_start, c_start, r_len, c_len = best_rect
                
                rect_origin_x = min_x + c_start
                rect_origin_z = min_z + r_start
                
                rect_coords = []
                for rr in range(r_start, r_start + r_len):
                    for cc in range(c_start, c_start + c_len):
                        grid[rr][cc] = 0
                        rect_coords.append((min_x + cc, min_z + rr))
                
                rects.append({
                    "origin": (rect_origin_x, rect_origin_z),
                    "size": (c_len, r_len),
                    "center": (rect_origin_x + c_len // 2, rect_origin_z + r_len // 2),
                    "blocks": rect_coords
                })
            else:
                break
        
        return rects

    async def _process_component(self, s, gold_set, cleanup_fn, color_idx_ref):
        """Helper to decompose and process a connected component."""
        rects = self._decompose_to_rectangles(
            s['coords'], s['min_x'], s['min_z'], s['max_x'], s['max_z']
        )
        
        h = s['h']
        vis_y = h # User request: "un bloque mas a bajo"
        
        for rect in rects:
            width, length = rect['size']
            zone_data = {
                "center": rect['center'],
                "origin": rect['origin'],
                "size": rect['size'],
                "average_height": int(h),
                "blocks": rect['blocks']
            }
            
            msg = {
                "type": "map.v1",
                "source": self.id,
                "target": "BROADCAST", 
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'),
                "status": "SUCCESS",
                "payload": zone_data
            }
            await self.bus.publish(self.id, msg)
            self.logger.info(f"Zona Rectangular detectada: {width}x{length}")
            
            # Visualize with Distinct Block (Wool)
            color_idx = color_idx_ref[0]
            color_idx_ref[0] = (color_idx + 1) % 14 
            block_data = color_idx + 1 # 1 to 14
            
            coord_list = rect['blocks']
            for (gx, gz) in coord_list:
                if (gx, gz) not in gold_set:
                    gold_set.add((gx, gz))
                    self.mc.setBlock(gx, vis_y, gz, 35, block_data)
            
            asyncio.create_task(cleanup_fn(coord_list, vis_y))

    async def _scan_and_find_zones(self):
        """
        Escanea y procesa zonas usando Connected Component Labeling (Union-Find) en tiempo real.
        - Robustez total para formas irregulares.
        - Detección: Une bloques contiguos de igual altura.
        - Cierre: Cuando un componente deja de tener bloques en la columna actual ("Frontera X"), se cierra.
        - Post-Proceso: Descompone el componente en rectángulos maximales (decompose).
        - Validación: Rectángulos >= 2x2.
        - Visualización: Diamante durante escaneo (H+1).
        - Visualización Zonas: Bloques de LANA de COLORES distintos para cada rectángulo (H+1).
        """
        center_x = int(self.context.get('target_x', self.posX))
        center_z = int(self.context.get('target_z', self.posZ))
        radius = self.range 
        
        g_min_x, g_max_x = center_x - radius, center_x + radius
        g_min_z, g_max_z = center_z - radius, center_z + radius
        
        # State:
        # visual_active_blocks: set of (x, z) that are part of a valid zone (showing color).
        visual_active_blocks = set()
        
        # Union-Find Structures
        parent = {}
        # stats: root_id -> {'min_x', 'max_x', 'min_z', 'max_z', 'h', 'coords': list of (x,z)}
        stats = {}
        
        def find(i):
            path = []
            while i != parent[i]:
                path.append(i)
                i = parent[i]
            for node in path:
                parent[node] = i
            return i

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
                # Merge stats into root_j
                s_i = stats[root_i]
                s_j = stats[root_j]
                s_j['min_x'] = min(s_i['min_x'], s_j['min_x'])
                s_j['max_x'] = max(s_i['max_x'], s_j['max_x'])
                s_j['min_z'] = min(s_i['min_z'], s_j['min_z'])
                s_j['max_z'] = max(s_i['max_z'], s_j['max_z'])
                s_j['coords'].extend(s_i['coords'])
                del stats[root_i]
            return root_j

        def new_component(x, z, h):
            idx = (x, z)
            parent[idx] = idx
            stats[idx] = {
                'min_x': x, 'max_x': x,
                'min_z': z, 'max_z': z,
                'h': h,
                'coords': [(x, z)]
            }
            return idx

        # Column tracking: z -> component_id (root not guaranteed, use find)
        prev_col_labels = {} 
        active_roots = set()
        
        # Color cycling reference (mutable list to pass by ref)
        color_idx_ref = [0] 

        self.logger.info(f"Exploración CCL+Decomposition en ({g_min_x},{g_min_z}) a ({g_max_x},{g_max_z})...")

        # Cleanup helpers
        async def cleanup_batch_diamonds(batch):
            await asyncio.sleep(5)
            for (bx, by, bz) in batch:
                if (bx, bz) not in visual_active_blocks:
                    self.mc.setBlock(bx, by, bz, 0)
        
        async def cleanup_zone_visuals(coords, y):
            """Limpia la zona de visualización (Lana) tras 5s."""
            await asyncio.sleep(5)
            for (gx, gz) in coords:
                self.mc.setBlock(gx, y, gz, 0) # Clear
                if (gx, gz) in visual_active_blocks:
                    visual_active_blocks.remove((gx, gz))

        # Scan Loop X
        for x in range(g_min_x, g_max_x + 1):
            curr_col_labels = {}
            active_roots_this_col = set()
            
            # Batch Visuals for this column
            col_diamonds = []

            # Scan Loop Z
            for z in range(g_min_z, g_max_z + 1):
                # Radius Check
                if (x - center_x)**2 + (z - center_z)**2 > radius**2:
                    continue
                
                h = self.mc.getHeight(x, z)
                
                # Visual: Diamond (Optimized Task Creation)
                vis_y = h + 1
                self.mc.setBlock(x, vis_y, z, 57)
                col_diamonds.append((x, vis_y, z))
                
                # CCL Logic
                current_id = new_component(x, z, h)
                
                # Merge Left
                if z in prev_col_labels:
                    prev_id = prev_col_labels[z]
                    root_prev = find(prev_id)
                    if stats[root_prev]['h'] == h:
                        current_id = union(current_id, root_prev)
                
                # Merge Up
                if (z - 1) in curr_col_labels:
                    up_id = curr_col_labels[z - 1]
                    root_up = find(up_id)
                    if stats[root_up]['h'] == h:
                        current_id = union(current_id, root_up)
                
                # Store
                current_id = find(current_id) 
                curr_col_labels[z] = current_id
                active_roots_this_col.add(current_id)
            
            # Schedule Cleanup for THIS column (One task per column > One task per block)
            if col_diamonds:
                asyncio.create_task(cleanup_batch_diamonds(col_diamonds))

            # Check Closed Components
            closed_roots = set()
            for r in active_roots:
                real_root = find(r)
                if real_root not in active_roots_this_col:
                    closed_roots.add(real_root)
            
            # Process Closed
            for r in closed_roots:
                await self._process_component(stats[r], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)
                del stats[r]

            # Update Active Roots
            active_roots = active_roots_this_col
            prev_col_labels = curr_col_labels
            
            # Yield less frequently (Every 10 cols instead of 5)
            if (x - g_min_x) % 10 == 0: await asyncio.sleep(0.001)

        # End: Process remaining active
        for r in active_roots:
            real_root = find(r)
            if real_root in stats: 
                await self._process_component(stats[real_root], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)

        self.logger.info("Exploración finalizada.")
        self.context["scan_complete"] = True

    async def _publish_zones(self):
        """Deprecated."""
        pass
    async def run(self):
        self.logger.info("ExplorerBot iniciado")
        await super().run()
    def setup_subscriptions(self):
        """Suscripciones específicas del ExplorerBot."""
        
        super().setup_subscriptions()
        
        # Comandos específicos: start, set, pause
        for cmd in ["start", "set", "pause"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")
    async def handle_command(self, command: str, payload=None):
        """Manejo de comandos específicos (start, set) + base."""
        payload = payload or {}
        # 1. Intentar manejar comandos específicos de ExplorerBot
        if command == "stop":
            msg = f"{self.id}: Deteniendo operaciones..."
            self.logger.info(msg)
            self.mc.postToChat(msg)
            # Set interrupt flag
            self.context['interrupt'] = True
            await self.set_state(State.IDLE, "stop command")
            return

        elif command == "start":
            # ... existing start logic ...
            # Reset interrupt flag
            self.context['interrupt'] = False
            # ...
            if "x" in payload and "z" in payload:
                x = payload["x"]
                z = payload["z"]
            else:
                try:
                    pos = self.mc.player.getTilePos()
                    self.posX = pos.x
                    self.posZ = pos.z
                    x = int(pos.x)
                    z = int(pos.z)
                except Exception as e:
                    self.logger.error(f"Error obteniendo posición del jugador: {e}")
                    self.posX = 0
                    self.posZ = 0
                    x = 0
                    z = 0
            
            if "range" in payload:
                self.range = payload["range"]

            msg = f"{self.id}: Iniciando exploracion rápida en ({x}, {z}) con Rango={self.range}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            self.context.update({
                'target_x': x, 
                'target_z': z, 
                'range': self.range,
                'scan_complete': False, 
                'report_sent': False,
                'interrupt': False, # Ensure False on start
                'paused': False # Ensure False on start
            })
            await self.set_state(State.RUNNING, "start command")
            return
            
        elif command == "pause":
            # ./explorer pause 1 -> args=['1']
            args = payload.get("args", [])
            val = args[0] if args else "1"
            
            should_pause = (val in ["1", "true", "on", "yes"])
            self.context["paused"] = should_pause
            
            status_str = "PAUSADO" if should_pause else "REANUDADO"
            msg = f"{self.id}: Exploración {status_str}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            return
            
        elif command == "set":
            # ... existing set logic ...
            if "range" in payload:
                self.range = payload["range"]
                msg = f"{self.id}: Rango actualizado a {self.range}"
                self.logger.info(msg)
                self.mc.postToChat(msg)
                self.context['range'] = self.range
            else:
                self.mc.postToChat(f"{self.id}: El comando set requiere 'range'.")
            return
            
        await super().handle_command(command, payload)

    async def _scan_and_find_zones(self):
        """
        Escanea y procesa zonas usando Connected Component Labeling (Union-Find).
        - Versión robusta secuencial (Single-Thread Async).
        - Escaneo lineal (Arriba-Abajo).
        - Detección unificada de zonas planas.
        - Soporte para interrupción inmediata (STOP).
        """
        center_x = int(self.context.get('target_x', self.posX))
        center_z = int(self.context.get('target_z', self.posZ))
        radius = self.range 
        
        g_min_x, g_max_x = center_x - radius, center_x + radius
        g_min_z, g_max_z = center_z - radius, center_z + radius
        
        # State
        visual_active_blocks = set()
        parent = {}
        stats = {}
        color_idx_ref = [0]
        
        # CCL Helpers
        def find(i):
            path = []
            while i in parent and i != parent[i]:
                path.append(i)
                i = parent[i]
            for node in path:
                parent[node] = i
            return i

        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
                s_i = stats[root_i]
                s_j = stats[root_j]
                s_j['min_x'] = min(s_i['min_x'], s_j['min_x'])
                s_j['max_x'] = max(s_i['max_x'], s_j['max_x'])
                s_j['min_z'] = min(s_i['min_z'], s_j['min_z'])
                s_j['max_z'] = max(s_i['max_z'], s_j['max_z'])
                s_j['coords'].extend(s_i['coords'])
                del stats[root_i]
            return root_j

        def new_component(x, z, h):
            idx = (x, z)
            if idx not in parent:
                parent[idx] = idx
                stats[idx] = {
                    'min_x': x, 'max_x': x,
                    'min_z': z, 'max_z': z,
                    'h': h,
                    'coords': [(x, z)]
                }
            return idx
        
        # Helpers
        async def cleanup_batch_diamonds(batch):
            await asyncio.sleep(1)
            for (bx, by, bz) in batch:
                if (bx, bz) not in visual_active_blocks:
                    self.mc.setBlock(bx, by, bz, 0)
        
        async def cleanup_zone_visuals(coords, y):
            await asyncio.sleep(5)
            for (gx, gz) in coords:
                self.mc.setBlock(gx, y, gz, 0) 
                if (gx, gz) in visual_active_blocks:
                    visual_active_blocks.remove((gx, gz))

        self.logger.info(f"Iniciando escaneo secuencial en R={radius}...")
        
        prev_col_labels = {} 
        active_roots = set()

        try:
            # SCAN LOOP X
            for x in range(g_min_x, g_max_x + 1):
                if self.context.get('interrupt'): break

                # PAUSE CHECK
                while self.context.get('paused'):
                    await asyncio.sleep(1)
                    if self.context.get('interrupt'): break
                if self.context.get('interrupt'): break 

                curr_col_labels = {}
                active_roots_this_col = set()
                col_diamonds = []

                # SCAN LOOP Z
                for z in range(g_min_z, g_max_z + 1):
                    # Yield every iteration
                    await asyncio.sleep(0)

                    # Pause Check
                    while self.context.get('paused'):
                        await asyncio.sleep(0.5)
                        if self.context.get('interrupt'): break
                    
                    if self.context.get('interrupt'): break
                    
                    # Radius Check
                    if (x - center_x)**2 + (z - center_z)**2 > radius**2:
                        continue
                    
                    h = self.mc.getHeight(x, z)
                    vis_y = h 
                    
                    # Visual: Diamond Trail
                    self.mc.setBlock(x, vis_y, z, 57)
                    col_diamonds.append((x, vis_y, z))
                    
                    # CCL Logic
                    current_id = new_component(x, z, h)
                    
                    if z in prev_col_labels:
                        prev_id = prev_col_labels[z]
                        root_prev = find(prev_id)
                        if stats[root_prev]['h'] == h:
                            current_id = union(current_id, root_prev)
                    
                    if (z - 1) in curr_col_labels:
                        up_id = curr_col_labels[z - 1]
                        root_up = find(up_id)
                        if stats[root_up]['h'] == h:
                            current_id = union(current_id, root_up)
                    
                    current_id = find(current_id) 
                    curr_col_labels[z] = current_id
                    active_roots_this_col.add(current_id)
                
                if self.context.get('interrupt'): break

                # Batch Cleanup
                if col_diamonds:
                    asyncio.create_task(cleanup_batch_diamonds(col_diamonds))

                # Check Closed
                closed_roots = set()
                for r in active_roots:
                    real_root = find(r)
                    if real_root not in active_roots_this_col:
                        closed_roots.add(real_root)
                
                # Process Closed
                for r in closed_roots:
                    if self.context.get('interrupt'): break
                    await self._process_component(stats[r], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)
                    del stats[r]

                active_roots = active_roots_this_col
                prev_col_labels = curr_col_labels
            
            # End Process remaining active
            if not self.context.get('interrupt'):
                for r in active_roots:
                    real_root = find(r)
                    if real_root in stats: 
                        await self._process_component(stats[real_root], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)

        except Exception as e:
            self.logger.error(f"Error en escaneo: {e}")

        if not self.context.get('interrupt'):
            self.logger.info("Exploración finalizada.")
            self.context["scan_complete"] = True
        else:
            self.logger.info("Exploración INTERRUMPIDA.")