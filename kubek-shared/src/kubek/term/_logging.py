from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from kubek.term.verbosity import Verbosity, VerbosityLevel

_LOG_LEVEL_BY_VERBOSITY: dict[VerbosityLevel, int] = {
    VerbosityLevel.NORMAL: logging.WARNING,
    VerbosityLevel.VERBOSE: logging.INFO,
    VerbosityLevel.DIAGNOSTIC: logging.DEBUG,
}


def set_logger_levels_from_verbosity_count(
    verbosity_count: int,
    *logger_names: str,
) -> None:
    """Set logging thresholds for named loggers from a -v / -vv count.

    0  -> WARNING and above
    1  -> INFO and above
    2+ -> DEBUG and above

    If no logger names are provided, configures the root logger.
    """
    verbosity = Verbosity.from_count(verbosity_count)
    level = _LOG_LEVEL_BY_VERBOSITY[verbosity.level]

    if not logger_names:
        logger_names = ("",)  # root logger

    for name in logger_names:
        logging.getLogger(name).setLevel(level)


@contextmanager
def suppress_logging(logger: logging.Logger | None = None) -> Iterator[None]:
    """Temporarily suppress console log output.

    Removes console stream handlers from `logger` (the root logger by default)
    for the duration of the block, so log lines don't corrupt console output
    such as a live-rendered display. File handlers are left in place, so file
    logging keeps working. The stdlib "last resort" handler (which writes to
    stderr when a logger has no handlers) is also silenced.

    Console handlers are identified by type: a ``StreamHandler`` that is not a
    ``FileHandler`` (``FileHandler`` is a subclass of ``StreamHandler``). This
    avoids comparing against ``sys.stdout``/``sys.stderr`` identity, which
    breaks when those streams are swapped (e.g. under pytest's ``capsys``).
    """
    logger = logger if logger is not None else logging.getLogger()
    removed_handlers = [
        handler
        for handler in logger.handlers
        if isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
    ]
    for handler in removed_handlers:
        logger.removeHandler(handler)

    previous_last_resort = logging.lastResort
    logging.lastResort = logging.NullHandler()

    try:
        yield
    finally:
        logging.lastResort = previous_last_resort
        for handler in removed_handlers:
            logger.addHandler(handler)
