import json
import logging
import sys
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_keywords = ["token", "secret", "password", "key", "authorization", "credential"]

    def _filter_secrets(self, data):
        if isinstance(data, dict):
            cleaned = {}
            for k, v in data.items():
                if any(s in str(k).lower() for s in self.secret_keywords):
                    cleaned[k] = "***REDACTED***"
                else:
                    cleaned[k] = self._filter_secrets(v)
            return cleaned
        elif isinstance(data, list):
            return [self._filter_secrets(v) for v in data]
        return data

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Include extra attributes that might be passed via 'extra'
        reserved_keys = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename", 
            "funcName", "levelname", "levelno", "lineno", "module", "msecs", 
            "message", "msg", "name", "pathname", "process", "processName", 
            "relativeCreated", "stack_info", "thread", "threadName", "taskName"
        }
        for key, value in record.__dict__.items():
            if key not in reserved_keys:
                log_record[key] = value
        
        # Filter out any secrets
        log_record = self._filter_secrets(log_record)

        return json.dumps(log_record)

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # Let uvicorn use the same formatter for standard output
    uvicorn_logger = logging.getLogger("uvicorn")
    for handler in uvicorn_logger.handlers[:]:
        uvicorn_logger.removeHandler(handler)
    uvicorn_logger.addHandler(handler)
    
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    for handler in uvicorn_access_logger.handlers[:]:
        uvicorn_access_logger.removeHandler(handler)
    uvicorn_access_logger.addHandler(handler)
