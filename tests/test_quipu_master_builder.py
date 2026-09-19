# tests/test_quipu_master_builder.py

import json
import os
from unittest.mock import patch
import pytest

from quipu.config.settings import QuipuSettings
from quipu.consolidator.master_builder import MasterBuilder


@pytest.fixture
def settings(tmp_path):
    """Fixture que simula las variables de entorno y activa el almacenamiento local."""
    with patch.dict(
        os.environ,
        {
            "NESTJS_API_URL": "https://api.test.com",
            "GOOGLE_DRIVE_FOLDER_ID": "mock_folder_id",
            "GEMINI_API_KEY": "mock_gemini_key",
            "ENABLE_LOCAL_STORAGE": "true",
        },
    ):
        # tmp_path es provisto automáticamente por pytest para crear carpetas temporales seguras
        return QuipuSettings(data_dir=str(tmp_path))


def test_assemble_payload_dict_agnostic(settings):
    """Valida el ensamblaje en memoria con un payload de negocio inyectado externamente."""
    builder = MasterBuilder(settings=settings)
    
    # Este diccionario simula lo que un plugin inyectaría
    mock_business_payload = {
        "origen": "poder_judicial",
        "informacion_cej": {"juzgado": "Lima", "estado": "Tramite"},
    }

    result = builder.assemble_payload_dict(
        global_id="EXP-TEST-001",
        business_payload=mock_business_payload,
        drive_legajo_url="[https://drive.google.com/file/d/123/view]",
    )

    # Validar metadatos orquestados por quipu
    assert result["id_expediente_global"] == "EXP-TEST-001"
    assert result["drive_legajo_url"] == "[https://drive.google.com/file/d/123/view]"
    assert "fecha_consolidacion" in result

    # Validar que el payload de negocio se encapsuló sin modificaciones
    assert result["datos_negocio"] == mock_business_payload
    assert result["datos_negocio"]["origen"] == "poder_judicial"


def test_save_to_disk_creates_file(settings):
    """Valida la creación física del JSON cuando ENABLE_LOCAL_STORAGE está activo."""
    builder = MasterBuilder(settings=settings)
    
    dummy_payload = {"id_expediente_global": "EXP-TEST-002", "estado": "ok"}
    global_id = "EXP-TEST-002"

    output_path = builder.save_to_disk(dummy_payload, global_id)

    # Verificar existencia en disco
    assert output_path.exists()
    assert output_path.name == "exp_EXP-TEST-002.json"

    # Verificar integridad del contenido escrito
    with output_path.open("r", encoding="utf-8") as f:
        saved_data = json.load(f)

    assert saved_data == dummy_payload