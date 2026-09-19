# main.py

import asyncio
import logging
from typing import Optional, Dict, Any

from quipu.config.settings import QuipuSettings
from quipu.workflows.extraction_workflow import ExtractionWorkflow

# Configuración básica de logging para ejecuciones directas
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("quipu.main")


async def procesar_expediente_completo(
    global_id: str,
    pdf_bytes: bytes,
    sources_paths: Dict[str, str],
    chasky_data: Optional[Dict[str, Any]] = None,
    settings: Optional[QuipuSettings] = None,
) -> bool:
    """
    Punto de entrada principal para procesar un expediente completo.
    Delega toda la orquestación y resolución de plugins a ExtractionWorkflow.
    """
    logger.info("=== Iniciando procesamiento de expediente: %s ===", global_id)

    try:
        # Cargar configuración activa
        active_settings = settings or QuipuSettings()

        # Delegar el trabajo al workflow de extracción
        workflow = ExtractionWorkflow(settings=active_settings)
        resultado = await workflow.execute(
            global_id=global_id,
            pdf_bytes=pdf_bytes,
            sources_paths=sources_paths,
            chasky_data=chasky_data,
        )

        return resultado

    except Exception as exc:
        logger.critical("💥 Error no controlado al procesar expediente %s: %s", global_id, exc, exc_info=True)
        return False


if __name__ == "__main__":
    # Prueba CLI de verificación rápida
    demo_id = "EXP-2026-001"
    demo_sources = {
        "remaju": "data/01_raw/remaju_EXP-2026-001.pdf",
        "sunarp": "data/01_raw/sunarp_EXP-2026-001.pdf",
    }
    demo_pdf = b"%PDF-1.4 Mock Content"

    exito = asyncio.run(
        procesar_expediente_completo(
            global_id=demo_id,
            pdf_bytes=demo_pdf,
            sources_paths=demo_sources,
        )
    )
    print(f"\nResultado de la ejecución CLI: {'ÉXITO' if exito else 'FALLO'}")