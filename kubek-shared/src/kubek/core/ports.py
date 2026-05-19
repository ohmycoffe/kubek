import hashlib
import socket

MIN_DYNAMIC_PORT = 49152
MAX_DYNAMIC_PORT = 65535


def get_deterministic_port(
    service: str,
    namespace: str,
    service_port: int,
):
    key = f"{namespace}/{service}:{service_port}"
    h = hashlib.sha256(key.encode()).hexdigest()
    value = int(h[:8], base=16)  # first 32 bits = 8 hex chars * 4 bits/char
    return MIN_DYNAMIC_PORT + (value % (MAX_DYNAMIC_PORT - MIN_DYNAMIC_PORT + 1))


def is_port_free(port: int) -> bool:
    """Check if a local port is free by trying to bind to it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("", port))
            return True
        except OSError:
            return False


def find_free_port() -> int:
    """Find a free local port by binding to port 0,
    which tells the OS to select an available port.
    """
    # TOCTOU: the port is freed before kubectl binds it, so another process
    # could claim it in the window. Unavoidable without passing a pre-bound
    # socket, which kubectl does not support.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]
