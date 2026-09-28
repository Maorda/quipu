# src/quipu/workflows/extraction_workflow.py

import logging
from importlib.metadata import entry_points
from typing import Any, Dict, List, Optional

from quipu.config.settings import QuipuSettings
from quipu.dispatchers.drive_publisher import GoogleDrivePublisher
from quipu.dispatchers.nestjs_client import NestJSClient
from quipu.orchestrator.pipeline import (
    QuipuPipelineOrchestrator,
    QuipuPluginProtocol,
)

logger = logging.getLogger("quipu.workflows.extraction")


class ExtractionWorkflow:
    def __init__(
        self,
        settings: QuipuSettings,
        drive_publisher: Optional[GoogleDrivePublisher] = None,
        nestjs_client: Optional[NestJSClient] = None,
    ) -> None:
        self.settings = settings

        self.drive_publisher = (
            drive_publisher
            if drive_publisher is not None
            else GoogleDrivePublisher(settings=settings)
        )

        self.nestjs_client = (
            nestjs_client
            if nestjs_client is not None
            else NestJSClient(settings=settings)
        )

    def cargar_plugins_dinamicos(
        self,
        sources_paths: Dict[str, str],
        raw_data: Dict[str, Any],
    ) -> List[QuipuPluginProtocol]:
        plugins_instanciados: List[QuipuPluginProtocol] = []

        # Descubrir los plugins externos registrados mediante Entry Points.
        discovered_eps = entry_points(group="quipu.plugins")

        # Mapear los Entry Points disponibles por nombre.
        plugin_map = {
            ep.name.lower().strip(): ep
            for ep in discovered_eps
        }

        for source_key in sources_paths:
            source_key_clean = source_key.lower().strip()

            plugin_ep = plugin_map.get(source_key_clean)

            if plugin_ep is None:
                logger.warning(
                    "No se encontró ningún Entry Point registrado para "
                    "el plugin fuente: '%s'.",
                    source_key_clean,
                )
                continue

            try:
                # Cargar la implementación registrada en el Entry Point.
                plugin_class = plugin_ep.load()

                # Instanciar el plugin utilizando el contrato actual.
                plugin_instance = plugin_class(raw_data=raw_data)

                plugins_instanciados.append(plugin_instance)

                logger.info(
                    "Plugin externo '%s' cargado exitosamente "
                    "mediante Entry Points.",
                    source_key_clean,
                )

            except Exception:
                logger.exception(
                    "Error al cargar o instanciar el plugin externo '%s'.",
                    source_key_clean,
                )

        return plugins_instanciados

    async def execute(
        self,
        global_id: str,
        pdf_bytes: bytes,
        sources_paths: Dict[str, str],
        raw_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        logger.info(
            "Iniciando ExtractionWorkflow para el expediente: %s",
            global_id,
        )

        # Garantizar que None se convierta en un diccionario válido,
        # preservando cualquier diccionario vacío recibido explícitamente.
        safe_raw_data = (
            raw_data
            if raw_data is not None
            else {}
        )

        plugins = self.cargar_plugins_dinamicos(
            sources_paths=sources_paths,
            raw_data=safe_raw_data,
        )

        if not plugins:
            logger.error(
                "No se pudo cargar ningún plugin válido para el expediente: %s.",
                global_id,
            )
            return False

        orchestrator = QuipuPipelineOrchestrator(
            plugins=plugins,
            drive_publisher=self.drive_publisher,
            nestjs_client=self.nestjs_client,
        )

        success = await orchestrator.run_pipeline(
            id_expediente=global_id,
            pdf_bytes=pdf_bytes,
        )

        return success