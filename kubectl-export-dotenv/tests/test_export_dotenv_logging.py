import logging

from export_dotenv.logging_setup import setup_logging
from rich.console import Console
from rich.logging import RichHandler


def test_setup_logging():
    root = logging.getLogger()
    root.handlers.clear()
    logging.basicConfig()

    setup_logging(Console(stderr=True, force_terminal=False), verbose=0)

    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler, RichHandler)
    assert handler.formatter is not None
    assert handler.formatter._fmt == "%(message)s"
    assert handler.console.file is not None
