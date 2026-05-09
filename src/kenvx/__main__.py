import logging

from kenvx.cli.main import app
from kenvx.console import console
from kenvx.style import COLOR_WARNING

logging.basicConfig()


def deprecated_entry() -> None:
    console.print(
        f"[bold {COLOR_WARNING}]Warning:[/] 'envx' has been deprecated, use 'kenvx' instead."
    )
    app()


if __name__ == "__main__":
    app()
