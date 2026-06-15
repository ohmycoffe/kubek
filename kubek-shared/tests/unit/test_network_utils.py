import socket

from kubek.net.port import (
    find_free_port,
    get_deterministic_port,
    is_port_free,
)


def test_get_deterministic_port_is_stable():
    port1 = get_deterministic_port("my-service", "default", 8080)
    port2 = get_deterministic_port("my-service", "default", 8080)
    assert port1 == port2


def test_get_deterministic_port_differs_by_service():
    port1 = get_deterministic_port("service-a", "default", 8080)
    port2 = get_deterministic_port("service-b", "default", 8080)
    assert port1 != port2


def test_get_deterministic_port_differs_by_namespace():
    port1 = get_deterministic_port("my-service", "ns-a", 8080)
    port2 = get_deterministic_port("my-service", "ns-b", 8080)
    assert port1 != port2


def test_get_deterministic_port_differs_by_service_port():
    port1 = get_deterministic_port("my-service", "default", 80)
    port2 = get_deterministic_port("my-service", "default", 443)
    assert port1 != port2


def test_is_port_free_returns_false_when_port_is_bound():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
        assert is_port_free(port) is False


def test_is_port_free_returns_true_when_port_is_released():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        port = s.getsockname()[1]
    # socket is closed — port should be free now
    assert is_port_free(port) is True


def test_find_free_port_returns_a_bindable_port():
    port = find_free_port()

    assert port > 0
    assert is_port_free(port) is True
