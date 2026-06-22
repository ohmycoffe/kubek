from types import SimpleNamespace
from typing import cast

from kubek.kube.dto import (
    DaemonSet,
    Deployment,
    Pod,
    ReplicaSet,
    Service,
    StatefulSet,
)
from portfwd.application.ports import KubeGateway
from portfwd.application.queries import (
    fetch_daemonsets_for_namespaces,
    fetch_deployments_for_namespaces,
    fetch_pods_for_namespaces,
    fetch_replicasets_for_namespaces,
    fetch_services_for_namespaces,
    fetch_statefulsets_for_namespaces,
    fetch_targets_for_namespaces,
)
from portfwd.domain.models import TargetKind
from portfwd_test_utils.fakes import (
    make_daemonset,
    make_deployment,
    make_pod,
    make_replicaset,
    make_statefulset,
)


def _service(name: str, namespace: str, ports: list[int]) -> Service:
    raw = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
    }
    return Service.model_validate(raw)


def _pod(name: str, namespace: str, container_ports: list[int]) -> Pod:
    """One single-container pod, expressed in terms of the shared `make_pod`."""
    return make_pod(name, namespace, [container_ports])


def _deployment(name: str, namespace: str, container_ports: list[int]) -> Deployment:
    """One single-container deployment expressed in terms of make_deployment."""
    return make_deployment(name, namespace, [container_ports])


def _statefulset(name: str, namespace: str, container_ports: list[int]) -> StatefulSet:
    """One single-container statefulset expressed in terms of make_statefulset."""
    return make_statefulset(name, namespace, [container_ports])


def _daemonset(name: str, namespace: str, container_ports: list[int]) -> DaemonSet:
    """One single-container daemonset expressed in terms of make_daemonset."""
    return make_daemonset(name, namespace, [container_ports])


def _replicaset(name: str, namespace: str, container_ports: list[int]) -> ReplicaSet:
    """One single-container replicaset expressed in terms of make_replicaset."""
    return make_replicaset(name, namespace, [container_ports])


def _make_api(
    service=None,
    pod=None,
    deployment=None,
    statefulset=None,
    daemonset=None,
    replicaset=None,
) -> KubeGateway:
    """Minimal fake KubeGateway with optional repo attributes."""
    return cast(
        KubeGateway,
        SimpleNamespace(
            service=service,
            pod=pod,
            deployment=deployment,
            statefulset=statefulset,
            daemonset=daemonset,
            replicaset=replicaset,
        ),
    )


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


def test_fetch_deployments_for_namespaces_flattens_declared_container_ports():
    """Deployments with declared container ports produce one spec per unique port; portless deployments are omitted."""
    dep_a = _deployment("worker", "ns-1", [9090])
    dep_b = _deployment("api", "ns-2", [8080, 8443])
    dep_no_ports = _deployment("sidecar", "ns-1", [])

    class FakeDeploymentRepo:
        def list(self, namespace: str) -> list[Deployment]:
            return {
                "ns-1": [dep_a, dep_no_ports],
                "ns-2": [dep_b],
            }.get(namespace, [])

    api = _make_api(deployment=FakeDeploymentRepo())
    specs = fetch_deployments_for_namespaces(["ns-1", "ns-2"], api)

    keys = [
        (s.target.kind, s.target.namespace, s.target.name, s.remote_port) for s in specs
    ]
    assert keys == [
        (TargetKind.DEPLOYMENT, "ns-1", "worker", 9090),
        (TargetKind.DEPLOYMENT, "ns-2", "api", 8080),
        (TargetKind.DEPLOYMENT, "ns-2", "api", 8443),
    ]


def test_fetch_targets_includes_deployments():
    """The combined picker returns services, pods, and deployments when all three are selected."""
    svc = _service("alpha", "ns-1", [80])
    pod = _pod("worker", "ns-1", [9090])
    dep = _deployment("api", "ns-1", [8080])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakePodRepo:
        def list(self, namespace: str) -> list[Pod]:
            return {"ns-1": [pod]}.get(namespace, [])

    class FakeDeploymentRepo:
        def list(self, namespace: str) -> list[Deployment]:
            return {"ns-1": [dep]}.get(namespace, [])

    api = _make_api(
        service=FakeServiceRepo(),
        pod=FakePodRepo(),
        deployment=FakeDeploymentRepo(),
    )
    specs = fetch_targets_for_namespaces(
        ["ns-1"], api, kinds=[TargetKind.SERVICE, TargetKind.POD, TargetKind.DEPLOYMENT]
    )

    kinds = {(s.target.kind, s.target.name) for s in specs}
    assert kinds == {
        (TargetKind.SERVICE, "alpha"),
        (TargetKind.POD, "worker"),
        (TargetKind.DEPLOYMENT, "api"),
    }


def test_fetch_targets_honors_deployment_kind_filter():
    """Only deployment specs are returned when kinds=[TargetKind.DEPLOYMENT]."""
    svc = _service("alpha", "ns-1", [80])
    dep = _deployment("api", "ns-1", [8080])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeDeploymentRepo:
        def list(self, namespace: str) -> list[Deployment]:
            return {"ns-1": [dep]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), deployment=FakeDeploymentRepo())
    specs = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.DEPLOYMENT])

    assert {(s.target.kind, s.target.name) for s in specs} == {
        (TargetKind.DEPLOYMENT, "api")
    }


def test_fetch_statefulsets_for_namespaces_flattens_declared_container_ports():
    """StatefulSets with declared container ports produce one spec per unique port; portless statefulsets are omitted."""
    sts_a = _statefulset("worker", "ns-1", [9090])
    sts_b = _statefulset("api", "ns-2", [8080, 8443])
    sts_no_ports = _statefulset("sidecar", "ns-1", [])

    class FakeStatefulSetRepo:
        def list(self, namespace: str) -> list[StatefulSet]:
            return {
                "ns-1": [sts_a, sts_no_ports],
                "ns-2": [sts_b],
            }.get(namespace, [])

    api = _make_api(statefulset=FakeStatefulSetRepo())
    specs = fetch_statefulsets_for_namespaces(["ns-1", "ns-2"], api)

    keys = [
        (s.target.kind, s.target.namespace, s.target.name, s.remote_port) for s in specs
    ]
    assert keys == [
        (TargetKind.STATEFULSET, "ns-1", "worker", 9090),
        (TargetKind.STATEFULSET, "ns-2", "api", 8080),
        (TargetKind.STATEFULSET, "ns-2", "api", 8443),
    ]


def test_fetch_targets_includes_statefulsets():
    """The combined picker returns statefulsets when that kind is selected."""
    svc = _service("alpha", "ns-1", [80])
    sts = _statefulset("cache", "ns-1", [6379])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeStatefulSetRepo:
        def list(self, namespace: str) -> list[StatefulSet]:
            return {"ns-1": [sts]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), statefulset=FakeStatefulSetRepo())
    specs = fetch_targets_for_namespaces(
        ["ns-1"], api, kinds=[TargetKind.SERVICE, TargetKind.STATEFULSET]
    )

    kinds = {(s.target.kind, s.target.name) for s in specs}
    assert kinds == {
        (TargetKind.SERVICE, "alpha"),
        (TargetKind.STATEFULSET, "cache"),
    }


def test_fetch_targets_honors_statefulset_kind_filter():
    """Only statefulset specs are returned when kinds=[TargetKind.STATEFULSET]."""
    svc = _service("alpha", "ns-1", [80])
    sts = _statefulset("cache", "ns-1", [6379])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeStatefulSetRepo:
        def list(self, namespace: str) -> list[StatefulSet]:
            return {"ns-1": [sts]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), statefulset=FakeStatefulSetRepo())
    specs = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.STATEFULSET])

    assert {(s.target.kind, s.target.name) for s in specs} == {
        (TargetKind.STATEFULSET, "cache")
    }


def test_fetch_daemonsets_for_namespaces_flattens_declared_container_ports():
    """DaemonSets with declared container ports produce one spec per unique port; portless daemonsets are omitted."""
    ds_a = _daemonset("worker", "ns-1", [9090])
    ds_b = _daemonset("api", "ns-2", [8080, 8443])
    ds_no_ports = _daemonset("sidecar", "ns-1", [])

    class FakeDaemonSetRepo:
        def list(self, namespace: str) -> list[DaemonSet]:
            return {
                "ns-1": [ds_a, ds_no_ports],
                "ns-2": [ds_b],
            }.get(namespace, [])

    api = _make_api(daemonset=FakeDaemonSetRepo())
    specs = fetch_daemonsets_for_namespaces(["ns-1", "ns-2"], api)

    keys = [
        (s.target.kind, s.target.namespace, s.target.name, s.remote_port) for s in specs
    ]
    assert keys == [
        (TargetKind.DAEMONSET, "ns-1", "worker", 9090),
        (TargetKind.DAEMONSET, "ns-2", "api", 8080),
        (TargetKind.DAEMONSET, "ns-2", "api", 8443),
    ]


def test_fetch_targets_includes_daemonsets():
    """The combined picker returns daemonsets when that kind is selected."""
    svc = _service("alpha", "ns-1", [80])
    ds = _daemonset("agent", "ns-1", [2020])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeDaemonSetRepo:
        def list(self, namespace: str) -> list[DaemonSet]:
            return {"ns-1": [ds]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), daemonset=FakeDaemonSetRepo())
    specs = fetch_targets_for_namespaces(
        ["ns-1"], api, kinds=[TargetKind.SERVICE, TargetKind.DAEMONSET]
    )

    kinds = {(s.target.kind, s.target.name) for s in specs}
    assert kinds == {
        (TargetKind.SERVICE, "alpha"),
        (TargetKind.DAEMONSET, "agent"),
    }


def test_fetch_targets_honors_daemonset_kind_filter():
    """Only daemonset specs are returned when kinds=[TargetKind.DAEMONSET]."""
    svc = _service("alpha", "ns-1", [80])
    ds = _daemonset("agent", "ns-1", [2020])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeDaemonSetRepo:
        def list(self, namespace: str) -> list[DaemonSet]:
            return {"ns-1": [ds]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), daemonset=FakeDaemonSetRepo())
    specs = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.DAEMONSET])

    assert {(s.target.kind, s.target.name) for s in specs} == {
        (TargetKind.DAEMONSET, "agent")
    }


def test_fetch_replicasets_for_namespaces_flattens_declared_container_ports():
    """ReplicaSets with declared container ports produce one spec per unique port; portless replicasets are omitted."""
    rs_a = _replicaset("worker", "ns-1", [9090])
    rs_b = _replicaset("api", "ns-2", [8080, 8443])
    rs_no_ports = _replicaset("sidecar", "ns-1", [])

    class FakeReplicaSetRepo:
        def list(self, namespace: str) -> list[ReplicaSet]:
            return {
                "ns-1": [rs_a, rs_no_ports],
                "ns-2": [rs_b],
            }.get(namespace, [])

    api = _make_api(replicaset=FakeReplicaSetRepo())
    specs = fetch_replicasets_for_namespaces(["ns-1", "ns-2"], api)

    keys = [
        (s.target.kind, s.target.namespace, s.target.name, s.remote_port) for s in specs
    ]
    assert keys == [
        (TargetKind.REPLICASET, "ns-1", "worker", 9090),
        (TargetKind.REPLICASET, "ns-2", "api", 8080),
        (TargetKind.REPLICASET, "ns-2", "api", 8443),
    ]


def test_fetch_targets_includes_replicasets():
    """The combined picker returns replicasets when that kind is selected."""
    svc = _service("alpha", "ns-1", [80])
    rs = _replicaset("web", "ns-1", [8080])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeReplicaSetRepo:
        def list(self, namespace: str) -> list[ReplicaSet]:
            return {"ns-1": [rs]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), replicaset=FakeReplicaSetRepo())
    specs = fetch_targets_for_namespaces(
        ["ns-1"], api, kinds=[TargetKind.SERVICE, TargetKind.REPLICASET]
    )

    kinds = {(s.target.kind, s.target.name) for s in specs}
    assert kinds == {
        (TargetKind.SERVICE, "alpha"),
        (TargetKind.REPLICASET, "web"),
    }


def test_fetch_targets_honors_replicaset_kind_filter():
    """Only replicaset specs are returned when kinds=[TargetKind.REPLICASET]."""
    svc = _service("alpha", "ns-1", [80])
    rs = _replicaset("web", "ns-1", [8080])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc]}.get(namespace, [])

    class FakeReplicaSetRepo:
        def list(self, namespace: str) -> list[ReplicaSet]:
            return {"ns-1": [rs]}.get(namespace, [])

    api = _make_api(service=FakeServiceRepo(), replicaset=FakeReplicaSetRepo())
    specs = fetch_targets_for_namespaces(["ns-1"], api, kinds=[TargetKind.REPLICASET])

    assert {(s.target.kind, s.target.name) for s in specs} == {
        (TargetKind.REPLICASET, "web")
    }
