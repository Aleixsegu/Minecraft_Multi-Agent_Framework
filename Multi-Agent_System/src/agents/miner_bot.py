import asyncio
import os
import random
import time
from datetime import datetime, timezone
from agents.base_agent import BaseAgent
from agents.state_model import State
from utils.block_translator import get_block_id, get_block_name

# Materiales que sí vamos a minar físicamente
EASY_TO_MINE = {
    'stone', 'grass', 'dirt', 'cobblestone', 'sand', 'gravel', 
    'log', 'wood', 'planks', 'leaves', 'coal_ore', 'iron_ore',
    'oak_log', 'spruce_log', 'birch_log', 'jungle_log',
    'grass_block', 'sandstone'
}

class MinerBot(BaseAgent):
    """
    MinerBot: Funciones principales 
    - Filtra mensajes por ID.
    - Respeta zonas de construcción (Locking).
    - Alterna entre minería física y creativa.
    - Carga estrategias dinámicamente.
    """
 
    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)
        self.bom_received = False
        
        # Inicialización del contexto
        self.context.update({
            'inventory': {},          
            'requirements': {},       
            'inventory_ids': {},
            'requirements_ids': {},
            'mining_active': False,
            'current_zone': None,
            'forbidden_zones': [],
            'has_lock': False,
            'builder_id_request': None,
            'tasks_physical': {},
            'tasks_creative': {},
            'arrived_at_mine': False,
            'build_site_pos': None,
            'target_x': None,
            'target_y': None,
            'target_z': None,
            'home_x': None,
            'home_y': None,
            'home_z': None,
            'mining_attempts': 0,    # Contador para Vertical
            'mining_start_time': 0,  # Cronómetro para Grid
            'next_action': 'idle'
        })

        # Cargar estrategia por defecto
        self.load_strategy_dynamically("GridStrategy")

    def setup_subscriptions(self):
        super().setup_subscriptions()
        for cmd in ["start", "set", "fulfill", "stop", "pause", "resume"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")
            self.bus.subscribe(self.id, f"materials.requirements.v1")
            self.bus.subscribe(self.id, "region.lock.v1")
            self.bus.subscribe(self.id, "region.unlock.v1")
            self.bus.subscribe(self.id, "build.v1")

    async def run(self):
        self.logger.info("MinerBot iniciado")
        await super().run()

    async def perceive(self):
        try:
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            if msg:
                target = msg.get('target')
                if target and target != "BROADCAST" and target != self.id:
                    return 

                # Filtrar grupos
                sender = msg.get("source")
                partners = self.context.get("partners")
                if partners and sender and sender != "User" and sender != "System" and sender != "USER_CHAT" and sender != self.id:
                     if sender not in partners.values():
                         self.logger.debug(f"Mensaje ignorado de {sender}. Partners: {partners.values()}")
                         return 
                
                self.logger.info(f"Procesando mensaje: {msg.get('type')} de {sender}")
                await self.handle_incoming_message(msg)
                msg_type = msg.get("type")
                payload = msg.get("payload", {})
                
                if msg_type == "materials.requirements.v1":
                    self._process_bom(payload)

                elif msg_type in ["region.lock.v1", "build.v1"]:
                    source = msg.get("source")
                    if source != self.id:
                        zone = payload.get("zone")
                        if zone: self.context['forbidden_zones'].append(zone)

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
        build_pos = payload.get("build_position") 

        self.context['requirements'] = reqs
        self.context['builder_id_request'] = sender
        self.context['build_site_pos'] = build_pos
        self.bom_received = True 
        self.context['arrived_at_mine'] = False
        
        # Resetear inventario
        self.context['inventory'] = {} 
        self.context['inventory_ids'] = {}
        self.context['mining_attempts'] = 0 
        self.context['mining_start_time'] = time.time() # iniciar cronómetro


        # Guardar posicion donde se contruye la estructura
        try:
            pos = self.mc.player.getTilePos()
            self.context['home_x'] = pos.x
            self.context['home_y'] = pos.y
            self.context['home_z'] = pos.z
        except: pass

        # Calcular zona aleatoria
        if build_pos:
            bx = int(build_pos[0])
            bz = int(build_pos[1] if len(build_pos) < 3 else build_pos[2])
            offset_x = random.randint(50, 100) * (1 if random.random() > 0.5 else -1)
            offset_z = random.randint(50, 100) * (1 if random.random() > 0.5 else -1)
            self.context['target_x'] = bx + offset_x
            self.context['target_z'] = bz + offset_z
            self.context['target_y'] = None
            self.logger.info(f"Objetivo de minería: {self.context['target_x']}, {self.context['target_z']}")
        else:
            self._calculate_random_zone()

        # Inicializar inventarios
        for item in reqs:
            self.context['inventory'][item] = 0
            bid = get_block_id(item)
            if bid is not None: self.context['inventory_ids'][bid] = 0

        # IDs
        reqs_ids = {}
        for name, qty in reqs.items():
            bid = get_block_id(name)
            if bid is not None: reqs_ids[bid] = qty
        self.context['requirements_ids'] = reqs_ids

        # Clasificar
        easy_tasks = {k: v for k, v in reqs.items() if k in EASY_TO_MINE or 'stone' in k or 'dirt' in k or 'log' in k}
        hard_tasks = {k: v for k, v in reqs.items() if k not in easy_tasks}

        self.context['tasks_physical'] = easy_tasks
        self.context['tasks_creative'] = hard_tasks
        
        self.context['mining_active'] = True
        asyncio.create_task(self.set_state(State.RUNNING, "BOM Processed"))

    def _calculate_random_zone(self):
        hx = self.context.get('home_x', 0)
        hz = self.context.get('home_z', 0)
        # Aleatorio entre 50 y 100 bloques desde casa
        off_x = random.randint(50, 100) * (1 if random.random() > 0.5 else -1)
        off_z = random.randint(50, 100) * (1 if random.random() > 0.5 else -1)
        self.context['target_x'] = int(hx + off_x)
        self.context['target_z'] = int(hz + off_z)
        self.context['target_y'] = None

    async def decide(self):
        if self.state != State.RUNNING or not self.context.get('mining_active'):
            self.context['next_action'] = 'idle'
            return

        if self._is_order_complete():
            self.context['next_action'] = 'finish_delivery'
            return

        if self.context.get('mining_active') and not self.context.get('arrived_at_mine'):
             if self.context.get('target_x') is not None:
                self.context['next_action'] = 'initial_mine'
                return

        # Prioridad: Creativo
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
                self.mc.postToChat(f"[{self.id}] Zona ocupada. Esperando...")
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
        px, pz = pos
        for zone in self.context.get('forbidden_zones', []):
            zx, zz, r = zone.get('x', 0), zone.get('z', 0), zone.get('radius', 10)
            if (px - zx)**2 + (pz - zz)**2 <= r**2:
                return True
        return False
    
    async def act(self):
        action = self.context.get('next_action')
        
        if action == 'acquire_lock':
            await self._publish_lock()

        elif action == 'mine_creative':
            mat = self.context.get('current_target_material')
            qty_needed = self.context['requirements'][mat]
            self.logger.info(f"Generando {mat} (Creativo)...")
            await asyncio.sleep(1.0)
            self.context['inventory'][mat] = qty_needed
            bid = get_block_id(mat)
            if bid: self.context['inventory_ids'][bid] = qty_needed
            await self._send_inventory_update()

        elif action == 'initial_mine':
             mx = self.context.get('target_x')
             mz = self.context.get('target_z')
             if mx is not None and mz is not None:
                 await asyncio.sleep(2.0)
                 
                 found_y = 0
                 try:
                     found_y = self.mc.getHeight(mx, mz)
                 except: pass
                 
                 if found_y <= 0: found_y = 70
                 self.context['target_y'] = found_y
                 
                 strat_name = self.strategy.__class__.__name__ if self.strategy else "None"
                 self.mc.postToChat(f"[{self.id}] Iniciando mineria en ({mx}, {found_y}, {mz}) con estrategia {strat_name}")
            
             self.context['arrived_at_mine'] = True
             self.context['next_action'] = 'idle' 

        elif action == 'mine_physical':
            if self.strategy:
                strat_name = self.strategy.__class__.__name__

                # Control de tiempo (Grid)
                if "Grid" in strat_name:
                    start_time = self.context.get('mining_start_time', 0)
                    elapsed = time.time() - start_time
                    if elapsed > 300: # 5 minutos
                        self.mc.postToChat(f"[{self.id}] Se han pasado los 5 minutos de minado. El resto se sacara del creativo.")
                        # Rellenar
                        reqs = self.context.get('requirements', {})
                        for item, qty in reqs.items():
                            if item in self.context.get('tasks_physical', {}):
                                self.context['inventory'][item] = qty 
                                bid = get_block_id(item)
                                if bid: self.context['inventory_ids'][bid] = qty
                        
                        await self._send_inventory_update(status="RUNNING")
                        return

                # Validación de altura
                current_target_y = self.context.get('target_y', 0)
                if current_target_y <= 0:
                     try:
                        current_target_y = self.mc.getHeight(self.context['target_x'], self.context['target_z'])
                        self.context['target_y'] = current_target_y
                     except: pass
                
                if current_target_y <= 0:
                    self.mc.postToChat(f"[{self.id}] Error terreno. Reseteando posición...")
                    self.context['target_x'] += 5
                    self.context['target_y'] = 80
                    return

                start_pos = {
                    'x': self.context.get('target_x'), 
                    'y': current_target_y, 
                    'z': self.context.get('target_z')
                }
                
                active = await self.strategy.mine(
                    self.context['requirements_ids'], 
                    self.context.get('inventory_ids', {}), 
                    start_pos
                )
                
                updated = False
                for bid, qty in self.context.get('inventory_ids', {}).items():
                    name = get_block_name(bid)
                    if name:
                        old = self.context['inventory'].get(name, 0)
                        if qty != old:
                            self.context['inventory'][name] = qty
                            updated = True

                if updated:
                    await self._send_inventory_update(status="RUNNING")
                
                await asyncio.sleep(0.2) 
                
                if not active:
                    # estrategia terminada
                    self.context['mining_attempts'] += 1
                    attempts = self.context['mining_attempts']
                    
                    if attempts >= 5 and "Vertical" in strat_name:
                        self.mc.postToChat(f"[{self.id}] Se han superado las 5 minadas. Se rellenara todo con el creativo.")
                        reqs = self.context.get('requirements', {})
                        for item, qty in reqs.items():
                            if item in self.context.get('tasks_physical', {}):
                                self.context['inventory'][item] = qty 
                                bid = get_block_id(item)
                                if bid: self.context['inventory_ids'][bid] = qty
                        await self._send_inventory_update(status="RUNNING")
                    
                    else:
                        # movimiento aleatorio para ambas estrategias
                        # calcular nuevas coordenadas aleatorias
                        self._calculate_random_zone()
                        
                        # intentar buscar la altura
                        new_x = self.context['target_x']
                        new_z = self.context['target_z']
                        ny = 70
                        try:
                            ny = self.mc.getHeight(new_x, new_z)
                            if ny <= 0: ny = 70
                            self.context['target_y'] = ny
                        except: pass
                        
                        # mensaje cambio de zona
                        self.mc.postToChat(f"[{self.id}] Ciclo {attempts} finalizado. Cambio de zona de mineria a ({new_x}, {ny}, {new_z}) con estrategia {strat_name}")
                        
                        # reiniciar estrategia
                        self.load_strategy_dynamically(strat_name, announce=False)
                    
                    await asyncio.sleep(1.0)
            else:
                self.logger.warning("Ninguna estrategia cargada.")
                await asyncio.sleep(2)

        elif action == 'finish_delivery':
            self.logger.info("MinerBot finish_delivery. Actualizando inventario.")
            await self._send_inventory_update(status="SUCCESS")
            await self._release_lock()
            self.context['mining_active'] = False
            await self.set_state(State.IDLE, "Done")

        elif action == 'wait_zone':
            await asyncio.sleep(2.0)
        elif action == 'idle':
            await asyncio.sleep(0.1)

    async def _publish_lock(self):
        x, z = self.context.get('target_x', 0), self.context.get('target_z', 0)
        msg = {
            "type": "region.lock.v1", "source": self.id, "target": "BROADCAST",
            "payload": {"zone": {"x": x, "z": z, "radius": 5}, "reason": "mining"}
        }
        await self.bus.publish(self.id, msg)
        self.context['has_lock'] = True
        self.context['current_zone'] = msg['payload']['zone']

    async def _release_lock(self):
        if not self.context.get('has_lock'): return
        msg = {
            "type": "region.unlock.v1", "source": self.id, "target": "BROADCAST",
            "payload": {"zone": self.context.get('current_zone')}
        }
        await self.bus.publish(self.id, msg)
        self.context['has_lock'] = False
        self.context['current_zone'] = None

    async def _send_inventory_update(self, status="RUNNING"):
        target = self.context.get('builder_id_request') or "BROADCAST"
        msg = {
            "type": "inventory.v1", "source": self.id, "target": target,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "payload": self.context['inventory'], "status": status
        }
        await self.bus.publish(self.id, msg)

    async def handle_command(self, command: str, payload=None):
        self.logger.info(f"Handle Command: {command}")
        payload = payload or {}
        if command in ["stop", "pause"]: await self._release_lock()
        
        if command == "status":
             strat_name = self.strategy.__class__.__name__ if self.strategy else "None"
             work_pos = f"({self.context.get('target_x')}, {self.context.get('target_y')}, {self.context.get('target_z')})"
             
             msg = f"[{self.id}] Status: {self.state.name} | Strat: {strat_name} | Target: {work_pos}"
             self.mc.postToChat(msg)
             return
            
        elif command == "help":
             msg = f"[{self.id}] Comandos específicos: start [x=<int>] [y=<int>] [z=<int>] [id=<AgentID>] | set strategy <vertical|grid|vein> [id=<AgentID>] | fulfill [id=<AgentID>]"
             self.mc.postToChat(msg)
             pass

        await super().handle_command(command, payload)

        if command == "start":
            x = payload.get("x"); z = payload.get("z")
            if x is not None and z is not None:
                self.context.update({'target_x': x, 'target_z': z})
                self.mc.postToChat(f"[{self.id}] Posicion manual: ({x}, {z})")
            else:
                self._calculate_random_zone()
                self.context['arrived_at_mine'] = False
                self.context['mining_active'] = True
                await self.set_state(State.RUNNING, "Manual Start")
            return

        elif command == "set":
            if "strategy" in payload: 
                should_announce = not payload.get("silent", False)
                self.load_strategy_dynamically(payload["strategy"], announce=should_announce)
            return

        elif command == "fulfill":
            if self.bom_received:
                await self.set_state(State.RUNNING, "fulfill")
                self.context['mining_active'] = True
                self.mc.postToChat(f"[{self.id}] Iniciando.")
            else:
                self.mc.postToChat(f"[{self.id}] Sin BOM.")
            return
        
    def load_strategy_dynamically(self, strat_name, announce=False):
        from utils.reflection import get_all_strategies
        import os
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        strategies_dir = os.path.join(base_path, "strategies")
        available = get_all_strategies(strategies_dir)
        selected_cls = None
        for name, cls in available.items():
            if strat_name.lower() in name.lower():
                selected_cls = cls
                break
        if selected_cls:
            self.strategy = selected_cls(self.mc, self.logger, self.id)
            if announce:
                msg = f"[{self.id}] Estrategia cambiada a: {selected_cls.__name__}"
                self.logger.info(msg)
                self.mc.postToChat(msg)
        else:
            self.mc.postToChat(f"[{self.id}] Estrategia '{strat_name}' no encontrada.")