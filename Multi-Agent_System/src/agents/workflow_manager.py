import logging
import re
import asyncio
import uuid

class WorkflowManager:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.logger = logging.getLogger("WorkflowManager")
        self.active_workflows = 0

    async def execute_workflow(self, command_str):
        """
        Parses and executes a workflow command with ISOLATION.
        Command format: /workflow run x=100 z=200 range=50 template=house miner.strategy=grid
        """
        self.active_workflows += 1
        workflow_id = f"WF{self.active_workflows}" # Unique ID for this execution
        
        self.logger.info(f"Processing workflow {workflow_id}: {command_str}")
        self.agent_manager.mc.postToChat(f"[{workflow_id}] Inicializando workflow")
        
        args = self._parse_args(command_str)
        
        # --- PASO 0: OBTENER O CREAR AGENTES ÚNICOS ---
        # Suffix agents with the workflow ID to ensure they are unique pairs
        explorer_id = f"ExplorerBot_{workflow_id}"
        builder_id = f"BuilderBot_{workflow_id}"
        miner_id = f"MinerBot_{workflow_id}"

        explorer = await self._ensure_agent("ExplorerBot", explorer_id, workflow_id)
        builder = await self._ensure_agent("BuilderBot", builder_id, workflow_id)
        miner = await self._ensure_agent("MinerBot", miner_id, workflow_id)

        # Connect them logically via Context (Group ID) if needed, 
        # basically telling them who their partners are.
        # This requires the agents to respect 'target_group' or similar filter in perceive.
        # For now, we update their context with their partners' IDs.
        explorer.context['partners'] = {'builder': builder_id, 'miner': miner_id}
        builder.context['partners'] = {'explorer': explorer_id, 'miner': miner_id}
        miner.context['partners'] = {'explorer': explorer_id, 'builder': builder_id}

        # --- PASO 1: CONFIGURAR MINERO (Pasivo) ---
        if 'miner.strategy' in args:
            strategy = args['miner.strategy']
            self.logger.info(f"[{workflow_id}] Configurando Minero {miner_id} con {strategy}")
            await miner.handle_command("set", {"strategy": strategy, "silent": True})
        
        # Reset miner state to be sure - REMOVED per user request (noise)
        # await miner.handle_command("stop", {}) 
        # await miner.handle_command("resume", {})

        # --- PASO 2: CONFIGURAR BUILDER (Pasivo) ---
        if 'template' in args:
            template = args['template']
            self.logger.info(f"[{workflow_id}] Configurando Builder {builder_id} con {template}")
            await builder.handle_command("plan", {"args": ["set", template], "silent": True})
            
        # Explicitly tell builder who to listen to?
        # The builder listens to 'map.v1'. If multiple explorers publish 'map.v1', 
        # all builders receive it. We need to filter by source in the agents.
        await builder.handle_command("build", {})

        # --- PASO 3: DISPARAR EXPLORADOR (Activo) ---
        try:
            payload = {}
            if 'range' in args:
                 payload['range'] = int(args['range'])
            
            if 'x' in args and 'z' in args:
                x = int(args['x'])
                z = int(args['z'])
                payload['x'] = x
                payload['z'] = z
                self.logger.info(f"[{workflow_id}] Iniciando Exploración en ({x}, {z})")
                # self.agent_manager.mc.postToChat(f"[{workflow_id}] Objetivo: {x},{z}")
            else:
                self.logger.info(f"[{workflow_id}] Iniciando Exploración en posición del jugador")

            # AHORA ES SEGURO: El bot ya ha tenido tiempo de arrancar
            await explorer.handle_command("start", payload)

        except ValueError as e:
            self.logger.error(f"Error parsing workflow coordinates: {e}")
            self.agent_manager.mc.postToChat(f"[{workflow_id}] Error: Coordenadas invalidas.")

    async def _ensure_agent(self, agent_type, agent_id, group_id):
        """
        Recupera o crea el agente.
        Si se crea nuevo, ESPERA OBLIGATORIAMENTE para evitar Race Condition.
        """
        agent = self.agent_manager.get_agent(agent_id)
        created_new = False
        
        if not agent:
            self.logger.info(f"Workflow: Creando agente {agent_id} ({agent_type})")
            agent = await self.agent_manager.create_agent(agent_type, agent_id)
            created_new = True
            
            # Tag the agent with the group ID
            if agent:
                agent.context['group_id'] = group_id
        
        # --- FIX DEFINITIVO ---
        if created_new:
            # self.logger.info(f"Workflow: Esperando arranque de {agent_id}...")
            await asyncio.sleep(1.0) # Reduced wait time slightly as unique IDs reduce conflicts
            
        return agent

    def _parse_args(self, command_str):
        args = {}
        cleaned = command_str.replace("/workflow run", "").strip()
        pattern = re.compile(r'([\w\.]+)=([^\s]+)')
        matches = pattern.findall(cleaned)
        for k, v in matches:
            args[k] = v
        return args