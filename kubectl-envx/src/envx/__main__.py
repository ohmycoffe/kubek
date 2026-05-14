import logging

from kubek.ui import COLOR_WARNING, console

from envx.cli.main import app

logging.basicConfig()


def deprecated_entry() -> None:
    console.print(
        f"[bold {COLOR_WARNING}]Warning:[/] 'envx' has been deprecated, use 'kenvx' instead."
    )
    app()


if __name__ == "__main__":
    app()
