from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from kubek.kube.dto.service import Service
from kubek.net import get_deterministic_port
from portfwd.application.port_forwarding.planner import (
    build_port_forward_plan,
    resolve_local_port,
    resolve_pod_remote_port,
    resolve_service_remote_port,
)
from portfwd.application.ports import KubeGateway
from portfwd.domain.errors import (
    AmbiguousPodPortError,
    AmbiguousServicePortError,
    MissingNamespaceError,
    NoPodPortsError,
    NoServicePortsError,
    PodNotFoundError,
    ServiceNotFoundError,
)
from portfwd.domain.models import (
    PortForwardSpec,
    TargetKind,
    TargetRef,
)
from portfwd_test_utils.fakes import make_pod

_FALLBACK_PORT = 50_000
_SVC_DETERMINISTIC_PORT = get_deterministic_port(
    name="svc", namespace="ns", service_port=80
)


@pytest.fixture
def mock_is_port_free():
    with patch(
        "portfwd.application.port_forwarding.planner.is_port_free"
    ) as is_port_free:
        yield is_port_free


@pytest.fixture
def mock_find_free_port():
    with patch(
        "portfwd.application.port_forwarding.planner.find_free_port"
    ) as find_free_port:
        yield find_free_port


def _make_service(name: str, namespace: str, ports: list[int]) -> Service:
    return Service.model_validate(
        {
            "metadata": {"name": name, "namespace": namespace},
            "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
        }
    )


def _make_api(namespace=None, services=None, pods=None) -> KubeGateway:
    """Minimal fake KubeFacade: only the attributes used by build_port_forward_plan."""
    services_map = {(ns, name): svc for (ns, name), svc in (services or {}).items()}
    pods_map = {(ns, name): pod for (ns, name), pod in (pods or {}).items()}

    class FakeServiceRepo:
        def get(self, name, namespace=None):
            return services_map.get((namespace, name))

    class FakePodRepo:
        def get(self, name, namespace=None):
            return pods_map.get((namespace, name))

    return cast(
        KubeGateway,
        SimpleNamespace(
            current_config=SimpleNamespace(namespace=namespace, context=None),
            service=FakeServiceRepo(),
            pod=FakePodRepo(),
        ),
    )


class TestTargetRef:
    def test_str_without_namespace(self):
        ref = TargetRef(kind=TargetKind.POD, name="api")
        assert str(ref) == "pod/api"

    def test_str_with_namespace(self):
        ref = TargetRef(kind=TargetKind.SERVICE, name="api", namespace="default")
        assert str(ref) == "svc/default/api"


class TestResolvedTargetRef:
    def test_str_includes_kind_and_namespace(self):
        from portfwd.domain.models import ResolvedTargetRef, TargetKind

        ref = ResolvedTargetRef(
            kind=TargetKind.SERVICE, name="api", namespace="default"
        )
        assert str(ref) == "svc/default/api"


class TestResolveLocalPort:
    def test_uses_deterministic_port_when_free(self, mock_is_port_free):
        """Returns the deterministic port when the port is free."""
        mock_is_port_free.return_value = True
        assert resolve_local_port("svc", "ns", 80) == _SVC_DETERMINISTIC_PORT

    def test_falls_back_to_free_port_when_deterministic_taken(
        self, mock_is_port_free, mock_find_free_port
    ):
        """Falls back to find_free_port when the deterministic port is already in use."""
        mock_is_port_free.return_value = False
        mock_find_free_port.return_value = _FALLBACK_PORT
        assert resolve_local_port("svc", "ns", 80) == _FALLBACK_PORT


class TestResolveRemotePort:
    def test_returns_single_port(self):
        """Returns the port number when the service has exactly one port."""
        service = _make_service("svc", "ns", [8080])
        assert resolve_service_remote_port(service) == 8080

    def test_raises_when_no_ports(self):
        """NoServicePortsError is raised for services with no declared ports."""
        service = _make_service("svc", "ns", [])
        with pytest.raises(NoServicePortsError):
            resolve_service_remote_port(service)

    def test_raises_when_multiple_ports(self):
        """AmbiguousServicePortError is raised when the service exposes more than one port."""
        service = _make_service("svc", "ns", [80, 8080])
        with pytest.raises(AmbiguousServicePortError):
            resolve_service_remote_port(service)


class TestResolvePodRemotePort:
    def test_returns_single_port(self):
        """Returns the container port when the pod declares exactly one."""
        pod = make_pod("api", "ns", [[8080]])
        assert resolve_pod_remote_port(pod) == 8080

    def test_returns_single_unique_port_across_containers(self):
        """Duplicate container ports across containers collapse to one."""
        pod = make_pod("api", "ns", [[8080], [8080]])
        assert resolve_pod_remote_port(pod) == 8080

    def test_raises_when_no_ports(self):
        """NoPodPortsError is raised when the pod declares no container ports."""
        pod = make_pod("api", "ns", [[]])
        with pytest.raises(NoPodPortsError):
            resolve_pod_remote_port(pod)

    def test_raises_when_multiple_ports(self):
        """AmbiguousPodPortError is raised when the pod exposes more than one port."""
        pod = make_pod("api", "ns", [[80, 8080]])
        with pytest.raises(AmbiguousPodPortError):
            resolve_pod_remote_port(pod)


class TestBuildPortForwardPlan:
    def test_uses_spec_ports_directly(self):
        """Ports declared in the spec are forwarded unchanged."""
        svc = _make_service("auth", "ns", [80])
        api = _make_api(namespace="ns", services={("ns", "auth"): svc})
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.SERVICE, name="auth", namespace="ns"),
            remote_port=443,
            local_port=9443,
        )
        plan = build_port_forward_plan(spec, api)
        assert plan.remote_port == 443
        assert plan.local_port == 9443
        assert plan.target.namespace == "ns"
        assert plan.target.name == "auth"

    def test_uses_api_namespace_when_absent_in_spec(self):
        """api.current_config.namespace is used when the spec has no namespace."""
        svc = _make_service("auth", "kube-public", [80])
        api = _make_api(
            namespace="kube-public", services={("kube-public", "auth"): svc}
        )
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.SERVICE, name="auth"),
            remote_port=80,
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, api)
        assert plan.target.namespace == "kube-public"

    def test_raises_when_namespace_missing(self):
        """MissingNamespaceError is raised when neither spec nor api supplies a namespace."""
        svc = _make_service("auth", "ns", [80])
        api = _make_api(namespace=None, services={("ns", "auth"): svc})
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.SERVICE, name="auth"),
            remote_port=80,
            local_port=9000,
        )
        with pytest.raises(MissingNamespaceError):
            build_port_forward_plan(spec, api)

    def test_raises_when_service_not_found(self):
        """ServiceNotFoundError is raised when the Service does not exist in the namespace."""
        api = _make_api(namespace="ns")
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.SERVICE, name="missing", namespace="ns"),
            remote_port=80,
            local_port=9000,
        )
        with pytest.raises(ServiceNotFoundError):
            build_port_forward_plan(spec, api)

    def test_resolves_remote_port_from_service(self):
        """When spec has no remote_port, it is read from the service's single declared port."""
        svc = _make_service("auth", "ns", [8080])
        api = _make_api(namespace="ns", services={("ns", "auth"): svc})
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.SERVICE, name="auth", namespace="ns"),
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, api)
        assert plan.remote_port == 8080

    def test_resolves_remote_port_from_pod(self):
        """A pod spec without a remote_port reads the pod's single container port."""
        pod = make_pod("worker", "ns", [[9090]])
        api = _make_api(namespace="ns", pods={("ns", "worker"): pod})
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.POD, name="worker", namespace="ns"),
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, api)
        assert plan.target.kind == TargetKind.POD
        assert plan.remote_port == 9090

    def test_pod_spec_port_used_directly(self):
        """An explicit remote_port is forwarded unchanged for pods."""
        pod = make_pod("worker", "ns", [[9090]])
        api = _make_api(namespace="ns", pods={("ns", "worker"): pod})
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.POD, name="worker", namespace="ns"),
            remote_port=8080,
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, api)
        assert plan.remote_port == 8080

    def test_raises_when_pod_not_found(self):
        """PodNotFoundError is raised when the Pod does not exist in the namespace."""
        api = _make_api(namespace="ns")
        spec = PortForwardSpec(
            target=TargetRef(kind=TargetKind.POD, name="missing", namespace="ns"),
            remote_port=80,
            local_port=9000,
        )
        with pytest.raises(PodNotFoundError):
            build_port_forward_plan(spec, api)
