from __future__ import annotations

import logging

from kubek.term import set_logger_levels_from_verbosity_count
from rich.console import Console
from rich.logging import RichHandler


def setup_logging(console: Console, verbose: int) -> None:
    """Replace root handlers with a RichHandler on *console*."""
    # Rich expects the formatter to pass only the message; it renders level/time/path.
    # https://rich.readthedocs.io/en/latest/logging.html
    format = "%(message)s"

    logging.basicConfig(
        force=True,
        format=format,
        handlers=[
            RichHandler(
                console=console,
                show_time=True,
                show_path=True,
                markup=False,
            )
        ],
    )
    set_logger_levels_from_verbosity_count(verbose, "kubek", "export-dotenv")
