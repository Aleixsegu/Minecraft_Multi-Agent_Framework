import json
import os
from pathlib import Path
from typing import Dict, Any

CHECKPOINTS_DIR = Path(__file__).resolve().parent.parent.parent / "checkpoints"

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

    def save(self, context: Dict[str, Any]):
        """
        Guarda el contexto del agente en un archivo JSON.
        """

        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[CHECKPOINT ERROR] No se pudo guardar el checkpoint para {self.agent_id}: {e}")

    def load(self) -> Dict[str, Any]:
        """
        Carga el contexto del agente desde su archivo de checkpoint.
        Retorna un diccionario vacío si falla o no existe.
        """

        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[CHECKPOINT ERROR] No se pudo cargar el checkpoint para {self.agent_id}: {e}")
            return {}
