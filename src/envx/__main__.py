import logging
import os

from envx.cli.main import app

logging.basicConfig(level=os.getenv("LOGGING_LEVEL", "INFO").upper())

if __name__ == "__main__":
    app()
