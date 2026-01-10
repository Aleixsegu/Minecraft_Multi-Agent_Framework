import asyncio
import os
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from agents.state_model import State
from strategies.mining_strategy import MiningStrategy
from utils.block_translator import get_block_id,get_block_name

# CONSTANTES: Materiales que sí vamos a minar físicamente (poniendo bloques de aire)
# El resto se tratarán como "suministro creativo" (se añaden al inventario tras una espera).
EASY_TO_MINE = {
    'stone', 'grass', 'dirt', 'cobblestone', 'sand', 'gravel', 
    'log', 'wood', 'planks', 'leaves', 'coal_ore', 'iron_ore'
}

class MinerBot(BaseAgent):

    """
    MinerBot: Funcines principales 
    - Filtra mensajes por ID.
    - Respeta zonas de construcción (Locking).
    - Alterna entre minería física y creativa.
    - Carga estrategias dinámicamente.
    """
 
    """
    Constructor
    """
    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)
        self.bom_received = False
        self.load_strategy_dynamically("VerticalStrategy")
        self.context.update({
            # Datos en formato STRING (para mensajes JSON)
            'inventory': {},          
            'requirements': {},       
            
            # Datos en formato INT (para la estrategia)
            'inventory_ids': {},
            'requirements_ids': {},
            
            'mining_active': False,
            'current_zone': None,
            'forbidden_zones': [],
            'has_lock': False,
            'builder_id_request': None,
            
            # Colas de tareas (Strings)
            'tasks_physical': {},
            'tasks_creative': {}
        })

    async def perceive(self):
        
        # Escucha mensajes del bus (materials.requirements).
        try:
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            if msg:
                print(msg)
                target = msg.get('target')
                if target and target != "BROADCAST":
                    return 

                await self.handle_incoming_message(msg)
                msg_type = msg.get("type")
                payload = msg.get("payload", {})
                
                if msg_type == "materials.requirements.v1":
                    self._process_bom(payload)

                elif msg_type in ["region.lock.v1", "build.v1"]:
                    source = msg.get("source")
                    if source != self.id:
                        zone = payload.get("zone")
                        if zone:
                            self.context['forbidden_zones'].append(zone)

                elif msg_type == "region.unlock.v1":
                    zone = payload.get("zone")
                    if zone in self.context['forbidden_zones']:
                        self.context['forbidden_zones'].remove(zone)

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error en perceive: {e}")

    def _process_bom(self, payload):
        reqs = payload.get("requirements", {})
        sender = payload.get("sender") or payload.get("source") or payload.get("builder_id")
        
        self.context['requirements'] = reqs
        self.context['builder_id_request'] = sender
        
        # 1. Inicializar Inventarios (String e ID)
        for item in reqs:
            if item not in self.context['inventory']:
                self.context['inventory'][item] = 0
                
            # Crear entrada en ID map también
            bid = get_block_id(item)
            if bid is not None:
                if bid not in self.context['inventory_ids']:
                    self.context['inventory_ids'][bid] = 0

        # 2. Convertir Requisitos a IDs para la estrategia
        # Esto permite que la estrategia sepa qué buscar usando ints
        reqs_ids = {}
        for name, qty in reqs.items():
            bid = get_block_id(name)
            if bid is not None:
                reqs_ids[bid] = qty
        self.context['requirements_ids'] = reqs_ids

        # 3. Clasificar Tareas (Usando nombres para facilitar la lógica de control)
        easy_tasks = {k: v for k, v in reqs.items() if k in EASY_TO_MINE or 'stone' in k or 'dirt' in k}
        hard_tasks = {k: v for k, v in reqs.items() if k not in easy_tasks}

        self.context['tasks_physical'] = easy_tasks
        self.context['tasks_creative'] = hard_tasks
        self.context['mining_active'] = True
        
        asyncio.create_task(self.set_state(State.RUNNING, "BOM Processed"))

    async def decide(self):
        # self.mc.postToChat(f"MinerBot {self.id}: En fase de run (decision) al haber hecho el comando start")

        if self.state != State.RUNNING or not self.context.get('mining_active'):
            self.context['next_action'] = 'idle'
            return

        if self._is_order_complete():
            self.context['next_action'] = 'finish_delivery'
            return

        # Prioridad: Creativo (Rápido)
        creative_pending = [k for k, v in self.context['tasks_creative'].items() if self.context['inventory'].get(k, 0) < v]
        if creative_pending:
            self.context['current_target_material'] = creative_pending[0]
            self.context['next_action'] = 'mine_creative'
            return

        # Minería Física
        physical_pending = [k for k, v in self.context['tasks_physical'].items() if self.context['inventory'].get(k, 0) < v]
        if physical_pending:
            target_pos = (self.context.get('target_x', 0), self.context.get('target_z', 0))
            
            if self._is_zone_forbidden(target_pos):
                self.mc.postToChat(f"{self.id}: Zona ocupada. Esperando...")
                self.context['next_action'] = 'wait_zone'
            else:
                if not self.context.get('has_lock'):
                    self.context['next_action'] = 'acquire_lock'
                else:
                    self.context['next_action'] = 'mine_physical'
            return
        
        self.context['next_action'] = 'idle'

    def _is_order_complete(self):
        reqs = self.context.get('requirements', {})
        inv = self.context.get('inventory', {})
        return all(inv.get(m, 0) >= qty for m, qty in reqs.items())
    
    def _is_zone_forbidden(self, pos):
        """Devuelve True si 'pos' cae dentro de alguna forbidden_zone."""
        px, pz = pos
        for zone in self.context.get('forbidden_zones', []):
            zx, zz, r = zone.get('x', 0), zone.get('z', 0), zone.get('radius', 10)
            if (px - zx)**2 + (pz - zz)**2 <= r**2:
                return True
        return False
    
    async def act(self):
        # self.mc.postToChat(f"MinerBot {self.id}: En fase de run (accion) al haber hecho el comando start")
        action = self.context.get('next_action')
        
        if action == 'acquire_lock':
            await self._publish_lock()

        elif action == 'mine_creative':
            mat = self.context.get('current_target_material')
            qty_needed = self.context['requirements'][mat]
            self.logger.info(f"Generando {mat} (Creativo)...")
            await asyncio.sleep(1.0)
            self.context['inventory'][mat] = qty_needed # Llenar de golpe
            
            # Sincronizar ID map también por consistencia
            bid = get_block_id(mat)
            if bid: self.context['inventory_ids'][bid] = qty_needed
            
            await self._send_inventory_update()

        elif action == 'mine_physical':
            # --- ADAPTACIÓN A vertical_strategy.py ---
            if self.strategy:
                # 1. Preparar argumentos específicos que pide la estrategia
                reqs_ids = self.context.get('requirements_ids', {})
                inv_ids = self.context.get('inventory_ids', {})
                
                # Start Pos debe ser un diccionario {x, y, z}
                start_pos = {
                    'x': self.context.get('target_x', 0),
                    'y': self.context.get('target_y', 0),
                    'z': self.context.get('target_z', 0)
                }

                # 2. Llamar a mine() pasando los argumentos
                # La estrategia devuelve un booleano (True=Sigue trabajando, False=Terminó/Bedrock)
                # Y modifica inv_ids "in-place"
                active = await self.strategy.mine(reqs_ids, inv_ids, start_pos)
                
                # 3. Sincronizar cambios: IDs -> Strings
                # Detectamos cambios en inv_ids y actualizamos self.context['inventory']
                updated_something = False
                for bid, qty in inv_ids.items():
                    name = get_block_name(bid) # Convertir ID a String
                    if name == "unknown":
                        self.logger.warning(f"Unknown block ID encountered: {bid}")
                    if name:
                        old_qty = self.context['inventory'].get(name, 0)
                        if qty != old_qty:
                            self.context['inventory'][name] = qty
                            updated_something = True
                            self.logger.info(f"Estrategia recolectó: {name} (Total: {qty})")

                # 4. Enviar reporte si hubo cambios
                if updated_something:
                    await self._send_inventory_update()
                
                
                
                # --- FRENO DE MANO ---
                # Esta pausa es la que evita que el bucle consuma 100% CPU o sature el log
                await asyncio.sleep(0.2) 
                
                # Si la estrategia devolvió False, significa que tocó fondo o terminó esa columna
                if not active:
                    # Obtenemos el nombre de la clase de la estrategia actual
                    strat_name = self.strategy.__class__.__name__
                    self.mc.postToChat(f"[{self.id}] Fin de ciclo estrategia: {strat_name}")

                    # CASO 1: VerticalStrategy -> Completar inventario mágicamente
                    if strat_name == "VerticalStrategy":
                        self.mc.postToChat(f"[{self.id}] Vertical terminada. Rellenando inventario restante...")
                        # Copiamos lo que falta directamente al inventario
                        reqs = self.context.get('requirements', {})
                        for item, qty in reqs.items():
                            self.context['inventory'][item] = qty # Cumplir requisito
                        
                        # Notificar cambio inmediato
                        await self._send_inventory_update(status="RUNNING")
                        
                        # En el siguiente ciclo 'decide', detectará que está completo e irá a 'finish_delivery'
                    
                    # CASO 2: GridStrategy -> Mover start_pos
                    elif strat_name == "GridStrategy":
                        # Movemos 5 bloques en X (asumiendo grid de 5x5)
                        current_x = self.context.get('target_x')
                        new_x = current_x + 5
                        self.context['target_x'] = new_x
                        
                        self.mc.postToChat(f"[{self.id}] Grid terminada. Moviendo a X={new_x}...")
                        
                        # IMPORTANTE: Reiniciar la estrategia para que empiece de 0 en la nueva zona
                        self.load_strategy_dynamically("GridStrategy")
                    
                    # Pausa extra para notar el cambio
                    await asyncio.sleep(1.0)
           
    
            else:
                self.logger.warning("No strategy loaded.")
                await asyncio.sleep(2)

        elif action == 'finish_delivery':
            self.mc.postToChat(f"{self.id}: Pedido completado.")
            await self._send_inventory_update(status="SUCCESS")
            await self._release_lock()
            self.context['mining_active'] = False
            await self.set_state(State.IDLE, "Done")

        elif action == 'wait_zone':
            await asyncio.sleep(2.0)
        elif action == 'idle':
            await asyncio.sleep(0.1)

    async def _publish_lock(self):
        """Publica mensaje region.lock.v1 para avisar al Explorer/Builder."""
        x, z = self.context.get('target_x', 0), self.context.get('target_z', 0)
        radius = 5
        msg = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "type": "region.lock.v1",
            "source": self.id,
            "target": "BROADCAST",
            "status": "RUNNING",
            "payload": {"zone": {"x": x, "z": z, "radius": radius}, "reason": "mining"}
        }
        await self.bus.publish(self.id, msg)
        self.context['has_lock'] = True
        self.context['current_zone'] = msg['payload']['zone']
        self.logger.info(f"Zona bloqueada: {msg['payload']['zone']}")

    async def _release_lock(self):
        """Libera la zona ocupada."""
        if not self.context.get('has_lock'): 
            return
        
        msg = {
            "type": "region.unlock.v1",
            "source": self.id,
            "target": "BROADCAST",
            "payload": {
                "zone": self.context.get('current_zone')
            }
        }
        await self.bus.publish(self.id, msg)
        self.context['has_lock'] = False
        self.context['current_zone'] = None
        self.logger.info("Zona liberada.")

    async def _send_inventory_update(self, status="RUNNING"):
        target = self.context.get('builder_id_request') or "BROADCAST"
        msg = {
            "type": "inventory.v1",
            "source": self.id,
            "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "payload": self.context['inventory'],
            "status": status
        }
        await self.bus.publish(self.id, msg)

    async def run(self):
        self.logger.info("MinerBot iniciado")
        await super().run()

    def setup_subscriptions(self):
        """Suscripciones específicas del MinerBot."""
        super().setup_subscriptions()
        
        # Comandos: start, set, fulfill
        # 1. Comandos de control
        for cmd in ["start", "set", "fulfill", "stop", "pause", "resume"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")

        self.bus.subscribe(self.id, f"materials.requirements.v1")

        """
        # 3. Coordinación (Locks): Escuchar a Explorer y Builder
        self.bus.subscribe(self.id, "region.lock.v1")
        self.bus.subscribe(self.id, "region.unlock.v1")
        self.bus.subscribe(self.id, "build.v1") # El builder avisa cuando construye"""

    async def handle_command(self, command: str, payload=None):
        
        
        payload = payload or {}
        
        if command in ["stop", "pause"]:
            await self._release_lock()
        await super().handle_command(command, payload)

        # Verificar ID si está presente en el payload (depende del parser, pero asumimos que puede venir)
        # El comando ./miner start <id> implica que el parser dirige esto o lo pone en payload.
        target_id = payload.get("id") or payload.get("target_id")
        if target_id and target_id != self.id:
            return

        if command == "start":
            # ./miner start <id> [x=.. z=.. y=..]
            
            x = payload.get("x")
            y = payload.get("y")
            z = payload.get("z")

            if x is None or z is None:
                try:
                    pos = self.mc.player.getTilePos()
                    x = pos.x
                    y = pos.y
                    z = pos.z
                except Exception as e:
                    self.logger.error(f"Error obteniendo posición del jugador: {e}")
                    x = 0; y = 0; z = 0

            msg = f"{self.id}: Iniciando mineria en ({x}, {y}, {z})"
            if self.strategy:
                msg += f" con estrategia {self.strategy.__class__.__name__}"
            
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            self.context.update({'target_x': x, 'target_y': y, 'target_z': z})
            return

        elif command == "set":
            # ./miner set strategy <id> <vertical|grid|vein>
            
            if "strategy" in payload:
                strat_name = payload["strategy"]
                
                # Importar dinamicamente para evitar ciclos o cargas innecesarias
                from utils.reflection import get_all_strategies
                import os
                
                # Asumimos path relativo desde este archivo: ../strategies
                # Pero reflection pide el path absoluto o correcto.
                # src/agents -> src/strategies
                current_dir = os.path.dirname(os.path.abspath(__file__))
                strategies_dir = os.path.join(os.path.dirname(current_dir), "strategies")
                
                available_strategies = get_all_strategies(strategies_dir)
                
                # Buscar coincidencia (ej: "vertical" match "VerticalStrategy")
                selected_cls = None
                for name, cls in available_strategies.items():
                    if strat_name.lower() in name.lower():
                        selected_cls = cls
                        break
                
                if selected_cls:
                    self.strategy = selected_cls(self.mc, self.logger, self.id)
                    msg = f"{self.id}: Estrategia establecida a {selected_cls.__name__}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                else:
                    self.mc.postToChat(f"{self.id}: Estrategia '{strat_name}' no encontrada.")
            return

        elif command == "fulfill":
            # ./miner fulfill <id>
            if self.bom_received:
                await self.set_state(State.RUNNING, "fulfill command")
                self.mc.postToChat(f"{self.id}: BOM recibido. Iniciando mineria.")
            else:
                self.mc.postToChat(f"{self.id}: No se puede iniciar. BOM no recibido.")
            return

        await super().handle_command(command, payload)

    def load_strategy_dynamically(self, strat_name):
        """
        Carga la estrategia usando reflexión. 
        Busca en src/strategies/ y hace match parcial con el nombre.
        """
        from utils.reflection import get_all_strategies
        
        # Ruta dinámica a la carpeta strategies
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # src/
        strategies_dir = os.path.join(base_path, "strategies")
        
        available = get_all_strategies(strategies_dir)
        
        selected_cls = None
        for name, cls in available.items():
            if strat_name.lower() in name.lower():
                selected_cls = cls
                break
        
        if selected_cls:
            # Instanciamos la nueva estrategia
            self.strategy = selected_cls(self.mc, self.logger, self.id)
            # Opcional: pasarle las coords actuales si queremos persistencia de posición
            msg = f"{self.id}: Estrategia cambiada a {selected_cls.__name__}"
            self.logger.info(msg)
            self.mc.postToChat(msg)
        else:
            self.mc.postToChat(f"{self.id}: Estrategia '{strat_name}' no encontrada.")