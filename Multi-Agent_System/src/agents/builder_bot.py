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
        self.context.update({'current_plan': None})
        BuilderBot.instances.append(agent_id)

    def setup_subscriptions(self):
        """Suscripciones específicas del BuilderBot."""
        super().setup_subscriptions()
        
        # Comandos específicos
        for cmd in ["plan", "bom", "build"]:
            self.bus.subscribe(self.id, f"command.{cmd}.v1")

        self.bus.subscribe(self.id, "map.v1")
        self.bus.subscribe(self.id, "inventory.v1")

    async def perceive(self):
        pass

    async def decide(self):
        pass

    async def act(self):
        pass

    async def run(self):
        self.logger.info("BuilderBot iniciado")
        await super().run()

    async def handle_command(self, command: str, payload=None):
        """Manejo de comandos específicos (plan, bom, build) + base."""
        payload = payload or {}
        args = payload.get("args", [])

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
                    structure_class = structures[plan_name]
                    # Asumimos que se instancia para obtener datos
                    instance = structure_class()
                    
                    if hasattr(instance, 'get_bom'):
                        bom = instance.get_bom()
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
