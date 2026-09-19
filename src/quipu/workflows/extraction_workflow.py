# src/quipu/workflows/extraction_workflow.py

import asyncio
import importlib
import inspect
import logging
from typing import Dict, Any, List, Optional

from quipu.config.settings import QuipuSettings
from quipu.dispatchers.drive_publisher import GoogleDrivePublisher
from quipu.dispatchers.nestjs_client import NestJSClient
from quipu.orchestrator.pipeline import QuipuPipelineOrchestrator, QuipuPluginProtocol

logger = logging.getLogger("quipu.workflows.extraction")


class ExtractionWorkflow:
    """
    Workflow encargado de la resolución dinámica de plugins según las fuentes 
    de entrada y de orquestar el ciclo completo de extracción, consolidación y envío.
    """

    def __init__(
        self,
        settings: QuipuSettings,
        drive_publisher: Optional[GoogleDrivePublisher] = None,
        nestjs_client: Optional[NestJSClient] = None,
    ) -> None:
        self.settings = settings
        self.drive_publisher = drive_publisher or GoogleDrivePublisher()
        self.nestjs_client = nestjs_client or NestJSClient(settings=settings)

    def _to_pascal_case(self, snake_str: str) -> str:
        """Convierte cadenas snake_case a PascalCase (ej: sunat_ruc -> SunatRuc)."""
        return "".join(word.capitalize() for word in snake_str.lower().split("_"))

    def cargar_plugins_dinamicos(
        self,
        sources_paths: Dict[str, str],
        chasky_data: Optional[Dict[str, Any]] = None,
    ) -> List[QuipuPluginProtocol]:
        """
        Carga e instancia dinámicamente los micro-plugins basándose en las llaves
        presentes en `sources_paths` (ej. 'remaju', 'sunat_ruc').
        """
        plugins_instanciados: List[QuipuPluginProtocol] = []

        for source_key, file_path in sources_paths.items():
            source_key_clean = source_key.lower().strip()
            module_name = f"quipu.plugins.{source_key_clean}.main"
            
            # Genera nombres robustos: sunat_ruc -> SunatRucPlugin
            class_prefix = self._to_pascal_case(source_key_clean)
            class_name = f"{class_prefix}Plugin"

            try:
                modulo = importlib.import_module(module_name)
                plugin_class = getattr(modulo, class_name)

                # Inspección estricta de la firma para evitar enmascarar errores internos con try/except
                constructor_signature = inspect.signature(plugin_class.__init__)
                
                if "chasky_data" in constructor_signature.parameters:
                    plugin_instance = plugin_class(file_path=file_path, chasky_data=chasky_data)
                else:
                    plugin_instance = plugin_class(file_path=file_path)

                plugins_instanciados.append(plugin_instance)
                logger.info("✅ Plugin '%s' cargado exitosamente desde %s.", class_name, module_name)

            except ModuleNotFoundError:
                logger.warning("⚠️ No se encontró el módulo para la fuente '%s' (%s).", source_key_clean, module_name)
            except AttributeError:
                logger.warning("⚠️ El módulo %s no define la clase '%s'.", module_name, class_name)
            except Exception as exc:
                logger.error("❌ Error al instanciar el plugin '%s': %s", class_name, exc)

        return plugins_instanciados

    async def execute(
        self,
        global_id: str,
        pdf_bytes: bytes,
        sources_paths: Dict[str, str],
        chasky_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Ejecuta la secuencia completa del workflow de extracción.
        """
        logger.info("🚀 Iniciando ExtractionWorkflow para el expediente: %s", global_id)

        # 1. Cargar plugins dinámicamente en un hilo separado para no bloquear el event loop asíncrono
        plugins = await asyncio.to_thread(
            self.cargar_plugins_dinamicos,
            sources_paths=sources_paths,
            chasky_data=chasky_data
        )

        if not plugins:
            logger.error("❌ No se pudo cargar ningún plugin válido para las fuentes: %s", list(sources_paths.keys()))
            return False

        # 2. Instanciar el orquestador con los plugins activos
        orchestrator = QuipuPipelineOrchestrator(
            plugins=plugins,
            drive_publisher=self.drive_publisher,
            nestjs_client=self.nestjs_client,
        )

        # 3. Ejecutar el pipeline de procesamiento y transmisión
        success = await orchestrator.run_pipeline(
            id_expediente=global_id,
            pdf_bytes=pdf_bytes,
        )

        if success:
            logger.info("🎉 Workflow de extracción finalizado con éxito para el expediente: %s", global_id)
        else:
            logger.error("❌ El workflow de extracción reportó fallos para el expediente: %s", global_id)

        return success