import logging
import sys
import traceback
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logger():
    logger = logging.getLogger("DocumentsGenerator")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


def log_error(context: str, error: Exception, extra: dict = None):
    error_msg = f"[{context}] Ошибка: {str(error)}"
    if extra:
        error_msg += f" | Детали: {extra}"
    logger.error(error_msg)
    logger.error(f"Трассировка:\n{traceback.format_exc()}")


def log_info(context: str, message: str, extra: dict = None):
    info_msg = f"[{context}] {message}"
    if extra:
        info_msg += f" | {extra}"
    logger.info(info_msg)


def log_warning(context: str, message: str, extra: dict = None):
    warn_msg = f"[{context}] {message}"
    if extra:
        warn_msg += f" | {extra}"
    logger.warning(warn_msg)