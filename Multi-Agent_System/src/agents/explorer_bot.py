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
        self.range = 15 # rango por defecto

    async def perceive(self):
        try:
            # Comprovar mensajes
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
            # Comprobar si hay una tarea en segundo plano ejecutándose
            if self.context.get("scanning_in_progress", False):
                self.context["next_action"] = "wait_for_scan"
                return

            if "target_x" in self.context and "target_z" in self.context:
                
                # Si no hemos escaneado, decidimos ESCANEAR
                if not self.context.get("scan_complete", False):
                    self.context["next_action"] = "scan_environment"
                    self.logger.info("Decisión: Iniciar tarea de escaneo (segundo plano).")
                
                # Si ya escaneamos pero no hemos reportado, decidimos REPORTAR
                elif not self.context.get("report_sent", False):
                    self.context["next_action"] = "report_zones"
                    self.logger.info("Decisión: Finalizar reporte.")
                
                # Datos enviados, terminar misión
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
            self.context["report_sent"] = True
            
        elif action == "finish_mission":
            self.logger.info("Misión finalizada. Volviendo a IDLE.")
            await self.set_state(State.IDLE, "mission_completed")
            self.context["next_action"] = "idle"
            
        elif action == "wait_for_scan":
            pass

    def _decompose_to_rectangles(self, coords_list, min_x, min_z, max_x, max_z):
        """
        Descompone una lista de coordenadas en el menor número de rectángulos maximales (>=2x2).
        """
        width_map = max_x - min_x + 1
        length_map = max_z - min_z + 1
        
        # Construcción de la cuadrícula
        grid = [[0 for _ in range(width_map)] for _ in range(length_map)]
        for (gx, gz) in coords_list:
            grid[gz - min_z][gx - min_x] = 1
            
        rects = []
        
        while True:
            best_rect = None # (r_start, c_start, r_len, c_len)
            best_area = 0
            
            # Histograma para cada fila
            heights = [0] * width_map
            
            for r in range(length_map):
                for c in range(width_map):
                    if grid[r][c] == 1:
                        heights[c] += 1
                    else:
                        heights[c] = 0
                
                # Rectángulo más grande en histograma
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
        """Ayudante para descomponer y procesar un componente conectado."""
        rects = self._decompose_to_rectangles(
            s['coords'], s['min_x'], s['min_z'], s['max_x'], s['max_z']
        )
        
        h = s['h']
        vis_y = h
        
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
            await self.bus.publish("map.v1", msg)
            self.logger.info(f"Zona enviada: {width}x{length} (H={h})")
            
            # Visualizar con lana
            color_idx = color_idx_ref[0]
            color_idx_ref[0] = (color_idx + 1) % 14 
            block_data = color_idx + 1
            
            coord_list = rect['blocks']
            for (gx, gz) in coord_list:
                if (gx, gz) not in gold_set:
                    gold_set.add((gx, gz))
                    self.mc.setBlock(gx, vis_y, gz, 35, block_data)
            
            asyncio.create_task(cleanup_fn(coord_list, vis_y))

    # Serialización de checkpoints
    def _load_scan_state(self):
        """Deserializa el estado de escaneo desde self.context."""
        data = self.context.get('scan_state')
        if not data or not data.get('has_state'):
            return None
            
        def to_tuple(x):
            """Convierte 'x,y' o [x,y] a (x,y)."""
            if isinstance(x, str):
                try:
                    p = x.split(',')
                    return (int(p[0]), int(p[1]))
                except: return x
            elif isinstance(x, (list, tuple)):
                return tuple(x)
            return x
            
        stats = {}
        for k, v in data["stats"].items():
            r_k = to_tuple(k)
            # v['coords'] es lista de listas [[x,z],...] -> lista de tuplas
            v['coords'] = [tuple(c) for c in v['coords']]
            stats[r_k] = v
            
        parent = {}
        for k, v in data["parent"].items():
            parent[to_tuple(k)] = to_tuple(v)

        # Prev Cols: clave="z" (str) -> valor=[x,z]
        prev_col_labels = {}
        for k, v in data["prev_col_labels"].items():
            prev_col_labels[int(k)] = to_tuple(v)

        # Active Roots: lista de [x,z]
        active_roots = {to_tuple(k) for k in data["active_roots"]}
        
        # Estado de Columna Local (para reanudar a mitad de columna)
        curr_col_labels = {}
        if "curr_col_labels" in data:
            for k, v in data["curr_col_labels"].items():
                curr_col_labels[int(k)] = to_tuple(v)
        
        active_roots_this_col = set()
        if "active_roots_this_col" in data:
            active_roots_this_col = {to_tuple(k) for k in data["active_roots_this_col"]}

        resume_x = data.get("resume_x")
        resume_z = data.get("resume_z")
        
        self.logger.info(f"Estado de escaneo recuperado. Reanudando desde X={resume_x}, Z={resume_z}")
        return stats, parent, active_roots, prev_col_labels, curr_col_labels, active_roots_this_col, resume_x, resume_z

    def _clear_scan_state(self):
        """Limpia el estado de escaneo guardado del contexto."""
        if 'scan_state' in self.context:
            del self.context['scan_state']

    async def _scan_and_find_zones(self):
        """
        Escanea y procesa zonas usando Connected Component Labeling (Union-Find) en tiempo real.
        Soporta reanudación desde checkpoint serializado.
        """
        center_x = int(self.context.get('target_x', self.posX))
        center_z = int(self.context.get('target_z', self.posZ))
        radius = self.range 
        
        g_min_x = center_x - radius
        g_max_x = center_x + radius
        g_min_z = center_z - radius
        g_max_z = center_z + radius
        
        # State Initialization
        restored = self._load_scan_state()
        if restored:
            stats, parent, active_roots, prev_col_labels, saved_curr_col, saved_active_this, start_x, start_z = restored
            current_start_x = max(g_min_x, start_x)
            current_start_z = start_z
        else:
            stats = {}
            parent = {} 
            prev_col_labels = {} 
            active_roots = set()
            saved_curr_col = {}
            saved_active_this = set()
            current_start_x = g_min_x
            current_start_z = g_min_z

        visual_active_blocks = set() 
        color_idx_ref = [0]
        
        # Funciones de soporte
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
        
        async def cleanup_batch_diamonds(batch):
            await asyncio.sleep(2)
            for (bx, by, bz) in batch:
                if (bx, bz) not in visual_active_blocks:
                    self.mc.setBlock(bx, by, bz, 0)
        
        async def cleanup_zone_visuals(coords, y):
            await asyncio.sleep(5)
            for (gx, gz) in coords:
                self.mc.setBlock(gx, y, gz, 0) 
                if (gx, gz) in visual_active_blocks:
                    visual_active_blocks.remove((gx, gz))

        self.logger.info(f"Escaneo R={radius}. Inicio X={current_start_x}, Z={current_start_z}")
        
        try:
            for x in range(current_start_x, g_max_x + 1):
                # Init variables por columna
                if x == current_start_x and restored:
                    # Usar estado parcial guardado si se reanuda
                    curr_col_labels = saved_curr_col
                    active_roots_this_col = saved_active_this
                    z_start = current_start_z
                    # Resetear 'restored' para que las siguientes columnas empiecen frescas
                    restored = False 
                else:
                    curr_col_labels = {}
                    active_roots_this_col = set()
                    z_start = g_min_z
                
                col_diamonds = []

                for z in range(z_start, g_max_z + 1):
                    await asyncio.sleep(0)

                    # Comprobar Pausa/Interrupción dentro del bucle
                    is_paused = self.context.get('paused')
                    is_interrupted = self.context.get('interrupt')

                    if is_paused or is_interrupted:
                        # Guardar estado EXACTO a mitad de columna
                        self.context['scan_state'] = {
                            "stats": stats, "parent": parent, 
                            "prev_col_labels": prev_col_labels, "active_roots": active_roots,
                            "curr_col_labels": curr_col_labels, "active_roots_this_col": active_roots_this_col,
                            "resume_x": x, "resume_z": z, "has_state": True
                        }
                        if is_paused: 
                            self.logger.info(f"Pausado en X={x}, Z={z}")
                        
                        # eliminar diamantes parciales actuales al instante para evitar bloques congelados
                        if col_diamonds:
                            asyncio.create_task(cleanup_batch_diamonds(col_diamonds))
                            
                        return # Salir/Romper completamente

                    # Comprobación de Radio
                    if (x - center_x)**2 + (z - center_z)**2 > radius**2:
                        continue
                    
                    h = self.mc.getHeight(x, z)
                    vis_y = h 
                    
                    self.mc.setBlock(x, vis_y, z, 57)
                    col_diamonds.append((x, vis_y, z))
                    
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

                if col_diamonds:
                    asyncio.create_task(cleanup_batch_diamonds(col_diamonds))
 
                closed_roots = set()
                for r in active_roots:
                    real_root = find(r)
                    if real_root not in active_roots_this_col:
                        closed_roots.add(real_root)
                
                for r in closed_roots:
                    if self.context.get('interrupt'): break
                    await self._process_component(stats[r], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)
                    del stats[r]

                active_roots = active_roots_this_col
                prev_col_labels = curr_col_labels

            if not self.context.get('interrupt') and not self.context.get('paused'):
                for r in active_roots:
                    real_root = find(r)
                    if real_root in stats: 
                        await self._process_component(stats[real_root], visual_active_blocks, cleanup_zone_visuals, color_idx_ref)
                
                self._clear_scan_state()

        except Exception as e:
            self.logger.error(f"Error en escaneo: {e}")
            
        if not self.context.get('interrupt') and not self.context.get('paused'):
            self.logger.info("Exploración finalizada.")
            self.context["scan_complete"] = True
        elif self.context.get('paused'):
            self.logger.info("Exploración PAUSADA.")
        else:
            self.logger.info("Exploración INTERRUMPIDA (Estado Guardado).")

    async def _publish_zones(self):
        """Deprecated."""
        pass
    async def run(self):
        self.logger.info("ExplorerBot iniciado")
        self.context["scanning_in_progress"] = False 
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
        
        if command == "stop":
            msg = f"[{self.id}] Detenido"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            self.context['interrupt'] = True
            
            # Esperar a que el escaneo guarde estado y salga
            # Comprobamos si la tarea sigue corriendo
            waited = 0
            while self.context.get("scanning_in_progress", False) and waited < 50: 
                 await asyncio.sleep(0.1)
                 waited += 1
            
            await self.set_state(State.STOPPED, "stop command")
            return

        elif command == "start":
            if self.state == State.RUNNING:
                 self.mc.postToChat(f"[{self.id}] Ya estoy en ejecucion.")
                 return

            # Resetear flags
            self.context['interrupt'] = False
            self.context['paused'] = False
            
            # Coordenadas
            if "x" in payload and "z" in payload:
                x, z = payload["x"], payload["z"]
            else:
                try:
                    pos = self.mc.player.getTilePos()
                    self.posX, self.posZ = pos.x, pos.z
                    x, z = int(pos.x), int(pos.z)
                except:
                    x, z = 0, 0
            
            if "range" in payload:
                self.range = payload["range"]

            msg = f"[{self.id}] Iniciando exploracion en ({x}, {z}) con Rango={self.range}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            self.context.update({
                'target_x': x, 'target_z': z, 'range': self.range,
                'scan_complete': False, 'report_sent': False,
                'interrupt': False, 'paused': False
            })
            self._clear_scan_state()
            
            await self.set_state(State.RUNNING, "start command")
            return
            
        elif command == "pause":
            self.context["paused"] = True
            
            waited = 0
            while self.context.get("scanning_in_progress", False) and waited < 20:
                 await asyncio.sleep(0.1)
                 waited += 1
            
            # transición a estado PAUSED (guarda checkpoint)
            await self.set_state(State.PAUSED, "pause command")
            self.mc.postToChat(f"[{self.id}] Pausado")
            return

        elif command == "resume":
            # Cargar desde checkpoint
            loaded_context = self.checkpoint.load()
            if loaded_context:
                self.context.update(loaded_context)
                self.logger.info("Contexto cargado desde checkpoint.")
            
            self.context["paused"] = False
            self.context["interrupt"] = False
            self.context["scanning_in_progress"] = False
            
            self.mc.postToChat(f"[{self.id}] Reanudado")
            await self.set_state(State.RUNNING, "resume command")
            return
            
        elif command == "set":
            if "range" in payload:
                self.range = payload["range"]
                msg = f"[{self.id}] Rango actualizado a {self.range}"
                self.logger.info(msg)
                self.mc.postToChat(msg)
                self.context['range'] = self.range
            else:
                self.mc.postToChat(f"[{self.id}] El comando set requiere 'range'.")
            return
            
        if command == "status":
             stats_count = 0
             if self.context.get("scan_state") and "stats" in self.context["scan_state"]:
                stats_count = len(self.context["scan_state"]["stats"])
             
             msg = f"[{self.id}] Status: {self.state.name} | Range: {self.range} | Target: ({self.context.get('target_x')}, {self.context.get('target_z')})"
             self.mc.postToChat(msg)
             return

        elif command == "help":
             msg = f"[{self.id}] Comandos específicos: start [x=<int>] [z=<int>] [range=<int>] [id=<AgentID>] | set range <int> [id=<AgentID>]"
             self.mc.postToChat(msg)
             pass 

        await super().handle_command(command, payload)
