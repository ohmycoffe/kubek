from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def call_subprocess(cmd: list[str]) -> str:
    """Execute a subprocess command and return stdout.

    Args:
        cmd: Command as list of strings.

    Returns:
        Command stdout as string.

    Raises:
        CalledProcessError: If command returns non-zero exit code.
    """
    logger.debug(" ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def get_current_namespace() -> str | None:
    """Get the active namespace from kubeconfig, or None if not set."""
    result = call_subprocess(
        ["kubectl", "config", "view", "--minify", "-o", "jsonpath={..namespace}"]
    )
    return result.strip() or None
