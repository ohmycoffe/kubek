# Intentionally configured basicConfig at the top of the entrypoint
# to capture logs emitted before setup_logging is called
import logging

logging.basicConfig()

from kubek.term import create_output

from export_dotenv.cli import app

out = create_output()


def deprecated_entry() -> None:
    out.caution(
        "envx is deprecated, use kubectl export-dotenv instead.",
        ["kubectl export-dotenv", "envx"],
    )
    app()


if __name__ == "__main__":
    app()
