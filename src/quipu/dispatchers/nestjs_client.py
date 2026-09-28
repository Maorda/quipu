# src/quipu/dispatchers/nestjs_client.py

import asyncio
import logging
from typing import Any, Dict, Final, Union

import httpx
from pydantic import BaseModel

from quipu.config.settings import QuipuSettings

logger = logging.getLogger("quipu")
_MAX_ATTEMPTS: Final[int] = 3


class NestJSClient:
    """Cliente HTTP asíncrono y agnóstico para la sincronización con backends."""

    def __init__(self, settings: QuipuSettings) -> None:
        self.settings = settings

    async def send_payload(
        self,
        payload_data: Union[BaseModel, Dict[str, Any]],
        endpoint_path: str,
    ) -> bool:
        """Envía datos mediante POST asíncrono a un endpoint inyectado por el plugin."""
        base_url = self.settings.NESTJS_API_URL.rstrip("/")
        clean_path = endpoint_path.lstrip("/")
        endpoint = f"{base_url}/{clean_path}" if clean_path else base_url

        # 🎯 FIX CRÍTICO: Se añade by_alias=True para preservar los nombres camelCase hacia NestJS
        if isinstance(payload_data, BaseModel):
            payload = payload_data.model_dump(mode="json", by_alias=True)
        else:
            payload = payload_data

        exp_id = payload.get("remate", {}).get("expediente", "UNKNOWN")

        async with httpx.AsyncClient(timeout=30.0) as client:
            for intento in range(_MAX_ATTEMPTS):
                try:
                    response = await client.post(
                        endpoint,
                        json=payload,
                    )

                    if response.status_code in (200, 201):
                        logger.info(
                            "Datos del ID %s transmitidos correctamente a %s.",
                            exp_id,
                            endpoint,
                        )
                        return True

                    if 500 <= response.status_code <= 599:
                        raise httpx.HTTPStatusError(
                            f"El servidor respondió con error HTTP {response.status_code}.",
                            request=response.request,
                            response=response,
                        )

                    logger.error(
                        "Error no recuperable (HTTP %s) al transmitir el ID %s. Respuesta: %s",
                        response.status_code,
                        exp_id,
                        response.text,
                    )
                    return False

                except (
                    httpx.ConnectError,
                    httpx.TimeoutException,
                    httpx.HTTPStatusError,
                ) as exc:
                    if intento == _MAX_ATTEMPTS - 1:
                        logger.critical(
                            "Transmisión del ID %s agotada tras %d intentos: %s",
                            exp_id,
                            _MAX_ATTEMPTS,
                            exc,
                        )
                        return False

                    backoff = 2 ** intento
                    logger.warning(
                        "Intento %d/%d fallido para ID %s: %s. Reintentando en %d segs.",
                        intento + 1,
                        _MAX_ATTEMPTS,
                        exp_id,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)

        return False