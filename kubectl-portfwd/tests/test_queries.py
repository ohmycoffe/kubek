from types import SimpleNamespace
from typing import cast

from kubek.kube.dto import Pod, Service
from portfwd.application.ports import KubeGateway
from portfwd.application.queries import (
    fetch_pods_for_namespaces,
    fetch_services_for_namespaces,
    fetch_targets_for_namespaces,
)
from portfwd.domain.models import TargetKind
from portfwd_test_utils.fakes import make_pod


def _service(name: str, namespace: str, ports: list[int]) -> Service:
    raw = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
    }
    return Service.model_validate(raw)


def _pod(name: str, namespace: str, container_ports: list[int]) -> Pod:
    """One single-container pod, expressed in terms of the shared `make_pod`."""
    return make_pod(name, namespace, [container_ports])


def _make_api(service=None, pod=None) -> KubeGateway:
    return cast(KubeGateway, SimpleNamespace(service=service, pod=pod))


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


def test_fetch_pods_for_namespaces_flattens_declared_container_ports():
    """Pods with declared container ports become one spec per unique port."""
    pod_a = _pod("worker", "ns-1", [9090])
    pod_b = _pod("api", "ns-2", [8080, 8443])
    pod_no_ports = _pod("sidecar", "ns-1", [])

    class FakePodRepo:
        def list(self, namespace: str) -> list[Pod]:
            return {
                "ns-1": [pod_a, pod_no_ports],
                "ns-2": [pod_b],
            }.get(namespace, [])

    api = _make_api(pod=FakePodRepo())
    specs = fetch_pods_for_namespaces(["ns-1", "ns-2"], api)

    keys = [
        (s.target.kind, s.target.namespace, s.target.name, s.remote_port) for s in specs
    ]
    assert keys == [
        (TargetKind.POD, "ns-1", "worker", 9090),
        (TargetKind.POD, "ns-2", "api", 8080),
        (TargetKind.POD, "ns-2", "api", 8443),
    ]


def test_fetch_targets_combines_services_and_pods():
    """The combined picker source returns services followed by pods."""
    svc = _service("alpha", "ns-1", [80])
    pod = _pod("worker", "ns-1", [9090])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakePodRepo:
        def list(self, namespace: str) -> list[Pod]:
            return {"ns-1": [pod]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), pod=FakePodRepo())
    specs = fetch_targets_for_namespaces(
        ["ns-1"], api, kinds=[TargetKind.SERVICE, TargetKind.POD]
    )

    kinds = {(s.target.kind, s.target.name) for s in specs}
    assert kinds == {
        (TargetKind.SERVICE, "alpha"),
        (TargetKind.POD, "worker"),
    }


def test_fetch_targets_honors_selected_kinds():
    """Only the requested kinds are fetched."""
    svc = _service("alpha", "ns-1", [80])
    pod = _pod("worker", "ns-1", [9090])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakePodRepo:
        def list(self, namespace: str) -> list[Pod]:
            return {"ns-1": [pod]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), pod=FakePodRepo())

    pods_only = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.POD])
    assert {(s.target.kind, s.target.name) for s in pods_only} == {
        (TargetKind.POD, "worker")
    }

    svcs_only = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.SERVICE])
    assert {(s.target.kind, s.target.name) for s in svcs_only} == {
        (TargetKind.SERVICE, "alpha")
    }
