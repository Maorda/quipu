# src/quipu/consolidator/master_builder.py

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from quipu.config.settings import QuipuSettings


class MasterBuilder:
    """Ensamblador agnóstico in-memory para el objeto de transferencia de datos maestro."""

    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

    def assemble_payload_dict(
        self,
        global_id: str,
        business_payload: Dict[str, Any],
        drive_legajo_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ensambla el payload final combinando metadatos de orquestación y datos de negocio.
        
        El plugin es responsable de estructurar, validar y proveer el `business_payload`.
        """
        return {
            "id_expediente_global": global_id,
            "drive_legajo_url": drive_legajo_url,
            "fecha_consolidacion": datetime.now(timezone.utc).isoformat(),
            "datos_negocio": business_payload,
        }

    def save_to_disk(
        self, payload_dict: Dict[str, Any], global_id: str
    ) -> Path:
        """Utilitario opcional de persistencia en disco solo para pruebas o depuración local."""
        output_dir = self.settings.get_temp_dir("04_output/json_maestro")
        output_file_path = output_dir / f"exp_{global_id}.json"

        with output_file_path.open("w", encoding="utf-8") as json_file:
            json.dump(
                payload_dict,
                json_file,
                ensure_ascii=False,
                indent=2,
            )

        return output_file_path