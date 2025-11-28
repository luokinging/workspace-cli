import logging
import sys
from pathlib import Path

# Default log file in the current directory or a specific location?
# User said: "在 workroot directory中定义log文件path（可选）"
# We can default to workspace-cli.log in CWD or handle it in config.

logger = logging.getLogger("workspace-cli")

def setup_logging(debug: bool = False, log_file: Path = None):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    
    # Reset handlers
    logger.handlers = []
    logger.setLevel(level)
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG) # Always log debug to file?
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

def get_logger():
    return logger
