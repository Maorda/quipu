import pytest
from pydantic import ValidationError

from dantesito.quipu.config.schemas import CreateExpedienteDto


def test_create_expediente_dto_valid_payload() -> None:
    payload = {
        "id_expediente_global": "EXP-2026-000123",
        "informacion_cej": {
            "expediente_numero": "00123-2026",
            "materia": "EJECUCION DE GARANTIA",
            "demandante": "Banco Ejemplo S.A.",
            "demandado": "Juan Perez",
        },
        "informacion_remaju": {
            "numero_convocatoria": 1,
            "porcentaje_a_rematar": 100,
            "fecha_remate": "2026-09-15",
            "estado": "PENDIENTE",
        },
        "informacion_sunarp": {
            "partida_registral": "12345678",
            "area_terreno": 120.5,
            "gravamenes": [],
        },
        "drive_legajo_url": "https://drive.google.com/file/d/ejemplo/view",
    }

    dto = CreateExpedienteDto(**payload)

    assert dto.id_expediente_global == payload["id_expediente_global"]
    assert dto.informacion_cej == payload["informacion_cej"]
    assert dto.informacion_remaju == payload["informacion_remaju"]
    assert dto.informacion_sunarp == payload["informacion_sunarp"]
    assert dto.drive_legajo_url == payload["drive_legajo_url"]


def test_create_expediente_dto_missing_required_fields() -> None:
    payload = {
        "informacion_cej": {
            "expediente_numero": "00123-2026",
            "materia": "EJECUCION DE GARANTIA",
        },
        "informacion_remaju": {
            "numero_convocatoria": 1,
            "porcentaje_a_rematar": 100,
        },
    }

    with pytest.raises(ValidationError):
        CreateExpedienteDto(**payload)


def test_create_expediente_dto_optional_drive_url() -> None:
    payload = {
        "id_expediente_global": "EXP-2026-000123",
        "informacion_cej": {
            "expediente_numero": "00123-2026",
            "materia": "EJECUCION DE GARANTIA",
        },
        "informacion_remaju": {
            "numero_convocatoria": 1,
            "porcentaje_a_rematar": 100,
        },
        "informacion_sunarp": {
            "partida_registral": "12345678",
            "area_terreno": 120.5,
        },
    }

    dto = CreateExpedienteDto(**payload)

    assert dto.drive_legajo_url is None