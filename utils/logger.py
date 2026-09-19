import logging
import os


def setup_logger(log_file_path: str) -> logging.Logger:
    logger = logging.getLogger("quipu_logger")
    logger.setLevel(logging.INFO)

    log_directory = os.path.dirname(log_file_path)
    if log_directory:
        os.makedirs(log_directory, exist_ok=True)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(
            log_file_path,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger