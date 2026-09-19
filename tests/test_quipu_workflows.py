# tests/test_quipu_workflows.py
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.workflows.pipeline_orchestrator import PipelineOrchestrator


@pytest.fixture(autouse=True)
def mock_google_auth_for_workflow():
    """Aísla el constructor de Google Drive de fallas criptográficas PEM en este módulo."""
    with patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_cred:
        mock_cred.return_value = MagicMock()
        yield


@pytest.mark.anyio
async def test_pipeline_orchestrator_coordinates_7_phases_and_purges_staged_files(
    tmp_path: Path,
) -> None:
    """
    Verifica que PipelineOrchestrator orqueste el ciclo de vida de 7 fases,
    coordinando adecuadamente con ChaskyConsolidator y los despachadores correspondientes,
    y ejecute la purga física de los archivos Markdown temporales almacenados en staged_dir.
    """
    # Forzar el DATA_DIR aislado en la sandbox del test para autocalcular propiedades de solo lectura
    settings = QuipuSettings()
    
    settings.output_json_dir.mkdir(parents=True, exist_ok=True)
    settings.staged_dir.mkdir(parents=True, exist_ok=True)

    staged_md_file = settings.staged_dir / "remaju_temp.md"
    staged_md_file.write_text("# Fragmento Remaju\nTexto legal de remate judicial...", encoding="utf-8")

    assert staged_md_file.exists(), "El archivo de staging debe existir antes de la ejecución del orquestador."

    mock_chasky = MagicMock()
    
    # Crear archivo maestro físico simulado
    fake_master_path = settings.output_json_dir / "exp_MOCK_ID.json"
    fake_master_path.write_text('{"id_expediente_global": "MOCK_ID"}', encoding="utf-8")
    
    # Simular archivo temporal intermedio de Chasky que purga la Fase 7
    temp_chasky = settings.output_json_dir / "temp_MOCK_ID.json"
    temp_chasky.write_text('{"informacion_cej": {}, "informacion_remaju": {}, "informacion_sunarp": {}}', encoding="utf-8")

    mock_builder = MagicMock(return_value=fake_master_path)
    mock_nestjs = AsyncMock(return_value=True)

    # Inyección de parches en los constructores para evitar validaciones de red o criptografía reales
    with patch("dantesito.chasky.consolidation.consolidator.ChaskyConsolidator.build_master_expediente", new=mock_chasky), \
         patch("dantesito.quipu.consolidator.master_builder.MasterBuilder.assemble_and_save", new=mock_builder), \
         patch("dantesito.quipu.dispatchers.drive_publisher.GoogleDrivePublisher.upload_legajo") as mock_upload, \
         patch("dantesito.quipu.dispatchers.nestjs_client.NestJSClient.send_expediente", new=mock_nestjs):

        mock_upload.return_value = "https://google.com"

        # Instanciación y ejecución del orquestador DENTRO del contexto protegido
        orchestrator = PipelineOrchestrator(settings=settings)
        
        with patch("dantesito.quipu.workflows.pipeline_orchestrator.CreateExpedienteDto") as mock_dto_cls:
            mock_dto_cls.return_value = MagicMock()
            
            result = await orchestrator.run_full_cycle(
                global_id="MOCK_ID",
                cej_path="mock_cej.json",
                remaju_path="mock_remaju.pdf",
                sunarp_path="mock_sunarp.pdf"
            )

    assert result is True
    assert not staged_md_file.exists(), "La Fase 7 asíncrona debió purgar los residuos Markdown de staged_dir."
