import sys
import structlog
from config import LOGS_DIR


def get_logger(name: str = "swarm"):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(0),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
    )
    return structlog.get_logger(name)
