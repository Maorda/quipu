# tests/test_nestjs_client.py

import pytest
from unittest.mock import AsyncMock, patch
import httpx

from quipu.config.settings import QuipuSettings
from quipu.dispatchers.nestjs_client import NestJSClient
from quipu.config.schemas import CreateExpedienteDto


@pytest.fixture
def settings():
    """Fixture de configuración básica para las pruebas."""
    return QuipuSettings(
        nestjs_api_url="https://api.test.com",
        google_drive_folder_id="mock_folder_id",
        gemini_api_key="mock_gemini_key",
    )


@pytest.mark.anyio
async def test_nestjs_client_send_success(settings):
    """Valida la transmisión exitosa de un DTO con el endpoint parametrizado."""
    client = NestJSClient(settings=settings)

    dto = CreateExpedienteDto(
        id_expediente_global="EXP-2026-001",
        informacion_cej={"juzgado": "Lima", "especialista": "Pérez"}
    )

    # Mock de la respuesta HTTP 201 Created
    mock_response = AsyncMock()
    mock_response.status_code = 201

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Ejecutar el envío usando un path personalizado (agnóstico)
        result = await client.send_payload(dto, endpoint_path="/api/v2/tramites")

        assert result is True
        mock_post.assert_awaited_once()
        
        # Verificar que la URL se concatenó correctamente
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.test.com/api/v2/tramites"
        assert "json" in kwargs


@pytest.mark.anyio
async def test_nestjs_client_retry_and_fail(settings):
    """Valida que el cliente agote los reintentos (backoff) ante fallos de servidor (5xx)."""
    client = NestJSClient(settings=settings)

    payload_dict = {
        "id_expediente_global": "EXP-2026-002",
        "datos": "prueba"
    }

    # Mock simulando error constante 500 del servidor
    mock_response = AsyncMock()
    mock_response.status_code = 500
    mock_response.request = httpx.Request("POST", "https://api.test.com/api/v1/expedientes")

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep: # Evita esperar en los tests
        
        mock_post.return_value = mock_response

        result = await client.send_payload(payload_dict)

        assert result is False
        # Debe haber intentado 3 veces según _MAX_ATTEMPTS
        assert mock_post.await_count == 3