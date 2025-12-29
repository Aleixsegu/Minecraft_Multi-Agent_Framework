
import logging
import re

class WorkflowManager:
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        self.logger = logging.getLogger("WorkflowManager")

    async def execute_workflow(self, command_str):
        """
        Parses and executes a workflow command.
        Command format: /workflow run [x=<int> z=<int>] [range=<int>] [template=<name>] [miner.strategy=<...>] ...
        """
        self.logger.info(f"Processing workflow: {command_str}")
        
        args = self._parse_args(command_str)
        
        # 1. Setup ExplorerBot
        if 'range' in args:
            x = int(args.get('x', 0)) # Default to 0? Or current pos?
            z = int(args.get('z', 0))
            scan_range = int(args.get('range', 50))
            
            # Ensure Explorer exists
            explorer = self.agent_manager.get_agent("ExplorerBot1")
            if not explorer:
                explorer = await self.agent_manager.create_agent("ExplorerBot", "ExplorerBot1")
            
            # Reset/Stop if running?
            # explorer.stop() 
            
            # Explorer Start Command logic simulation
            # We can either directly call methods or simulate a chat command
            # Simulating chat command is safer for state transitions
            cmd = f"./explorer start {x} {z} {scan_range}"
            self.logger.info(f"Auto-starting Explorer: {cmd}")
            # We need a way to inject this command. 
            # If AgentManager has access to message parser or we can call handle_command directly.
            # BaseAgent.handle_command is async.
            await explorer.handle_command("start", [str(x), str(z), str(scan_range)])

        # 2. Setup BuilderBot (Prepare Plan)
        if 'template' in args:
            template = args['template']
            builder = self.agent_manager.get_agent("BuilderBot1")
            if not builder:
                builder = await self.agent_manager.create_agent("BuilderBot", "BuilderBot1")
                
            cmd = f"./builder plan set {template}"
            self.logger.info(f"Auto-setting Builder plan: {cmd}")
            # The 'plan set' command expects args: ['set', 'target_id'?, 'plan_name']
            # Based on previous interactions: ./builder plan set 1 <name>
            # args for handle_command: ['set', '1', template]
            await builder.handle_command("plan", ["set", "1", template])

        # 3. Setup MinerBot
        if 'miner.strategy' in args:
            strategy = args['miner.strategy']
            miner = self.agent_manager.get_agent("MinerBot1")
            if not miner:
                miner = await self.agent_manager.create_agent("MinerBot", "MinerBot1")
            
            # Parametros opcionales de miner
            mx = args.get('miner.x')
            my = args.get('miner.y')
            mz = args.get('miner.z')
            
            # start <strategy> [params...]
            cmd_args = [strategy]
            if mx and my and mz:
                cmd_args.extend([mx, my, mz])
                
            self.logger.info(f"Auto-starting Miner: ./miner start {' '.join(cmd_args)}")
            await miner.handle_command("start", cmd_args)

        self.agent_manager.mc.postToChat("[Workflow] Workflow initiated successfully.")

    def _parse_args(self, command_str):
        """
        Parses k=v arguments from string.
        """
        args = {}
        # Removing /workflow run prefix if present
        cleaned = command_str.replace("/workflow run", "").strip()
        
        # Regex for key=value pairs
        # Matches: key=value where value can be anything until next space
        pattern = re.compile(r'([\w\.]+)=([^\s]+)')
        matches = pattern.findall(cleaned)
        
        for k, v in matches:
            args[k] = v
            
        return args
