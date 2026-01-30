import pytest
import os
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

# Asegurar que importamos del src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from utils.checkpoints import Checkpoints, clear_prev_checkpoints, CHECKPOINTS_DIR

@pytest.fixture
def clean_checkpoints_dir():
    """Fixture para asegurar un directorio de checkpoints limpio antes y después."""
    os.makedirs(CHECKPOINTS_DIR, exist_ok=True)
    yield
    # Cleanup opcional, aunque clear_prev_checkpoints se encarga de esto también
    for filename in os.listdir(CHECKPOINTS_DIR):
        file_path = os.path.join(CHECKPOINTS_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception:
            pass

class TestCheckpoints:
    
    def test_init_creates_dir(self):
        """Prueba que al instanciar se crea el directorio si no existe."""
        # Borramos temporalmente si existe
        if os.path.exists(CHECKPOINTS_DIR):
            try:
                # Intentamos borrar, si falla ignoramos (puede haber archivos en uso)
                shutil.rmtree(CHECKPOINTS_DIR)
            except:
                pass
                
        cp = Checkpoints("test_init_agent")
        assert os.path.exists(CHECKPOINTS_DIR)
        assert cp.file_path == CHECKPOINTS_DIR / "test_init_agent.json"

    def test_make_serializable(self):
        """Prueba la lógica de conversión recursiva a JSON-serializable."""
        cp = Checkpoints("serial_agent")
        
        complex_data = {
            "int": 1,
            "str": "val",
            # Tuple key -> string "x,y"
            (10, 20): "coord_val",
            # Set -> List
            "set_data": {1, 2, 3},
            # Tuple value -> List
            "tuple_val": (5, 6),
            "nested": [
                {(3, 4): "val2"}
            ]
        }
        
        serialized = cp._make_serializable(complex_data)
        
        assert serialized["int"] == 1
        assert serialized["10,20"] == "coord_val"
        assert isinstance(serialized["set_data"], list)
        assert 1 in serialized["set_data"]
        assert serialized["tuple_val"] == [5, 6]
        assert serialized["nested"][0]["3,4"] == "val2"

    def test_save_and_load(self, clean_checkpoints_dir):
        """Prueba el ciclo completo de guardado y carga."""
        cp = Checkpoints("saver_agent")
        data = {"state": "RUNNING", "inventory": ["dirt", "stone"]}
        
        # Guardar
        cp.save(data)
        assert os.path.exists(cp.file_path)
        
        # Cargar
        loaded = cp.load()
        assert loaded["state"] == "RUNNING"
        assert loaded["inventory"] == ["dirt", "stone"]

    def test_load_non_existent(self, clean_checkpoints_dir):
        """Prueba cargar un agente sin checkpoint previo."""
        cp = Checkpoints("ghost_agent")
        if os.path.exists(cp.file_path):
            os.remove(cp.file_path)
            
        loaded = cp.load()
        assert loaded == {}

    def test_load_corrupt_json(self, clean_checkpoints_dir):
        """Prueba robustez ante archivos JSON corruptos."""
        cp = Checkpoints("corrupt_agent")
        with open(cp.file_path, "w") as f:
            f.write("{ bad json structure ...")
            
        # No debe lanzar excepción, sino loguear y retornar {}
        loaded = cp.load()
        assert loaded == {}

    def test_clear_prev_checkpoints(self, clean_checkpoints_dir):
        """Prueba la función global de limpieza."""
        # Crear archivos dummy
        (CHECKPOINTS_DIR / "temp1.json").touch()
        (CHECKPOINTS_DIR / "temp2.txt").touch()
        
        assert len(os.listdir(CHECKPOINTS_DIR)) >= 2
        
        clear_prev_checkpoints()
        
        # Debería estar vacío
        assert len(os.listdir(CHECKPOINTS_DIR)) == 0

    def test_save_error_handling(self, clean_checkpoints_dir):
        """Prueba manejo de errores al guardar (ej: permisos)."""
        cp = Checkpoints("locked_agent")
        
        # Mock de open para que falle
        with patch("builtins.open", side_effect=PermissionError("Boom")):
            # No debe crashear
            cp.save({"data": 1})
            # Verificar log error (opcional si mockeamos logger)
