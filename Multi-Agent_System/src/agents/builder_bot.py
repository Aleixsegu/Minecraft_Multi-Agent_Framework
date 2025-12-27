import asyncio
import time
import os
from agents.base_agent import BaseAgent
from agents.state_model import State
from utils.reflection import get_all_structures

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
                    self.logger.info(f"{self.id} Received map data.")
                    self.context['latest_map'] = payload
                    # Si recibimos un mapa, intentamos analizarlo si tenemos plan
                    if self.context.get('current_plan'):
                         self.context['task_phase'] = 'ANALYZING_MAP'
                
                elif msg_type == "inventory.v1":
                    self.logger.info(f"{self.id} Received inventory data.")
                    # El payload es { "iron": 12, ... }
                    self.context['inventory'] = payload
                    if self.context['task_phase'] == 'WAITING_MATERIALS':
                        # Trigger re-evaluación
                        pass

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.error(f"Error en perceive (mensajes): {e}")

    async def decide(self):
        """
        Decide la siguiente acción.
        """
        phase = self.context.get('task_phase')
        
        if phase == 'ANALYZING_MAP':
            # Verificar si el mapa sirve para la estructura
            zone_info = self.context.get('latest_map')
            plan_name = self.context.get('current_plan')
            
            if not zone_info or not plan_name:
                self.context['next_action'] = 'wait'
                return

            structures = get_all_structures(STRUCTURES_DIR)
            if plan_name not in structures:
                self.mc.postToChat(f"{self.id}: Plan {plan_name} not found.")
                # Go back to IDLE but keep listening? Warning: if we go IDLE we might stop analyzing.
                # Use IDLE to wait for new inputs.
                self.context['task_phase'] = 'IDLE'
                return

            structure = structures[plan_name]
            
            # Check size against zone size
            # Zone data: {center: (x,z), size: (w, l), average_height: y, ...}
            
            zone_size = zone_info.get('size', (0, 0))
            zone_width, zone_length = zone_size
            
            # Structure dims
            s_width = getattr(structure, 'width', 0)
            s_length = getattr(structure, 'length', 0)
             
            # Check size
            # We check if structure fits in the zone.
            if s_width > zone_width or s_length > zone_length:
                 # Check rotated?
                 if (s_width > zone_length or s_length > zone_width):
                     self.mc.postToChat(f"{self.id}: Zone too small for {plan_name} ({s_width}x{s_length} vs {zone_width}x{zone_length})")
                     # Return to IDLE to wait for next map message
                     self.context['task_phase'] = 'IDLE'
                     return
                 
            # If OK, calculate BOM and request materials
            self.context['requirements'] = structure.get_bom()
            
            # Calculate build origin to center the structure in the zone
            # Zone center (zc_x, zc_z)
            zc_x, zc_z = zone_info.get('center')
            
            # Use zone center as logical center, structure built relative to it?
            # Existing logic expected 'target_position' as center.
            self.context['target_position'] = (zc_x, zc_z)
            self.context['target_height'] = zone_info.get('average_height', 0)
            
            self.context['plan_object'] = structure # Store parser object
            
            self.context['next_action'] = 'request_materials'
            
        elif phase == 'WAITING_MATERIALS':
            # Check if inventory matches requirements
            reqs = self.context.get('requirements', {})
            inv = self.context.get('inventory', {})
            
            missing = False
            for material, qty in reqs.items():
                if inv.get(material, 0) < qty:
                    missing = True
                    break
            
            if not missing:
                self.mc.postToChat(f"{self.id}: Materials received. Ready to build!")
                self.context['next_action'] = 'start_building'
            else:
                self.context['next_action'] = 'wait_materials'

        elif phase == 'BUILDING':
            self.context['next_action'] = 'continue_building'
            
        else:
            self.context['next_action'] = 'idle'


    async def _build_task_wrapper(self):
        try:
            await self._build_structure_task()
        except Exception as e:
            self.logger.error(f"Error en tarea de construcción: {e}")
        finally:
            self.context["building_in_progress"] = False

    async def _build_structure_task(self):
        """Lógica de construcción completa en segundo plano."""
        # Prepare build list if not ready
        structure = self.context.get('plan_object')
        if not structure: return

        if not self.context.get('blocks_to_build'):
                self.context['blocks_to_build'] = structure.get_blocks()
                self.context['build_index'] = 0
        
        blocks = self.context.get('blocks_to_build', [])
        idx = self.context.get('build_index', 0)
        center = self.context.get('target_position') # (x, z)
        start_x, start_z = center if center else (0,0)
        
        base_y = self.context.get('target_height')
        if base_y is None:
            try:
                base_y = self.mc.player.getTilePos().y 
            except:
                base_y = 65

        while idx < len(blocks):
            # Check Interrupt
            if self.context.get('interrupt'):
                self.logger.info("Construcción DETENIDA por usuario.")
                self.context['task_phase'] = 'IDLE' # Reset
                self.context['interrupt'] = False
                self.context['build_index'] = idx # Save progress?
                return

            # Batch Size
            count = 0
            while idx < len(blocks) and count < 10:
                if self.context.get('interrupt'): break # Inner break

                b = blocks[idx]
                abs_x = start_x + b['x']
                abs_y = base_y + b['y']
                abs_z = start_z + b['z']
                
                block_id = 1 
                name = b['block'].lower()
                if "log" in name: block_id = 17
                elif "planks" in name: block_id = 5
                elif "cobble" in name: block_id = 4
                elif "glass" in name: block_id = 20
                elif "air" in name: block_id = 0 
                
                self.mc.setBlock(abs_x, abs_y, abs_z, block_id)
                idx += 1
                count += 1
            
            self.context['build_index'] = idx
            
            # Yield infrequently to execute batch fast but allow interrupts
            await asyncio.sleep(0.1)

        self.mc.postToChat(f"{self.id}: Building complete!")
        self.context['task_phase'] = 'IDLE'
        self.context['current_plan'] = None
        self.context['blocks_to_build'] = [] # Clear

    async def act(self):
        """
        Ejecuta acciones.
        """
        action = self.context.get('next_action')
        
        if action == 'request_materials':
            # Send BOM to MinerBot
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
            await self.bus.publish("materials_request", msg)
            self.logger.info(f"Sent material request: {bom}")
            self.mc.postToChat(f"{self.id}: Requested materials for {plan_name}")
            
            self.context['task_phase'] = 'WAITING_MATERIALS'
            
        elif action == 'start_building' or action == 'continue_building':
             if not self.context.get('building_in_progress'):
                 self.logger.info("Lanzando construcción en background...")
                 self.context['building_in_progress'] = True
                 self.context['task_phase'] = 'BUILDING'
                 asyncio.create_task(self._build_task_wrapper())
        
        elif action == 'wait_for_build':
            # Do nothing
            pass

    async def run(self):
        self.logger.info("BuilderBot iniciado")
        await super().run()

    async def handle_command(self, command: str, payload=None):
        """Manejo de comandos específicos (plan, bom, build) + base."""
        payload = payload or {}
        args = payload.get("args", [])

        if command == "stop":
            msg = f"{self.id}: Deteniendo construcción..."
            self.logger.info(msg)
            self.mc.postToChat(msg)
            self.context['interrupt'] = True
            await self.set_state(State.IDLE, "stop command")
            return

        if command == "plan":
            # ./builder plan list
            # ./builder plan set <id> <template>
            subcmd = args[0] if len(args) > 0 else None
            
            if subcmd == "list":
                # Solo responde el primer bot registrado para evitar spam
                if self.id == BuilderBot.instances[0]:
                    structures = get_all_structures(STRUCTURES_DIR)
                    names = list(structures.keys())
                    msg = f"Available plans: {', '.join(names)}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                return

            elif subcmd == "set":
                # ./builder plan set <id> <template> -> args=['set', '1', 'SimpleHouse']
                # ./builder plan set <template> -> args=['set', 'SimpleHouse']
                
                structures = get_all_structures(STRUCTURES_DIR)
                
                # Buscar si algún argumento coincide con un template
                template_name = None
                for arg in args[1:]:
                    if arg in structures:
                        template_name = arg
                        break
                
                # Si no encontramos template en args, quizas el parser lo tomó como ID y lo puso en payload['id']?
                # Pero hemos puesto templates en IGNORED_IDS, asi que siempre debe estar en args.
                
                if template_name:
                    self.context['current_plan'] = template_name
                    msg = f"{self.id}: Plan set to {template_name}"
                    self.logger.info(msg)
                    self.mc.postToChat(msg)
                else:
                    self.mc.postToChat(f"{self.id}: Template not found in arguments.")
                return

        elif command == "bom":
            # ./builder bom <id>
            plan_name = self.context.get('current_plan')
            if not plan_name:
                self.mc.postToChat(f"{self.id}: No plan set. Use 'plan set' first.")
                return

            structures = get_all_structures(STRUCTURES_DIR)
            if plan_name in structures:
                try:
                    structure = structures[plan_name]
                    
                    if hasattr(structure, 'get_bom'):
                        bom = structure.get_bom()
                        msg = f"{self.id} BOM for {plan_name}: {bom}"
                        self.mc.postToChat(msg)
                        self.logger.info(msg)
                        
                        # Enviar requerimientos al MinerBot
                        req_msg = {
                            "type": "materials.requirements.v1",
                            "sender": self.id,
                            "target": "MinerBot",
                            "payload": {
                                "structure": plan_name,
                                "requirements": bom,
                                "builder_id": self.id
                            }
                        }
                        # Publicamos al bus general para que lo capturen los mineros
                        await self.bus.publish("materials_request", req_msg)
                        self.logger.info(f"Requirement message sent: {req_msg}")
                        
                    else:
                        self.mc.postToChat(f"Structure {plan_name} has no get_bom() method.")
                        
                except Exception as e:
                    self.logger.error(f"Error executing BOM command: {e}")
                    self.mc.postToChat(f"Error retrieving BOM for {plan_name}.")
            return

        elif command == "build":
            # ./builder build <id>
            plan_name = self.context.get('current_plan')
            if not plan_name:
                 self.mc.postToChat(f"{self.id}: No plan set.")
                 return
                 
            self.logger.info(f"{self.id}: Starting build of {plan_name}")
            self.mc.postToChat(f"{self.id}: Building {plan_name}...")
            await self.set_state(State.RUNNING, "build command")
            return

        # Delegar al padre si no es uno de los nuestros
        await super().handle_command(command, payload)
