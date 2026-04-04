# src/utils/logger.py
import logging
import logging.handlers
from pathlib import Path
from src.utils.config import CONFIG


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with file + console handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Avoid duplicate handlers on re-import

    logger.setLevel(CONFIG["logging"]["level"])
    formatter = logging.Formatter(
        fmt=CONFIG["logging"]["format"],
        datefmt=CONFIG["logging"]["date_format"],
    )

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)

    # Rotating file handler
    log_path = Path(CONFIG["logging"]["file"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=CONFIG["logging"]["max_bytes"],
        backupCount=CONFIG["logging"]["backup_count"],
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    return logger