import json
import os
from pathlib import Path
from typing import Dict, Any
from utils.logging import Logger

CHECKPOINTS_DIR = Path(__file__).resolve().parent.parent.parent / "checkpoints"

def clear_prev_checkpoints():
    """
    Elimina todos los archivos de checkpoints en el directorio de checkpoints.
    """

    if os.path.exists(CHECKPOINTS_DIR):
        for filename in os.listdir(CHECKPOINTS_DIR):
            file_path = os.path.join(CHECKPOINTS_DIR, filename)
            if os.path.isfile(file_path):
                os.unlink(file_path)

class Checkpoints:
    """
    Clase para gestionar el guardado y carga de estados de los agentes (Checkpoints).
    Sigue un patrón similar al Logger, instanciándose por agente.
    """
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        
        self.base_path = Path(CHECKPOINTS_DIR)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.file_path = self.base_path / f"{self.agent_id}.json"
        self.logger = Logger(self.__class__.__name__)

    def save(self, context: Dict[str, Any]):
        """
        Guarda el contexto del agente en un archivo JSON.
        """

        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=4, ensure_ascii=False)
            self.logger.info(f"Checkpoint guardado para {self.agent_id}")
        except Exception as e:
            self.logger.error(f"No se pudo guardar el checkpoint para {self.agent_id}: {e}")

    def load(self) -> Dict[str, Any]:
        """
        Carga el contexto del agente desde su archivo de checkpoint.
        Retorna un diccionario vacío si falla o no existe.
        """

        if not self.file_path.exists():
            self.logger.info(f"No se encontró el checkpoint para {self.agent_id}")
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
            self.logger.info(f"Checkpoint cargado para {self.agent_id}")
        except Exception as e:
            self.logger.error(f"No se pudo cargar el checkpoint para {self.agent_id}: {e}")
            return {}
