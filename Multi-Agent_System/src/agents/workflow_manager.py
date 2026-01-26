import logging
import re
import asyncio

class WorkflowManager:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.logger = logging.getLogger("WorkflowManager")

    async def execute_workflow(self, command_str):
        """
        Parses and executes a workflow command.
        Command format: /workflow run x=100 z=200 range=50 template=house miner.strategy=grid
        """
        self.logger.info(f"Processing workflow: {command_str}")
        self.agent_manager.mc.postToChat("[Workflow] Inicializando secuencia...")
        
        args = self._parse_args(command_str)
        
        # --- PASO 0: OBTENER O CREAR AGENTES ---
        explorer = await self._ensure_agent("ExplorerBot", "ExplorerBot_WF")
        builder = await self._ensure_agent("BuilderBot", "BuilderBot_WF")
        miner = await self._ensure_agent("MinerBot", "MinerBot_WF")

        # --- PASO 1: CONFIGURAR MINERO (Pasivo) ---
        if 'miner.strategy' in args:
            strategy = args['miner.strategy']
            self.logger.info(f"Workflow: Configurando Minero con estrategia {strategy}")
            await miner.handle_command("set", {"strategy": strategy})
        
        await miner.handle_command("stop", {}) 
        await miner.handle_command("resume", {})

        # --- PASO 2: CONFIGURAR BUILDER (Pasivo) ---
        if 'template' in args:
            template = args['template']
            self.logger.info(f"Workflow: Configurando Builder con plantilla {template}")
            await builder.handle_command("plan", {"args": ["set", template]})
            await builder.handle_command("build", {})

        # --- PASO 3: DISPARAR EXPLORADOR (Activo) ---
        try:
            scan_range = int(args.get('range', 30))
            payload = {"range": scan_range}
            
            if 'x' in args and 'z' in args:
                x = int(args['x'])
                z = int(args['z'])
                payload['x'] = x
                payload['z'] = z
                self.logger.info(f"Workflow: Iniciando Exploración en ({x}, {z})")
                self.agent_manager.mc.postToChat(f"[Workflow] Objetivo: {x},{z}")
            else:
                self.logger.info(f"Workflow: Iniciando Exploración en posición del jugador")

            # AHORA ES SEGURO: El bot ya ha tenido tiempo de arrancar gracias al sleep en _ensure_agent
            await explorer.handle_command("start", payload)

        except ValueError as e:
            self.logger.error(f"Error parsing workflow coordinates: {e}")
            self.agent_manager.mc.postToChat("[Workflow] Error: Coordenadas invalidas.")

    async def _ensure_agent(self, agent_type, agent_id):
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
        
        # --- FIX DEFINITIVO ---
        # Si el agente es nuevo, su bucle 'run()' tarda unos milisegundos en arrancar 
        # y resetear el estado a IDLE. Si mandamos el comando 'start' antes de eso,
        # el reset lo borra.
        # Solución: Esperar 2 segundos ciegamente para dejar que el agente se estabilice.
        if created_new:
            self.logger.info(f"Workflow: Esperando arranque de {agent_id}...")
            await asyncio.sleep(2.0)
            
        return agent

    def _parse_args(self, command_str):
        args = {}
        cleaned = command_str.replace("/workflow run", "").strip()
        pattern = re.compile(r'([\w\.]+)=([^\s]+)')
        matches = pattern.findall(cleaned)
        for k, v in matches:
            args[k] = v
        return args