import logging

from envx.cli.main import app
from envx.console import console
from envx.style import COLOR_WARNING

logging.basicConfig()


def deprecated_entry() -> None:
    console.print(
        f"[bold {COLOR_WARNING}]Warning:[/] 'envx' has been deprecated, use 'kenvx' instead."
    )
    app()


if __name__ == "__main__":
    app()
