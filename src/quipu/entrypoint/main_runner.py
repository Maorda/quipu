# quipu/entrypoint/main_runner.py

import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from quipu.config.settings import QuipuSettings
# Ajusta la ruta de importación según la estructura de tu proyecto
from quipu.main import procesar_expediente_completo 

# Mover la carga del entorno fuera de la función asíncrona para evitar I/O redundante
load_dotenv(dotenv_path=".env", override=True)

logger = logging.getLogger("quipu_logger")

def _update_status_error(global_id: str, error_message: str):
    """Actualiza el archivo de estado físico a 'error' para detener el polling del frontend."""
    # Debe coincidir con la lógica de rutas de api_server.py
    data_dir = Path(os.environ.get("DATA_DIR", "./data"))
    status_file = data_dir / "04_output" / f"status_{global_id}.json"
    
    if status_file.exists():
        try:
            with open(status_file, "r+", encoding="utf-8") as f:
                data = json.load(f)
                data["status"] = "error"
                data["fase_actual"] = f"Error crítico: {error_message}"
                data["archivo_actual"] = "Ejecución detenida"
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
        except Exception as e:
            logger.error("No se pudo actualizar el archivo de estado a error para %s: %s", global_id, e)

async def run_pipeline_entrypoint(global_id: str, sources_paths: dict) -> bool:
    """Entrypoint CLI asíncrono dinámico que despierta al orquestador."""
    try:
        if not sources_paths:
            error_msg = "No se proporcionaron fuentes (sources_paths)."
            logger.error("❌ %s Expediente: %s", error_msg, global_id)
            _update_status_error(global_id, error_msg)
            return False

        # Extraer el PDF principal dinámicamente en lugar de usar un mock
        pdf_bytes = b""
        # Toma la fuente prioritaria (ej. remaju) o la primera disponible en el diccionario
        primary_source_path = sources_paths.get("remaju") or next(iter(sources_paths.values()), None)
        
        if primary_source_path and os.path.exists(primary_source_path):
            with open(primary_source_path, "rb") as f:
                pdf_bytes = f.read()
        else:
            logger.warning("⚠️ No se pudo leer un archivo PDF principal válido desde la ruta: %s", primary_source_path)

        settings = QuipuSettings()
        
        # Despacho directo al controlador dinámico
        success = await procesar_expediente_completo(
            global_id=global_id,
            pdf_bytes=pdf_bytes,
            sources_paths=sources_paths,
            settings=settings
        )
        
        if not success:
            _update_status_error(global_id, "Fallo interno reportado por procesar_expediente_completo.")
            
        return success

    except Exception as exc:
        error_msg = str(exc)
        logger.error("❌ Error crítico en el runner de entrada para %s: %s", global_id, error_msg)
        _update_status_error(global_id, error_msg)
        return False