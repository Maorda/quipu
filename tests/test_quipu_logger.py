import logging
from pathlib import Path

from dantesito.quipu.utils.logger import setup_logger


def _cleanup_logger(logger: logging.Logger) -> None:
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_setup_logger_creates_physical_log_file(tmp_path: Path) -> None:
    log_file_path = tmp_path / "quipu_audit.log"
    logger = setup_logger(str(log_file_path))

    try:
        logger.info("Test de auditoría Chasky-Quipu")

        for handler in logger.handlers:
            handler.flush()

        assert log_file_path.exists()
        assert log_file_path.is_file()

        log_content = log_file_path.read_text(encoding="utf-8")
        assert "Test de auditoría Chasky-Quipu" in log_content
    finally:
        _cleanup_logger(logger)


def test_setup_logger_records_error_levels(tmp_path: Path) -> None:
    log_file_path = tmp_path / "quipu_audit.log"
    logger = setup_logger(str(log_file_path))

    try:
        logger.error("Error simulado de conexión NestJS")

        for handler in logger.handlers:
            handler.flush()

        assert log_file_path.exists()
        assert log_file_path.is_file()

        log_lines = log_file_path.read_text(encoding="utf-8").splitlines()

        assert any(
            "ERROR" in line and "Error simulado de conexión NestJS" in line
            for line in log_lines
        )
    finally:
        _cleanup_logger(logger)