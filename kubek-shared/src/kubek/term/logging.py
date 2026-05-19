import logging


def setup_logging(verbose: int, *logger_names: str) -> None:
    """Set log levels for named loggers from a -v / -vv count."""
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    level = levels[min(verbose, len(levels) - 1)]
    for name in logger_names:
        logging.getLogger(name).setLevel(level)
