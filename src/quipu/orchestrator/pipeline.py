# src/quipu/orchestrator/pipeline.py

import asyncio
import logging
from typing import List, Protocol, Any, Dict

from quipu.config.schemas import QuipuMasterPayload
from quipu.dispatchers.drive_publisher import GoogleDrivePublisher
from quipu.dispatchers.nestjs_client import NestJSClient

logger = logging.getLogger("quipu.orchestrator")


class QuipuPluginProtocol(Protocol):
    """Contrato que todo micro-plugin debe cumplir para ser orquestado."""
    source_key: str
    endpoint_path: str
    
    async def execute(self, id_expediente: str) -> Any:
        ...


class QuipuPipelineOrchestrator:
    """Coordina la ejecución paralela de micro-plugins y el dispatch final de forma agnóstica."""

    def __init__(
        self,
        plugins: List[QuipuPluginProtocol],
        drive_publisher: GoogleDrivePublisher,
        nestjs_client: NestJSClient
    ) -> None:
        self.plugins = plugins
        self.drive_publisher = drive_publisher
        self.nestjs_client = nestjs_client

    async def run_pipeline(
        self,
        id_expediente: str,
        pdf_bytes: bytes
    ) -> bool:
        """
        Ejecuta el ciclo de vida completo: extracción, carga, consolidación y transmisión
        sin requerir parámetros de infraestructura en su firma.
        """
        # 1. Ejecución paralela de todos los micro-plugins registrados y validados
        logger.info("Iniciando extracción paralela para ID: %s", id_expediente)
        tasks = [plugin.execute(id_expediente) for plugin in self.plugins]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

        # 2. Merge de los DTOs resultantes
        merged_data: Dict[str, Any] = {}
        for idx, resultado in enumerate(resultados):
            if isinstance(resultado, Exception):
                logger.error("Fallo en plugin índice %d para ID %s: %s", idx, id_expediente, resultado)
                continue
            
            # Extrae la llave raíz (ej. {"informacion_remaju": {...}}) y la fusiona
            merged_data.update(resultado.model_dump())

        # 3. Publicación del documento en Google Drive (El folder ID se asume en variables de entorno internas)
        logger.info("Cargando documento a Drive para ID: %s", id_expediente)
        file_name = f"expediente_{id_expediente}.pdf"
        legajo_url = self.drive_publisher.upload_legajo(
            file_source=pdf_bytes,
            file_name=file_name
        )

        if not legajo_url:
            logger.error("Carga a Drive fallida. Abortando pipeline para ID: %s", id_expediente)
            return False

        # 4. Consolidación en el Master Payload
        try:
            master_payload = QuipuMasterPayload(
                id_expediente_global=id_expediente,
                drive_legajo_url=legajo_url,
                **merged_data
            )
        except ValueError as exc:
            logger.error("Error de validación al ensamblar MasterPayload: %s", exc)
            return False

        # 5. Transmisión HTTP a NestJS iterando sobre los endpoints de los plugins activos
        all_dispatches_successful = True
        for plugin in self.plugins:
            target_endpoint = getattr(plugin, "endpoint_path", None)
            if target_endpoint:
                logger.info("Transmitiendo MasterPayload a %s (Plugin: %s)", target_endpoint, plugin.source_key)
                success = await self.nestjs_client.send_payload(
                    payload_data=master_payload, 
                    endpoint_path=target_endpoint
                )
                if not success:
                    all_dispatches_successful = False
            else:
                logger.warning("El plugin %s no define un endpoint_path. Omitiendo transmisión.", plugin.source_key)

        return all_dispatches_successful