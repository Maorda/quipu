# src/quipu/config/schemas.py

from typing import Optional
from pydantic import BaseModel, Field

class QuipuPluginBaseDto(BaseModel):
    """Clase base estandarizada para garantizar inmutabilidad en los micro-plugins."""
    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
    }

class QuipuMasterPayload(BaseModel):
    """Schema consolidador que se envía a NestJS. 
    Absorbe dinámicamente los datos de los micro-plugins.
    """
    id_expediente_global: str = Field(
        ..., 
        description="Identificador universal de la transacción o expediente"
    )
    drive_legajo_url: Optional[str] = Field(
        default=None, 
        description="Enlace persistente del documento cargado en Drive"
    )

    # Configuración clave: permite que se inyecten atributos no definidos aquí 
    # (ej. informacion_sunarp, informacion_cej) durante el merge del orquestador.
    model_config = {
        "extra": "allow",
        "frozen": True
    }