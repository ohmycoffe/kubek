from __future__ import annotations

import logging

from kubek.term.verbosity import Verbosity, VerbosityLevel

_LOG_LEVEL_BY_VERBOSITY: dict[VerbosityLevel, int] = {
    VerbosityLevel.NORMAL: logging.WARNING,
    VerbosityLevel.VERBOSE: logging.INFO,
    VerbosityLevel.DIAGNOSTIC: logging.DEBUG,
}


def setup_logging_from_count(
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
