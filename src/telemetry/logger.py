import logging
import json
import os
from datetime import datetime
from typing import Any, Dict

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        level_name = os.getenv("LOG_LEVEL", "INFO").upper()
        self.logger.setLevel(getattr(logging, level_name, logging.INFO))
        self.logger.propagate = False

        if self.logger.handlers:
            return
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File Handler (JSON)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(file_handler)
        
        # Console logging is optional because JSON logs make the chat UX noisy.
        if os.getenv("LOG_TO_CONSOLE", "false").lower() in {"1", "true", "yes", "on"}:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(console_handler)

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event with a timestamp and type."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data
        }
        self.logger.info(json.dumps(payload))

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

# Global logger instance
logger = IndustryLogger()
