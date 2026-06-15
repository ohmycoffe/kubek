import logging

from kubek.term._logging import setup_logging_from_count


def test_setup_logging_from_count_configures_root_logger():
    setup_logging_from_count(2)

    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_from_count_configures_named_loggers():
    setup_logging_from_count(1, "kubek", "portfwd")

    assert logging.getLogger("kubek").level == logging.INFO
    assert logging.getLogger("portfwd").level == logging.INFO
