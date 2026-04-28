import logging
import os
from typing import Optional

import uvicorn
from rich.logging import RichHandler
from rich.traceback import install as install_traceback

from judger import LOGGER_NAME
from judger.api import app


def setup_logger(
    log_file: Optional[str] = None,
    debug: bool = True
) -> None:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    console_handler = RichHandler(
        log_time_format="[%X.%f]",
        rich_tracebacks=True)
    logger.addHandler(console_handler)

    if log_file is not None:
        log_format = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)


def main():
    install_traceback()

    sandbox_endpoint: str = os.getenv(
        'PTOJ_SANDBOX_ENDPOINT',
        'http://localhost:5050'
    )
    host: str = os.getenv(
        'PTOJ_HOST',
        '0.0.0.0'
    )
    port: int = int(os.getenv(
        'PTOJ_PORT',
        '8000'
    ))
    log_file: Optional[str] = os.getenv(
        'PTOJ_LOG_FILE',
        'judger.log'
    )
    debug: bool = os.getenv('PTOJ_DEBUG', '1') == '1'

    setup_logger(log_file, debug)

    logger = logging.getLogger(f"{LOGGER_NAME}.main")
    logger.info(
        "Starting HTTP server with "
        f"sandbox_endpoint={sandbox_endpoint}, "
        f"host={host}, "
        f"port={port}, "
        f"log_file='{log_file}'"
    )

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_config=None  # Use our custom logger
    )


if __name__ == '__main__':
    main()
