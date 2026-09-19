# tests/test_quipu_drive_publisher.py

import os
from unittest.mock import MagicMock, patch
import pytest

from quipu.config.settings import QuipuSettings
from quipu.dispatchers.drive_publisher import GoogleDrivePublisher


@pytest.fixture
def mock_settings():
    """Simula el plugin inyectando su ID de carpeta de Google Drive maestro."""
    with patch.dict(
        os.environ,
        {
            "NESTJS_API_URL": "https://api.test.com",
            "GOOGLE_DRIVE_FOLDER_ID": "master_plugin_folder_id",
            "GEMINI_API_KEY": "mock_gemini_key",
        },
    ):
        return QuipuSettings()


@pytest.fixture
def mock_credentials():
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key": "mock_private_key",
        "client_email": "test@test.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


@patch("quipu.dispatchers.drive_publisher.build")
@patch("quipu.dispatchers.drive_publisher.service_account.Credentials.from_service_account_info")
def test_get_or_create_daily_folder_exists(mock_creds, mock_build, mock_settings, mock_credentials):
    """Valida que la librería detecte y reutilice la carpeta de la fecha si ya existe."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_files = mock_service.files.return_value
    
    # Mockear list().execute() para simular que Drive encontró la subcarpeta "19/08/2026"
    mock_files.list.return_value.execute.return_value = {
        "files": [{"id": "daily_folder_123", "name": "19/08/2026"}]
    }

    publisher = GoogleDrivePublisher(mock_settings, mock_credentials)
    folder_id = publisher._get_or_create_daily_folder("master_plugin_folder_id")

    # Debe retornar el ID existente y NO debe hacer llamadas para crear
    assert folder_id == "daily_folder_123"
    mock_files.create.assert_not_called()


@patch("quipu.dispatchers.drive_publisher.build")
@patch("quipu.dispatchers.drive_publisher.service_account.Credentials.from_service_account_info")
def test_get_or_create_daily_folder_creates_new(mock_creds, mock_build, mock_settings, mock_credentials):
    """Valida que la librería cree la carpeta dinámica si la lista de Drive retorna vacío."""
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_files = mock_service.files.return_value
    
    # Mockear list() devolviendo una lista vacía
    mock_files.list.return_value.execute.return_value = {"files": []}
    
    # Mockear create() simulando que Google Drive asigna un ID a la nueva carpeta
    mock_files.create.return_value.execute.return_value = {"id": "new_daily_folder_456"}

    publisher = GoogleDrivePublisher(mock_settings, mock_credentials)
    folder_id = publisher._get_or_create_daily_folder("master_plugin_folder_id")

    assert folder_id == "new_daily_folder_456"
    mock_files.create.assert_called_once()


@patch("quipu.dispatchers.drive_publisher.build")
@patch("quipu.dispatchers.drive_publisher.service_account.Credentials.from_service_account_info")
@patch("quipu.dispatchers.drive_publisher.datetime")
def test_upload_legajo_in_memory_to_daily_folder(mock_datetime, mock_creds, mock_build, mock_settings, mock_credentials):
    """Valida el flujo de inyección del archivo PDF en bytes a la subcarpeta asignada por quipu."""
    mock_datetime.now.return_value.strftime.return_value = "19/08/2026"
    
    mock_service = MagicMock()
    mock_build.return_value = mock_service
    mock_files = mock_service.files.return_value
    
    # Simula la existencia de la subcarpeta
    mock_files.list.return_value.execute.return_value = {"files": [{"id": "daily_folder_id"}]}
    # Simula la carga exitosa del archivo
    mock_files.create.return_value.execute.return_value = {"id": "uploaded_file_id_789"}

    publisher = GoogleDrivePublisher(mock_settings, mock_credentials)
    
    dummy_pdf_bytes = b"%PDF-1.4\n%..."
    file_name = "expediente_002_002_3036_PJ_CI.pdf"

    url_result = publisher.upload_legajo(dummy_pdf_bytes, file_name=file_name)

    # Validar que el archivo subido esté alojado en la subcarpeta hija, no en el master del plugin
    call_kwargs = mock_files.create.call_args[1]
    assert call_kwargs["body"]["parents"] == ["daily_folder_id"]
    assert call_kwargs["body"]["name"] == file_name
    
    # Validar el estricto cumplimiento de los corchetes
    assert url_result == "https://drive.google.com/file/d/uploaded_file_id_789/view"