import logging
import re
import asyncio

class WorkflowManager:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.logger = logging.getLogger("WorkflowManager")
        self.active_workflows = 0

    async def execute_workflow(self, command_str):
        """
        Analiza y ejecuta un comando de workflow.
        Formato del comando: /workflow run x=100 z=200 range=50 template=house miner.strategy=grid
        """
        self.active_workflows += 1
        workflow_id = f"WF{self.active_workflows}" # ID único para esta ejecución
        
        self.logger.info(f"Processing workflow {workflow_id}: {command_str}")
        self.agent_manager.mc.postToChat(f"[{workflow_id}] Inicializando workflow")
        
        args = self._parse_args(command_str)
        
        # Crear agentes únicos para cada workflow
        explorer_id = f"ExplorerBot_{workflow_id}"
        builder_id = f"BuilderBot_{workflow_id}"
        miner_id = f"MinerBot_{workflow_id}"

        explorer = await self._ensure_agent("ExplorerBot", explorer_id, workflow_id)
        builder = await self._ensure_agent("BuilderBot", builder_id, workflow_id)
        miner = await self._ensure_agent("MinerBot", miner_id, workflow_id)

        # Conectarlos lógicamente vía Contexto (ID de Grupo) diciéndoles quiénes son sus compañeros.
        explorer.context['partners'] = {'builder': builder_id, 'miner': miner_id}
        builder.context['partners'] = {'explorer': explorer_id, 'miner': miner_id}
        miner.context['partners'] = {'explorer': explorer_id, 'builder': builder_id}

        # Configurar minero
        if 'miner.strategy' in args:
            strategy = args['miner.strategy']
            self.logger.info(f"[{workflow_id}] Configurando Minero {miner_id} con {strategy}")
            await miner.handle_command("set", {"strategy": strategy, "silent": True})
        
        # Configurar builder
        if 'template' in args:
            template = args['template']
            self.logger.info(f"[{workflow_id}] Configurando Builder {builder_id} con {template}")
            await builder.handle_command("plan", {"args": ["set", template], "silent": True})
            
        await builder.handle_command("build", {})

        # Configurar explorador
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
            else:
                self.logger.info(f"[{workflow_id}] Iniciando Exploración en posición del jugador")

            await explorer.handle_command("start", payload)

        except ValueError as e:
            self.logger.error(f"Error analizando coordenadas del workflow: {e}")
            self.agent_manager.mc.postToChat(f"[{workflow_id}] Error: Coordenadas invalidas.")

    async def _ensure_agent(self, agent_type, agent_id, group_id):
        """
        Recupera o crea el agente.
        Si se crea nuevo, espera obligatoriamente para evitar Race Condition.
        """
        agent = self.agent_manager.get_agent(agent_id)
        created_new = False
        
        if not agent:
            self.logger.info(f"Workflow: Creando agente {agent_id} ({agent_type})")
            agent = await self.agent_manager.create_agent(agent_type, agent_id)
            created_new = True
            
            # Etiquetar al agente con el ID de grupo
            if agent:
                agent.context['group_id'] = group_id
        
        if created_new:
            await asyncio.sleep(1.0)
            
        return agent

    def _parse_args(self, command_str):
        args = {}
        cleaned = command_str.replace("/workflow run", "").strip()
        pattern = re.compile(r'([\w\.]+)=([^\s]+)')
        matches = pattern.findall(cleaned)
        for k, v in matches:
            args[k] = v
        return args