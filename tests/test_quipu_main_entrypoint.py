# tests/test_quipu_main_entrypoint.py

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from dantesito.quipu.config.settings import QuipuSettings
from dantesito.quipu.entrypoint.main_runner import run_pipeline_entrypoint


@pytest.mark.anyio
async def test_entrypoint_extracts_global_id_from_strict_filename_and_triggers_pipeline(
    tmp_path: Path,
) -> None:
    remaju_path = "D:/descargas_externas/remaju_0200-jp-2051-IE.pdf"
    sunarp_path = "D:/descargas_externas/sunarp_0200-jp-2051-IE.pdf"
    cej_path = "cej.json"

    environment = {
        "NESTJS_API_URL": "http://localhost:3000",
        "GOOGLE_DRIVE_FOLDER_ID": "mock_google_drive_folder_id",
        "DATA_DIR": str(tmp_path),
    }

    mock_run_full_cycle = AsyncMock(return_value=True)

    with (
        patch.dict(os.environ, environment, clear=False),
        patch(
            "dantesito.quipu.entrypoint.main_runner.PipelineOrchestrator.__init__",
            return_value=None,
        ),
        patch(
            "dantesito.quipu.entrypoint.main_runner.PipelineOrchestrator.run_full_cycle",
            new=mock_run_full_cycle,
        ),
    ):
        result = await run_pipeline_entrypoint(
            remaju_path,
            sunarp_path,
            cej_path,
        )

    assert result is True

    mock_run_full_cycle.assert_awaited_once_with(
        global_id="0200-jp-2051-IE",
        cej_path=cej_path,
        remaju_path=remaju_path,
        sunarp_path=sunarp_path,
    )


@pytest.mark.anyio
async def test_entrypoint_rejects_mismatched_or_invalid_filenames(
    tmp_path: Path,
) -> None:
    invalid_remaju_path = "D:/descargas_externas/remaju_exp123.pdf"
    mismatched_sunarp_path = "D:/descargas_externas/sunarp_exp456.pdf"
    cej_path = "cej.json"

    environment = {
        "NESTJS_API_URL": "http://localhost:3000",
        "GOOGLE_DRIVE_FOLDER_ID": "mock_google_drive_folder_id",
        "DATA_DIR": str(tmp_path),
    }

    mock_run_full_cycle = AsyncMock(return_value=True)

    with (
        patch.dict(os.environ, environment, clear=False),
        patch(
            "dantesito.quipu.entrypoint.main_runner.PipelineOrchestrator.__init__",
            return_value=None,
        ),
        patch(
            "dantesito.quipu.entrypoint.main_runner.PipelineOrchestrator.run_full_cycle",
            new=mock_run_full_cycle,
        ),
    ):
        try:
            result = await run_pipeline_entrypoint(
                invalid_remaju_path,
                mismatched_sunarp_path,
                cej_path,
            )

            assert result is False
        except ValueError:
            pass

    mock_run_full_cycle.assert_not_awaited()