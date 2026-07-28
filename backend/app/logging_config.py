import logging
import logging.handlers
from .config import LOG_DIR

def setup_logger():
    """Configure structured, rotating file logging."""
    logger = logging.getLogger("med_annotator")
    
    # Avoid duplicate handlers if setup multiple times
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )

    # File Handler - Rotating Logs (5MB max, 5 backups)
    log_file = LOG_DIR / "backend.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    
    # Console Handler for dev
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logger()
