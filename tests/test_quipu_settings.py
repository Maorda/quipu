# tests/test_quipu_settings.py
import os
from unittest.mock import patch
from dantesito.quipu.config.settings import QuipuSettings


def test_quipu_settings_load_from_environment() -> None:
    """Verifica que QuipuSettings cargue dinámicamente las variables obligatorias del entorno."""
    environment = {
        "NESTJS_API_URL": "http://localhost:3000/api/v1",
        "GOOGLE_DRIVE_FOLDER_ID": "drive_mock_123",
        "GEMINI_API_KEY": "AIzaSy_test_key"
    }

    # clear=False permite que las propiedades hereden el DATA_DIR aislado del test activo
    with patch.dict(os.environ, environment, clear=False):
        settings = QuipuSettings()

    assert settings.NESTJS_API_URL == "http://localhost:3000/api/v1"
    assert settings.GOOGLE_DRIVE_FOLDER_ID == "drive_mock_123"


def test_quipu_settings_builds_absolute_io_paths() -> None:
    """Verifica la construcción de subdirectorios absolutos a partir del DATA_DIR activo."""
    environment = {
        "NESTJS_API_URL": "http://localhost:3000/api/v1",
        "GOOGLE_DRIVE_FOLDER_ID": "drive_mock_123",
        "GEMINI_API_KEY": "AIzaSy_test_key",
        "DATA_DIR": "./data"
    }

    with patch.dict(os.environ, environment, clear=False):
        settings = QuipuSettings()
        
    assert settings.output_json_dir is not None
    assert settings.staged_dir is not None


def test_quipu_settings_missing_critical_environment() -> None:
    """Verifica que la ausencia de parámetros críticos lance un ValueError."""
    with patch.dict(os.environ, {}, clear=True):
        import pytest
        with pytest.raises(ValueError):
            QuipuSettings()
