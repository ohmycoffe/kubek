import socket


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


def ensure_port(preferred: int | None) -> int:
    """Return the preferred port if it's free, otherwise find a free port."""
    if preferred and is_port_free(preferred):
        return preferred
    else:
        return find_free_port()


def parse_qualname(ref: str) -> tuple[str, str]:
    """Parse a qualified name in the form 'namespace/service'."""
    ns, name = ref.split("/", 1)
    if not ns or not name:
        raise ValueError(f"Invalid reference {ref!r} (expected 'namespace/service')")
    return ns, name
