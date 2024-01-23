"""."""
import logging
from pathlib import Path

from rich.logging import RichHandler

LOGGING_FILE = Path("/tmp/logging.txt")


class LogFileFormatter(logging.Formatter):
    """."""
    def __init__(self) -> None:
        """."""
        super().__init__()

    def format(self, record):
        """."""
        format_ = f"{record.levelname:8s} {record.msg}"
        if record.levelno == logging.INFO:
            # INFO just get's the basics.
            return format_

        # However, non-INFO logging also get's method and linenumber.
        return format_ + f" ({record.funcName}:{record.lineno:d})"


def setup_logging(debug: bool = False) -> Path:
    """Configure logging using Rich for the terminal and our format for file."""
    logger = logging.getLogger()
    logger.handlers.clear()

    # Set our default logging level (note: If we ever want to know if we're running "in" Render,
    # use we can check os.getenv("RENDER") == "true")
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Setup terminal-based logging using Rich's handler..
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_time=False)],
    )

    # Setup file handler...
    file_handler = logging.FileHandler(LOGGING_FILE, mode="w")
    file_handler.setFormatter(LogFileFormatter())
    logger.addHandler(file_handler)

    # Quiet down some quite noisy underlying libraries...
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return LOGGING_FILE
