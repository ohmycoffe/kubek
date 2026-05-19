import logging
from typing import TYPE_CHECKING

from rich.console import Console

from kubek.term.style import RICH_THEME

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)

__stderr_console = Console(stderr=True, theme=RICH_THEME)
__stdout_console = Console(stderr=False, theme=RICH_THEME)


def get_console(stderr: bool = True) -> Console:
    return __stderr_console if stderr else __stdout_console
