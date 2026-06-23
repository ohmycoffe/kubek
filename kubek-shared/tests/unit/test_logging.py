import logging
import sys

from kubek.term._logging import set_logger_levels_from_verbosity_count, suppress_logging


def test_setup_logging_from_count_configures_root_logger():
    set_logger_levels_from_verbosity_count(2)

    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_from_count_configures_named_loggers():
    set_logger_levels_from_verbosity_count(1, "kubek", "portfwd")

    assert logging.getLogger("kubek").level == logging.INFO
    assert logging.getLogger("portfwd").level == logging.INFO


def test_suppress_console_logging_hides_stderr(capsys):
    logger = logging.getLogger("foo")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(stream=sys.stderr))
    logger.propagate = False
    # ensure root has a stderr handler
    logger.debug("visible - before")
    assert "visible - before" in capsys.readouterr().err

    with suppress_logging(logger):
        logger.critical("hidden")
    assert capsys.readouterr().err == ""

    logger.debug("visible - after")
    assert "visible - after" in capsys.readouterr().err
