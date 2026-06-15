from types import SimpleNamespace
from typing import cast

from kubek.kube.dto import Service
from portfwd.application.ports import KubeGateway
from portfwd.application.queries import (
    fetch_services_for_namespaces,
)


def _service(name: str, namespace: str, ports: list[int]) -> Service:
    raw = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
    }
    return Service.model_validate(raw)


def _make_api(service) -> KubeGateway:
    return cast(KubeGateway, SimpleNamespace(service=service))


def test_fetch_services_for_namespaces_combines_services_from_each_namespace():
    """Services from all requested namespaces are returned, sorted and flattened."""
    svc_a = _service("alpha", "ns-1", [80])
    svc_b = _service("beta", "ns-2", [443])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc_a], "ns-2": [svc_b]}.get(namespace, [])

    api = _make_api(FakeServiceRepo())
    specs = fetch_services_for_namespaces(["ns-1", "ns-2"], api)

    keys = [(s.target.namespace, s.target.name, s.remote_port) for s in specs]
    assert ("ns-1", "alpha", 80) in keys
    assert ("ns-2", "beta", 443) in keys


def test_fetch_services_for_namespaces_returns_empty_for_empty_namespaces():
    """Returns an empty list when no namespaces are provided."""

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return []

    api = _make_api(FakeServiceRepo())
    assert fetch_services_for_namespaces([], api) == []


def test_fetch_services_for_namespaces_sorts_and_expands_multi_port_services():
    """Services and ports are sorted; each port becomes its own spec."""
    svc_z = _service("zebra", "ns-b", [443, 80])
    svc_a = _service("alpha", "ns-a", [8080])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-a": [svc_a], "ns-b": [svc_z]}.get(namespace, [])

    api = _make_api(FakeServiceRepo())
    specs = fetch_services_for_namespaces(["ns-b", "ns-a"], api)

    keys = [(s.target.namespace, s.target.name, s.remote_port) for s in specs]
    assert keys == [
        ("ns-a", "alpha", 8080),
        ("ns-b", "zebra", 80),
        ("ns-b", "zebra", 443),
    ]
