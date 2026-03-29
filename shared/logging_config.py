"""
Shared logging configuration for all pipeline tools.

Usage:
    from shared.logging_config import get_logger
    log = get_logger(__name__)
    log.info("starting validation")
"""
import logging
from pathlib import Path


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger that writes to console (INFO) and file (DEBUG).

    Log files are written to ~/.pipeline_tools/logs/<name>.log.
    Calling get_logger with the same name multiple times is safe — handlers
    are only added once.

    Args:
        name: Logger name, typically __name__ of the calling module.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    log_dir = Path.home() / ".pipeline_tools" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace("/", ".").replace("\\", ".")
    fh = logging.FileHandler(log_dir / f"{safe_name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
