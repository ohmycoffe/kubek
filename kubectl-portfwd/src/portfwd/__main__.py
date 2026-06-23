# Intentionally configured basicConfig at the top of the entrypoint
# to capture logs emitted before setup_logging is called
import logging

logging.basicConfig()

from portfwd.presentation.cli import app

if __name__ == "__main__":
    app()
