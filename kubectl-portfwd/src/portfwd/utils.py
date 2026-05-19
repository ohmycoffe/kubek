def get_port_forward_status_id(
    namespace: str, service_name: str, remote_port: int
) -> str:
    """Stable id for a port-forward row in the live status table."""
    return f"{namespace}/{service_name}:{remote_port}"
