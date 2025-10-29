# utils/logger_config.py
import logging

logger = logging.getLogger("biochem_app")
if not logger.handlers:  # prevent duplicate handlers when reloaded
    handler = logging.StreamHandler()
    file_handler = logging.FileHandler("app.log")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
