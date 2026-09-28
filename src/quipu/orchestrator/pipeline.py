# src/quipu/orchestrator/pipeline.py

import asyncio
import logging
from typing import Any, Dict, List, Protocol

from quipu.config.schemas import QuipuMasterPayload
from quipu.dispatchers.drive_publisher import GoogleDrivePublisher
from quipu.dispatchers.nestjs_client import NestJSClient


logger = logging.getLogger("quipu.orchestrator")


class QuipuPluginProtocol(Protocol):
    """Contrato que todo micro-plugin debe cumplir para ser orquestado."""

    source_key: str
    endpoint_path: str

    async def execute(self, id_expediente: str) -> Any:
        """Ejecuta la extracción del plugin para un expediente."""
        ...


class QuipuPipelineOrchestrator:
    """Coordina la ejecución paralela de micro-plugins y el dispatch final."""

    def __init__(
        self,
        plugins: List[QuipuPluginProtocol],
        drive_publisher: GoogleDrivePublisher,
        nestjs_client: NestJSClient,
    ) -> None:
        self.plugins = plugins
        self.drive_publisher = drive_publisher
        self.nestjs_client = nestjs_client

    async def run_pipeline(
        self,
        id_expediente: str,
        pdf_bytes: bytes,
    ) -> bool:
        """
        Ejecuta el ciclo completo del pipeline:

        1. Ejecuta los micro-plugins en paralelo.
        2. Publica el legajo PDF en Google Drive.
        3. Construye y valida el MasterPayload interno.
        4. Transmite individualmente los DTOs válidos a NestJS.

        Retorna True únicamente cuando todas las etapas obligatorias
        finalizan correctamente.
        """

        # 1. Ejecución paralela de todos los micro-plugins registrados.
        logger.info(
            "Iniciando extracción paralela para ID: %s",
            id_expediente,
        )

        tasks = [
            plugin.execute(id_expediente)
            for plugin in self.plugins
        ]

        resultados = await asyncio.gather(
            *tasks,
            return_exceptions=True,
        )

        extraction_successful = True

        for plugin, resultado in zip(self.plugins, resultados):
            if isinstance(resultado, Exception):
                extraction_successful = False

                logger.error(
                    "Fallo en plugin %s para ID %s: %s",
                    getattr(plugin, "source_key", "unknown"),
                    id_expediente,
                    resultado,
                    exc_info=resultado,
                )

        if not extraction_successful:
            logger.error(
                "La extracción no finalizó correctamente para ID: %s",
                id_expediente,
            )

        # 2. Publicación del documento en Google Drive.
        logger.info(
            "Cargando documento a Drive para ID: %s",
            id_expediente,
        )

        file_name = f"expediente_{id_expediente}.pdf"

        try:
            legajo_url = self.drive_publisher.upload_legajo(
                file_source=pdf_bytes,
                file_name=file_name,
            )
        except Exception as exc:
            logger.error(
                "Excepción durante la carga a Drive para ID %s: %s",
                id_expediente,
                exc,
                exc_info=True,
            )
            return False

        if not legajo_url:
            logger.error(
                "Carga a Drive fallida. "
                "Abortando pipeline para ID: %s",
                id_expediente,
            )
            return False

        # 3. Consolidación y validación del MasterPayload interno.
        merged_data: Dict[str, Any] = {}

        for resultado in resultados:
            if isinstance(resultado, Exception):
                continue

            if not hasattr(resultado, "model_dump"):
                logger.error(
                    "El resultado de un plugin no implementa "
                    "model_dump(). Tipo recibido: %s",
                    type(resultado).__name__,
                )
                extraction_successful = False
                continue

            plugin_data = resultado.model_dump()

            if not isinstance(plugin_data, dict):
                logger.error(
                    "model_dump() devolvió un valor que no es dict. "
                    "Tipo recibido: %s",
                    type(plugin_data).__name__,
                )
                extraction_successful = False
                continue

            merged_data.update(plugin_data)

        try:
            QuipuMasterPayload(
                id_expediente_global=id_expediente,
                drive_legajo_url=legajo_url,
                **merged_data,
            )
        except Exception as exc:
            logger.error(
                "Error de validación al ensamblar "
                "MasterPayload interno para ID %s: %s",
                id_expediente,
                exc,
                exc_info=True,
            )
            return False

        if not extraction_successful:
            logger.error(
                "MasterPayload validado, pero existen fallos de extracción. "
                "No se realizará dispatch HTTP para ID: %s",
                id_expediente,
            )
            return False

        # 4. Transmisión HTTP a NestJS usando los DTOs limpios
        #    de cada plugin.
        all_dispatches_successful = True

        for plugin, resultado in zip(self.plugins, resultados):
            if isinstance(resultado, Exception):
                logger.error(
                    "Fallo previo en plugin %s. "
                    "Omitiendo transmisión.",
                    getattr(plugin, "source_key", "unknown"),
                )
                all_dispatches_successful = False
                continue

            target_endpoint = getattr(
                plugin,
                "endpoint_path",
                None,
            )

            if not target_endpoint:
                logger.warning(
                    "El plugin %s no define un endpoint_path. "
                    "Omitiendo transmisión.",
                    getattr(plugin, "source_key", "unknown"),
                )
                all_dispatches_successful = False
                continue

            if not hasattr(resultado, "model_dump"):
                logger.error(
                    "El resultado del plugin %s no implementa "
                    "model_dump(). Omitiendo transmisión.",
                    getattr(plugin, "source_key", "unknown"),
                )
                all_dispatches_successful = False
                continue

            payload_dict = resultado.model_dump(
                mode="json",
                by_alias=True,
            )

            if not isinstance(payload_dict, dict):
                logger.error(
                    "El DTO del plugin %s no produjo un diccionario "
                    "válido para NestJS.",
                    getattr(plugin, "source_key", "unknown"),
                )
                all_dispatches_successful = False
                continue

            # Inyección de la URL de Drive donde NestJS la espera.
            if "remate" in payload_dict:
                remate_payload = payload_dict["remate"]

                if isinstance(remate_payload, dict):
                    remate_payload["archivoUrl"] = legajo_url
                else:
                    logger.error(
                        "El campo 'remate' del plugin %s no es un "
                        "diccionario. Tipo recibido: %s",
                        getattr(plugin, "source_key", "unknown"),
                        type(remate_payload).__name__,
                    )
                    all_dispatches_successful = False
                    continue

            logger.info(
                "Transmitiendo DTO limpio a %s (Plugin: %s)",
                target_endpoint,
                getattr(plugin, "source_key", "unknown"),
            )

            try:
                success = await self.nestjs_client.send_payload(
                    payload_data=payload_dict,
                    endpoint_path=target_endpoint,
                )
            except Exception as exc:
                logger.error(
                    "Excepción durante transmisión del plugin %s "
                    "al endpoint %s: %s",
                    getattr(plugin, "source_key", "unknown"),
                    target_endpoint,
                    exc,
                    exc_info=True,
                )
                all_dispatches_successful = False
                continue

            if not success:
                logger.error(
                    "NestJS rechazó la transmisión del plugin %s "
                    "al endpoint %s.",
                    getattr(plugin, "source_key", "unknown"),
                    target_endpoint,
                )
                all_dispatches_successful = False

        if all_dispatches_successful:
            logger.info(
                "Pipeline finalizado correctamente para ID: %s",
                id_expediente,
            )
        else:
            logger.error(
                "Pipeline finalizado con errores de dispatch "
                "para ID: %s",
                id_expediente,
            )

        return all_dispatches_successful