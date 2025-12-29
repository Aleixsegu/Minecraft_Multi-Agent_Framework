import asyncio
import time
import datetime
import os
from agents.base_agent import BaseAgent
from agents.state_model import State
from utils.reflection import get_all_structures
from utils.block_translator import get_block_id

# Dynamic path to builder_structures
STRUCTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'builder_structures')

class BuilderBot(BaseAgent):
    
    # Mantiene registro de las instancias para evitar respuestas duplicadas en broadcasts informativos
    instances = []

    def __init__(self, agent_id, mc, bus):
        super().__init__(agent_id, mc, bus)     
        self.context.update({
            'current_plan': None,
            'task_phase': 'IDLE', # IDLE, ANALYZING_MAP, WAITING_MATERIALS, BUILDING
            'target_position': None,
            'plan_data': None, # Stores list of blocks to build
            'requirements': None,
            'inventory': {},
            'build_index': 0
        })
        BuilderBot.instances.append(agent_id)

    async def run(self):
        self.logger.info("BuilderBot iniciado")
        await super().run()

    def setup_subscriptions(self):
        """Suscripciones específicas del BuilderBot."""
        super().setup_subscriptions()
        
        # Suscribirse a comandos específicos
        specific_commands = ["plan", "build", "bom"]
        for cmd in specific_commands:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")
            
        # Suscribirse a datos necesarios
        self.bus.subscribe(self.id, "map.v1") # Recibir mapas del Explorer
        self.bus.subscribe(self.id, "inventory.v1")
    async def perceive(self):
        """
        Escucha mensajes del bus (map.v1, inventory.v1).
        """
        try:
            # Checkeo rápido de mensajes
            msg = await asyncio.wait_for(self.bus.receive(self.id), timeout=0.01)
            if msg:
                await self.handle_incoming_message(msg)
                
                # Procesa mensajes específicos de datos (no comandos)
                msg_type = msg.get("type")
                payload = msg.get("payload", {})
                
                if msg_type == "map.v1":
                    # Solo procesamos nuevos mapas si no estamos ocupados ya en una tarea avanzada
                    current_phase = self.context.get('task_phase')
                    if current_phase in ['IDLE', 'ANALYZING_MAP'] and self.context.get('current_plan'):
                         self.logger.info(f"{self.id} Received map candidate.")
                         self.context['latest_map'] = payload
                         self.context['task_phase'] = 'ANALYZING_MAP'
                         
                         # Wake up the agent loop
                         await self.set_state(State.RUNNING, "Map Received")
                    else:
                         self.logger.info(f"{self.id} Received map but ignored (Busy in {current_phase} or no plan).")
                
                elif msg_type == "inventory.v1":
                    self.logger.info(f"{self.id} Received inventory data.")
                    # El payload es { "iron": 12, ... }
                    self.context['inventory'] = payload
                    if self.context['task_phase'] == 'WAITING_MATERIALS':
                        # Trigger re-evaluación
                        await self.set_state(State.RUNNING, "Inventory Received")

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error en perceive (mensajes): {e}")

    async def decide(self):
        """
        Decide la siguiente acción basándose en el contexto y estado.
        """
        # Si está pausado, no decidimos nada nuevo
        if self.state == State.PAUSED:
            return

        phase = self.context.get('task_phase')
        
        # 1. Si estamos ANALIZANDO MAPA (Recibido map.v1)
        if phase == 'ANALYZING_MAP':
            try:
                zone_info = self.context.get('latest_map')
                plan_name = self.context.get('current_plan')
                
                if not zone_info or not plan_name:
                    self.context['task_phase'] = 'IDLE'
                    return
    
                structures = get_all_structures(STRUCTURES_DIR)
                if plan_name not in structures:
                    self.mc.postToChat(f"{self.id}: Plan {plan_name} not found.")
                    self.context['task_phase'] = 'IDLE'
                    return
    
                structure = structures[plan_name]
                
                # Check Dimensions
                zone_size = zone_info.get('size', (0, 0))
                zone_width, zone_length = zone_size
                s_width = getattr(structure, 'width', 0)
                s_length = getattr(structure, 'length', 0)
            
                # Simple check
                if s_width > zone_width or s_length > zone_length:
                     if (s_width > zone_length or s_length > zone_width):
                         self.logger.info(f"Zone too small for {plan_name} ({s_width}x{s_length} vs {zone_width}x{zone_length}). Ignoring.")
                         # Return to IDLE silently to wait for next map message
                         self.context['task_phase'] = 'IDLE'
                         return
                     
                # If OK
                self.context['requirements'] = structure.get_bom()
                
                # Calculate build origin
                # Prefer 'origin' (Top-Left corner) to keep inside zone.
                # If Schematic is 0-indexed from corner.
                if 'origin' in zone_info:
                    zc_x, zc_z = zone_info['origin']
                else:
                    # Fallback to center - (size/2) roughly? 
                    # For now just use center if origin missing (legacy)
                    zc_x, zc_z = zone_info.get('center', (0,0))
                
                self.context['target_position'] = (zc_x, zc_z)
                self.context['target_height'] = zone_info.get('average_height', 0)
                
                # Reset build progress
                self.context['blocks_to_build'] = structure.get_blocks()
                self.context['build_index'] = 0
                
                self.context['next_action'] = 'request_materials'
                
            except Exception as e:
                self.logger.error(f"Error analyzing map: {e}")
                self.context['task_phase'] = 'IDLE'
            
        # 2. ESPERANDO MATERIALES
        elif phase == 'WAITING_MATERIALS':
            # Check inventory vs requirements
            reqs = self.context.get('requirements', {})
            inv = self.context.get('inventory', {})
            
            missing = False
            missing_items = []
            for material, qty in reqs.items():
                if inv.get(material, 0) < qty:
                    missing = True
                    missing_items.append(f"{material}: {inv.get(material,0)}/{qty}")
            
            if not missing:
                self.mc.postToChat(f"{self.id}: Materials received. Ready to build!")
                self.logger.info(f"{self.id} Materials OK. Transitioning to start_building.")
                self.context['next_action'] = 'start_building'
            else:
                # Debug output throttled every 30s
                import time
                last_log = self.context.get('last_missing_log', 0)
                if time.time() - last_log > 30:
                     self.mc.postToChat(f"{self.id} Missing ({len(missing_items)}): {', '.join(missing_items[:3])}...")
                     self.context['last_missing_log'] = time.time()
                
                self.context['next_action'] = 'wait_materials'

        # 3. CONSTRUYENDO
        elif phase == 'BUILDING':
            if not self.context.get("building_in_progress", False):
                 self.context['next_action'] = 'resume_building'
            else:
                 self.context['next_action'] = 'wait_for_build'
            
        else:
            self.context['next_action'] = 'idle'


    async def act(self):
        """
        Ejecuta acciones.
        """
        action = self.context.get('next_action')
        
        if action == 'request_materials':
            plan_name = self.context.get('current_plan')
            bom = self.context.get('requirements')
            
            msg = {
                "type": "materials.requirements.v1",
                "sender": self.id,
                "target": "MinerBot",
                "payload": {
                    "structure": plan_name,
                    "requirements": bom,
                    "builder_id": self.id
                }
            }
            # Publish Request
            await self.bus.publish("materials_request", msg)
            self.logger.info(f"Sent material request: {bom}")
            
            self.mc.postToChat(f"{self.id}: Map valid. Sending BOM to MinerBot.")
            
            # --- SIMULATION (User Request) ---
            # Auto-deliver materials to self to bypass MinerBot
            self.mc.postToChat(f"{self.id} [SIM]: Auto-delivering SPECIFIC materials...")
            
            # Hardcoded items as requested + dynamic BOM
            sim_payload = {
                'iron_block': 64, 
                'redstone_wall_torch': 64, 
                'iron_trapdoor': 64, 
                'stone_slab': 64, 
                'lever': 64
            }
            # SIMULATION: Boost BOM quantities to ensure check passes (avoid exact match edge cases)
            if bom:
                for k, v in bom.items():
                    sim_payload[k] = v + 64

            fake_inv_msg = {
                "type": "inventory.v1",
                "sender": "MinerBot_Mock",
                "target": self.id,
                "payload": sim_payload
            }
            
            # DIRECT INJECTION (Skip Bus for simulation reliability)
            self.logger.info(f"Injecting simulated inventory keys: {list(sim_payload.keys())}")
            self.context['inventory'] = sim_payload
            
            # Also publish for consistency/logs, but we don't wait for it
            asyncio.create_task(self.bus.publish(self.id, fake_inv_msg))
            
            # WAKE UP IMMEDIATELY
            self.mc.postToChat(f"{self.id} [SIM]: Inventory Injected. Waking up...")
            self.context['task_phase'] = 'WAITING_MATERIALS'
            # Trigger check loop instantly by keeping it RUNNING if possible, 
            # though loop returns to perceive. perceive will see RUNNING?
            # Actually next loop iteration perceive runs. Then if running -> decide.
            # We need to ensure state is RUNNING.
            await self.set_state(State.RUNNING, "Simulated Inventory Injected")
            self.context['next_action'] = 'wait_materials' # decide will overwrite this if materials valid
            
        elif action == 'start_building' or action == 'resume_building':
             self.logger.info("Iniciando/Retomando construcción...")
             self.context['task_phase'] = 'BUILDING'
             self.context['building_in_progress'] = True
             # Launch background task
             asyncio.create_task(self._build_structure_task())
             self.context['next_action'] = 'wait_for_build'
        
        elif action == 'idle':
            pass

    async def _build_structure_task(self):
        """Tarea de construcción en background. Checkpoint-aware."""
        try:
            blocks = self.context.get('blocks_to_build', [])
            idx = self.context.get('build_index', 0)
            
            center = self.context.get('target_position') 
            if not center: return
            start_x, start_z = center
            
            base_y = self.context.get('target_height')
            if base_y is None: base_y = 65

            self.mc.postToChat(f"{self.id}: Start building {len(blocks)} blocks...")
            self.logger.info(f"Construyendo {len(blocks)} bloques desde índice {idx}...")

            while idx < len(blocks):
                # Check Pause
                if self.context.get('paused'):
                    self.logger.info("Construcción PAUSADA.")
                    self.context['build_index'] = idx
                    self.context['building_in_progress'] = False
                    # El estado general pasará a PAUSED vía comando, aquí solo salimos
                    return 

                # Check Stop (Interrupt)
                if self.context.get('interrupt'):
                    self.logger.info("Construcción DETENIDA.")
                    self.context['build_index'] = idx
                    self.context['building_in_progress'] = False
                    return

                # Build Batch (Speed limit)
                batch_size = 20 
                for _ in range(batch_size):
                    if idx >= len(blocks): break
                    
                    b = blocks[idx]
                    abs_x = int(start_x + b['x'])
                    abs_y = int(base_y + b['y'])
                    abs_z = int(start_z + b['z'])
                    
                    raw_name = b['block']
                    block_id = get_block_id(raw_name)
                    
                    # Debug first block placement to confirm coords
                    if idx == 0:
                        self.mc.postToChat(f"{self.id} First Block: {raw_name} -> ID:{block_id} at {abs_x},{abs_y},{abs_z}")
                    
                    self.mc.setBlock(abs_x, abs_y, abs_z, block_id)
                    idx += 1
                
                # Update progress
                self.context['build_index'] = idx
                
                # Yield to allow command processing
                await asyncio.sleep(0.05)

            # Finished
            self.mc.postToChat(f"{self.id}: Construccion completada!")
            self.context['task_phase'] = 'IDLE'
            self.context['building_in_progress'] = False
            self.context['build_index'] = 0
            self.context['blocks_to_build'] = []
            
        except Exception as e:
            msg = f"Error en construcción: {e}"
            self.logger.error(msg)
            self.mc.postToChat(f"{self.id}: {msg}")
            self.context['building_in_progress'] = False
            # Save checkpoint on error
            self.checkpoint.save(self.context)


    async def handle_command(self, command: str, payload=None):
        """Manejo de comandos específicos (plan, bom, build) + base."""
        payload = payload or {}
        args = payload.get("args", [])

        if command == "stop":
            msg = f"{self.id}: Deteniendo construcción..."
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            # Signal interrupt
            self.context['interrupt'] = True
            
            # Wait for task to exit gracefully
            waited = 0
            while self.context.get("building_in_progress", False) and waited < 50:
                await asyncio.sleep(0.1)
                waited += 1
                
            await self.set_state(State.STOPPED, "stop command")
            return
            
        elif command == "pause":
            val = args[0] if args else "1"
            should_pause = (val in ["1", "true", "on", "yes"])
            self.context["paused"] = should_pause
            
            msg = f"{self.id}: PAUSADO..."
            self.logger.info(msg)
            self.mc.postToChat(msg)
            
            # Wait for task to exit gracefully (save state)
            waited = 0
            while self.context.get("building_in_progress", False) and waited < 20:
                await asyncio.sleep(0.1)
                waited += 1

            await self.set_state(State.PAUSED, "pause command")
            return

        elif command == "resume":
            # Load checkpoint
            loaded = self.checkpoint.load()
            if loaded:
                self.context.update(loaded)
                self.logger.info("Contexto BuilderBot restaurado.")

            self.context["paused"] = False
            self.context["interrupt"] = False
            self.context["building_in_progress"] = False # Unlock decide loop
            
            self.mc.postToChat(f"{self.id}: REANUDANDO construcción...")
            await self.set_state(State.RUNNING, "resume command")
            return

        if command == "plan":
            # ./builder plan list
            # ./builder plan set <id> <template>
            subcmd = args[0] if len(args) > 0 else None
            
            if subcmd == "list":
                # Responder solo si es mensaje directo o si soy el líder (para broadcast)
                is_direct = "id" in payload
                is_leader = len(BuilderBot.instances) > 0 and self.id == BuilderBot.instances[0]

                if is_direct or is_leader:
                    structures = get_all_structures(STRUCTURES_DIR)
                    names = sorted(list(structures.keys()))
                    msg = f"Available plans: {', '.join(names)}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                return

            elif subcmd == "set":
                # Check Busy
                if self.context.get('task_phase') not in ('IDLE', None):
                     self.mc.postToChat(f"{self.id}: Occupied ({self.context.get('task_phase')}). Use stop first.")
                     return

                structures = get_all_structures(STRUCTURES_DIR)
                
                # Buscar si algún argumento coincide con un template
                template_name = None
                for arg in args[1:]:
                    if arg in structures:
                        template_name = arg
                        break
                
                if template_name:
                    self.context['current_plan'] = template_name
                    msg = f"{self.id}: Plan set to {template_name}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                    
                    # Si ya tenemos un mapa reciente, cambiamos a fase de analisis (auto-trigger)
                    if self.context.get('latest_map'):
                         self.context['task_phase'] = 'ANALYZING_MAP'
                         await self.set_state(State.RUNNING, "Plan Set with Map Ready")
                    else:
                         self.mc.postToChat(f"{self.id}: Waiting for map data...")
                else:
                    self.mc.postToChat(f"{self.id}: Template not found in arguments.")
                return

        elif command == "bom":
            # ./builder bom <id>
            # Muestra BOM informativo en chat
            plan_name = self.context.get('current_plan')
            if not plan_name:
                self.mc.postToChat(f"{self.id}: No plan set.")
                return

            structures = get_all_structures(STRUCTURES_DIR)
            if plan_name in structures:
                try:
                    structure = structures[plan_name]
                    if hasattr(structure, 'get_bom'):
                        bom = structure.get_bom()
                        msg = f"{self.id} BOM for {plan_name}: {bom}"
                        self.mc.postToChat(msg)
                    else:
                        self.mc.postToChat(f"Structure {plan_name} has no BOM.")
                except Exception as e:
                    self.logger.error(f"Error getting BOM: {e}")
            return

        elif command == "build":
            # ./builder build <id> -> TRIGGER explicitly the process
            plan_name = self.context.get('current_plan')
            if not plan_name:
                 self.mc.postToChat(f"{self.id}: No plan set. Use 'plan set' first.")
                 return
            
            # Check for map
            if not self.context.get('latest_map'):
                self.mc.postToChat(f"{self.id}: Waiting for map...")
            else:
                self.mc.postToChat(f"{self.id}: Map present. Analyzing...")
                self.context['task_phase'] = 'ANALYZING_MAP'
            return

        # Delegar al padre si no es uno de los nuestros
        await super().handle_command(command, payload)
