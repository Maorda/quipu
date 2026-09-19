# tests/test_quipu_api_server.py
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from dantesito.quipu.entrypoint.api_server import app


@pytest.fixture
def mock_api_environment(monkeypatch, tmp_path):
    """Sandbox de rutas para el servidor FastAPI."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QUIPU_API_AUTH_TOKEN", "TokenSecretoTest123")
    return None


def test_api_server_rejects_unauthorized_requests(mock_api_environment) -> None:
    """Verifica que el servidor perimetral responda 401 ante credenciales inválidas."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/trigger-pipeline",
        json={"numero_expediente": "0200-jp-2051-IE"},
        headers={"X-Auth-Token": "ClaveIncorrecta"},
    )
    assert response.status_code == 401


@pytest.mark.anyio
async def test_api_server_accepts_authorized_trigger_and_executes_bat(mock_api_environment, tmp_path) -> None:
    """Verifica la delegación asíncrona no bloqueante hacia el runner usando rutas calculadas dinámicamente."""
    mock_runner = AsyncMock(return_value=True)

    with patch(
        "dantesito.quipu.entrypoint.api_server.run_pipeline_entrypoint",
        new=mock_runner,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            payload = {
                "numero_expediente": "0200-jp-2051-IE",
            }

            response = await client.post(
                "/api/v1/trigger-pipeline",
                json=payload,
                headers={"X-Auth-Token": "TokenSecretoTest123"},
            )

            assert response.status_code == 200
            json_data = response.json()
            assert json_data.get("success") is True

            # Las rutas esperadas se calculan dinámicamente sobre la carpeta temporal de Pytest (DATA_DIR)
            expected_remaju = str(tmp_path / "01_raw" / "remaju_0200-jp-2051-IE.pdf")
            expected_sunarp = str(tmp_path / "01_raw" / "sunarp_0200-jp-2051-IE.pdf")
            expected_cej = str(tmp_path / "01_raw" / "cej_0200-jp-2051-IE.json")

            mock_runner.assert_awaited_once_with(
                remaju_path=expected_remaju,
                sunarp_path=expected_sunarp,
                cej_path=expected_cej,
            )
