from __future__ import annotations

import logging

from kubek.term import set_logger_levels_from_verbosity_count


def setup_logging(verbose: int) -> None:
    """Configure stderr logging for the pre-live CLI phase."""
    logging.basicConfig(force=True)
    set_logger_levels_from_verbosity_count(verbose, "kubek", "portfwd")
