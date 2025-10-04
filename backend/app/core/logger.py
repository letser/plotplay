"""
Centralized logging configuration for PlotPlay.
"""
import logging
from pathlib import Path

def setup_session_logger(session_id: str) -> logging.Logger:
    """
    Creates and configures a logger for a specific game session.

    Args:
        session_id: The unique identifier for the game session.

    Returns:
        A configured logger instance that writes to a session-specific file.
    """
    # Create a logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Create a specific logger for this session
    logger = logging.getLogger(session_id)
    logger.setLevel(logging.DEBUG)  # Capture all levels of messages

    # Prevent logs from propagating to the root logger
    logger.propagate = False

    # Avoid adding handlers if they already exist (e.g., on engine reload)
    if not logger.handlers:
        # Create a file handler to write logs to a session-specific file
        file_handler = logging.FileHandler(logs_dir / f"session_{session_id}.log", mode='w')
        file_handler.setLevel(logging.DEBUG)

        # Create a formatter to define the log message structure
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Add the handler to the logger
        logger.addHandler(file_handler)

    return logger