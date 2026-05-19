import logging

import kubek.term.format as fmt
from kubek.term import get_console

from export_dotenv.cli import app

logging.basicConfig()

console = get_console()


def deprecated_entry() -> None:
    console.print(
        fmt.warn("'envx' has been deprecated, use instead"),
        fmt.highlight("kubectl export-dotenv"),
    )
    app()


if __name__ == "__main__":
    app()
