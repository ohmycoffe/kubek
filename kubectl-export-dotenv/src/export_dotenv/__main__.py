import logging

from kubek.term import create_output

from export_dotenv.cli import app

logging.basicConfig()

out = create_output()


def deprecated_entry() -> None:
    out.caution(
        "envx is deprecated, use kubectl export-dotenv instead.",
        ["kubectl export-dotenv", "envx"],
    )
    app()


if __name__ == "__main__":
    app()
