# src/quipu/dispatchers/drive_publisher.py

import logging
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Union

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from quipu.config.settings import QuipuSettings

logger = logging.getLogger("quipu")


class GoogleDrivePublisher:
    """Despachador oficial para la carga de legajos en formato PDF hacia Google Drive.

    Soporta operaciones In-Memory (BytesIO), archivos locales y creación dinámica
    de subcarpetas agrupadas por fecha de ejecución.
    """

    def __init__(
        self,
        settings: QuipuSettings,
        credentials_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.settings = settings

        # 1. Resolver credenciales desde argumento explícito o variables de entorno
        if not credentials_info:
            client_email = os.environ.get("GOOGLE_CLIENT_EMAIL", "").strip()
            private_key = os.environ.get("GOOGLE_PRIVATE_KEY", "").strip()
            project_id = os.environ.get("GOOGLE_PROJECT_ID", "").strip()
            token_uri = os.environ.get(
                "GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"
            ).strip()

            if "\\n" in private_key:
                private_key = private_key.replace("\\n", "\n")

            if not client_email or not private_key:
                raise ValueError(
                    "GOOGLE_CLIENT_EMAIL o GOOGLE_PRIVATE_KEY no están configuradas."
                )

            credentials_info = {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": token_uri,
            }

        # 2. Inicializar credenciales oficiales de Google Cloud
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/drive"],
        )

        # 3. Construir el servicio
        self.service = build("drive", "v3", credentials=credentials)

    def _get_or_create_daily_folder(self, parent_id: str) -> Optional[str]:
        """Busca una subcarpeta con la fecha actual (ej. 19/08/2026) o la crea si no existe."""
        # Genera el string de la fecha en el formato solicitado
        folder_name = datetime.now().strftime("%d/%m/%Y")
        
        try:
            # Buscar si la carpeta ya existe dentro del ID inyectado por el plugin
            query = (
                f"mimeType='application/vnd.google-apps.folder' and "
                f"name='{folder_name}' and "
                f"'{parent_id}' in parents and "
                f"trashed=false"
            )
            
            response = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)"
            ).execute()
            
            files = response.get("files", [])
            
            if files:
                logger.debug("Subcarpeta diaria '%s' encontrada.", folder_name)
                return files[0].get("id")
            
            # Si no existe, crearla usando el parent proporcionado por el plugin
            logger.info("Creando subcarpeta diaria '%s' en Drive...", folder_name)
            folder_metadata = {
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id]
            }
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields="id"
            ).execute()
            
            return folder.get("id")
            
        except Exception as exc:
            logger.error("Error al obtener o crear la subcarpeta en Drive: %s", exc)
            return None

    def upload_legajo(
        self,
        file_source: Union[str, Path, bytes, BytesIO],
        file_name: str = "legajo.pdf",
    ) -> Optional[str]:
        """Sube un archivo a Google Drive dentro de la subcarpeta del día.

        Retorna la URL formateada adecuadamente entre corchetes [...] o None si falla.
        """
        try:
            # Obtener el ID de la carpeta principal asignada por el plugin
            main_folder_id = self.settings.GOOGLE_DRIVE_FOLDER_ID
            
            # Obtener o crear la subcarpeta dinámica para los archivos de hoy
            daily_folder_id = self._get_or_create_daily_folder(main_folder_id)
            if not daily_folder_id:
                logger.error("No se pudo resolver la carpeta de destino para la subida.")
                return None

            file_metadata = {
                "name": file_name,
                "parents": [daily_folder_id],
            }

            # Procesamiento de fuente In-Memory First
            if isinstance(file_source, (bytes, BytesIO)):
                stream = (
                    file_source
                    if isinstance(file_source, BytesIO)
                    else BytesIO(file_source)
                )
                media = MediaIoBaseUpload(
                    stream,
                    mimetype="application/pdf",
                    resumable=True,
                )
            else:
                path_obj = Path(file_source)
                if not path_obj.exists():
                    logger.error(
                        "El archivo local no existe en la ruta: %s", path_obj
                    )
                    return None

                file_metadata["name"] = path_obj.name
                media = MediaFileUpload(
                    str(path_obj),
                    mimetype="application/pdf",
                    resumable=True,
                )

            file_response = (
                self.service.files()
                .create(
                    body=file_metadata,
                    media_body=media,
                    fields="id",
                )
                .execute()
            )

            file_id = file_response.get("id")
            if not file_id:
                logger.error("No se pudo recuperar el ID del archivo en Google Drive.")
                return None

            logger.info(
                "Legajo subido con éxito. Destino ID: %s | File ID: %s", 
                daily_folder_id, file_id
            )

            # Estricto cumplimiento de sintaxis con la URL entre corchetes
            return f"https://drive.google.com/file/d/{file_id}/view"

        except Exception:
            logger.exception("Error durante la subida del legajo PDF a Google Drive.")
            return None