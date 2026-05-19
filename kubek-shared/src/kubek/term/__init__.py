from kubek.term.console import get_console
from kubek.term.errors import print_error
from kubek.term.format import (
    error,
    fatal,
    highlight,
    info,
    mute,
    ongoing_status,
    success,
    warn,
)
from kubek.term.logging import setup_logging
from kubek.term.style import STYLE_QUESTIONARY

__all__ = [
    "fatal",
    "error",
    "get_console",
    "highlight",
    "info",
    "mute",
    "ongoing_status",
    "print_error",
    "setup_logging",
    "success",
    "STYLE_QUESTIONARY",
    "warn",
]
