# src/quipu/config/settings.py

import os
from pathlib import Path
from typing import Optional


class QuipuSettings:
    """Configuración base de orquestación para quipu.

    Diseñada para ser agnóstica o extendida por plugins específicos de dominio.
    """

    def __init__(
        self,
        nestjs_api_url: Optional[str] = None,
        google_drive_folder_id: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        data_dir: Optional[str] = None,
    ) -> None:
        # Permite inyección directa (ideal para plugins) o fallback a variables de entorno
        try:
            self._nestjs_api_url = (
                nestjs_api_url or os.environ["NESTJS_API_URL"]
            ).strip()
            self._google_drive_folder_id = (
                google_drive_folder_id or os.environ["GOOGLE_DRIVE_FOLDER_ID"]
            ).strip()
            self._gemini_api_key = (
                gemini_api_key or os.environ["GEMINI_API_KEY"]
            ).strip()
        except KeyError as exc:
            raise ValueError(
                f"La variable de entorno o parámetro {exc} es obligatorio."
            ) from exc

        # Flag de desarrollo para pruebas físicas en disco
        self._enable_local_storage = (
            os.getenv("ENABLE_LOCAL_STORAGE", "false").lower() == "true"
        )
        self._data_dir = Path(
            data_dir or os.getenv("QUIPU_DATA_DIR", "./temp_data")
        ).resolve()

    @property
    def NESTJS_API_URL(self) -> str:
        return self._nestjs_api_url

    @property
    def GOOGLE_DRIVE_FOLDER_ID(self) -> str:
        return self._google_drive_folder_id

    @property
    def GEMINI_API_KEY(self) -> str:
        return self._gemini_api_key

    @property
    def ENABLE_LOCAL_STORAGE(self) -> bool:
        return self._enable_local_storage

    def get_temp_dir(self, category: str = "temp") -> Path:
        """Retorna una ruta temporal.

        Solo crea la carpeta física si ENABLE_LOCAL_STORAGE está activo.
        """
        target_path = self._data_dir / category
        if self._enable_local_storage:
            target_path.mkdir(parents=True, exist_ok=True)
        return target_path