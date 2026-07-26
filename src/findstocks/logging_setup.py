"""Configuración de logging para la app."""

import logging
from typing import Optional


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    nivel = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=nivel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )
