import time
from utils.json_schema import validate_message
from utils.logging import log_event


class CommandParser:
    """
    Parses chat commands from Minecraft and converts them 
    into standardized JSON messages to send through the MessageBus.

    Supported commands (as per TAP assignment):
        /agent pause|resume|stop|status
        /explorer start x=<int> z=<int> [range=<int>]
        /miner start [x=<int> y=<int> z=<int>]
        /miner set strategy <vertical|grid|vein>
        /builder build
        /builder bom
        /workflow run ...
    """

    def __init__(self, message_bus):
        self.bus = message_bus

    # ---------------------------------------------------------
    # PUBLIC API
    # ---------------------------------------------------------
    async def handle_chat(self, text: str):
        """
        Main entry point. Takes a chat command string, parses it,
        and sends the resulting message to the appropriate agent.
        """

        if not text.startswith("/"):
            return  # Not a command

        parts = text[1:].split()  # remove leading "/" and split
        main = parts[0].lower()

        if main == "explorer":
            await self._parse_explorer(parts[1:])
        elif main == "miner":
            await self._parse_miner(parts[1:])
        elif main == "builder":
            await self._parse_builder(parts[1:])
        elif main == "workflow":
            await self._parse_workflow(parts[1:])
        elif main == "agent":
            await self._parse_agent(parts[1:])
        else:
            await log_event({
                "event": "unknown_command",
                "command": text,
            })

    # ---------------------------------------------------------
    # EXPLORER COMMANDS
    # ---------------------------------------------------------
    async def _parse_explorer(self, parts):
        """
        Explorer-related commands:
            /explorer start x=10 z=20 range=50
        """

        if parts[0] == "start":
            params = self._parse_key_value_pairs(parts[1:])

            msg = {
                "type": "command.explorer.start.v1",
                "source": "USER",
                "target": "ExplorerBot",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "payload": params,
                "status": "PROCESSING"
            }

            validate_message(msg)
            await self.bus.send("USER", "ExplorerBot", msg)

    # ---------------------------------------------------------
    # MINER COMMANDS
    # ---------------------------------------------------------
    async def _parse_miner(self, parts):
        """
        Miner-related commands:
            /miner start
            /miner set strategy grid
        """

        if parts[0] == "start":
            params = self._parse_key_value_pairs(parts[1:])

            msg = {
                "type": "command.miner.start.v1",
                "source": "USER",
                "target": "MinerBot",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "payload": params,
                "status": "PROCESSING"
            }

            validate_message(msg)
            await self.bus.send("USER", "MinerBot", msg)

        elif parts[0] == "set" and parts[1] == "strategy":
            strategy = parts[2]

            msg = {
                "type": "command.miner.set_strategy.v1",
                "source": "USER",
                "target": "MinerBot",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "payload": {"strategy": strategy},
                "status": "PROCESSING"
            }

            validate_message(msg)
            await self.bus.send("USER", "MinerBot", msg)

    # ---------------------------------------------------------
    # BUILDER COMMANDS
    # ---------------------------------------------------------
    async def _parse_builder(self, parts):
        """
        Builder commands:
            /builder build
            /builder bom
        """

        if parts[0] == "build":
            msg = {
                "type": "command.builder.build.v1",
                "source": "USER",
                "target": "BuilderBot",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "payload": {},
                "status": "PROCESSING"
            }

            validate_message(msg)
            await self.bus.send("USER", "BuilderBot", msg)

        elif parts[0] == "bom":
            msg = {
                "type": "command.builder.bom.v1",
                "source": "USER",
                "target": "BuilderBot",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "payload": {},
                "status": "PROCESSING"
            }

            validate_message(msg)
            await self.bus.send("USER", "BuilderBot", msg)

    # ---------------------------------------------------------
    # WORKFLOW COMMANDS
    # ---------------------------------------------------------
    async def _parse_workflow(self, parts):
        params = self._parse_key_value_pairs(parts)

        msg = {
            "type": "command.workflow.run.v1",
            "source": "USER",
            "target": "ALL",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": params,
            "status": "PROCESSING"
        }

        validate_message(msg)
        await self.bus.broadcast("USER", msg)

    # ---------------------------------------------------------
    # GENERIC AGENT COMMANDS
    # ---------------------------------------------------------
    async def _parse_agent(self, parts):
        """
        Command examples:
            /agent pause
            /agent resume
            /agent stop
        """

        cmd = parts[0]

        msg = {
            "type": f"command.agent.{cmd}.v1",
            "source": "USER",
            "target": "ALL",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "payload": {},
            "status": "PROCESSING"
        }

        validate_message(msg)
        await self.bus.broadcast("USER", msg)

    # ---------------------------------------------------------
    # PARSE KEY=VALUE PARAMETERS
    # ---------------------------------------------------------
    def _parse_key_value_pairs(self, pairs):
        """
        Converts tokens like ["x=10", "z=20", "range=50"]
        into {"x": 10, "z": 20, "range": 50}
        """

        result = {}

        for p in pairs:
            if "=" not in p:
                continue

            key, value = p.split("=")

            # try to convert to int
            try:
                value = int(value)
            except:
                pass

            result[key] = value

        return result
