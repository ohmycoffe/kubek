from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from kubek.kube.dto.service import Service
from kubek.net import get_deterministic_port
from portfwd.application.port_forwarding.planner import (
    build_port_forward_plan,
    resolve_local_port,
    resolve_remote_port,
)
from portfwd.application.ports import KubeGateway
from portfwd.domain.config import PortFwdConfig, ServicePortForwardDefaults
from portfwd.domain.errors import (
    AmbiguousServicePortError,
    MissingNamespaceError,
    NoServicePortsError,
    ServiceNotFoundError,
)
from portfwd.domain.models import NamespacedServiceNameSpec, ServicePortForwardSpec

_FALLBACK_PORT = 50_000
_SVC_DETERMINISTIC_PORT = get_deterministic_port(
    service="svc", namespace="ns", service_port=80
)
_SVC_CONFIG = ServicePortForwardDefaults(
    name="svc", namespace="ns", remote_port=80, local_port=9000
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


def _make_api(namespace=None, services=None) -> KubeGateway:
    """Minimal fake KubeFacade: only the attributes used by build_port_forward_plan."""
    services_map = {(ns, name): svc for (ns, name), svc in (services or {}).items()}

    class FakeServiceRepo:
        def get(self, name, namespace=None):
            return services_map.get((namespace, name))

    return cast(
        KubeGateway,
        SimpleNamespace(
            current_config=SimpleNamespace(namespace=namespace, context=None),
            service=FakeServiceRepo(),
        ),
    )


class TestNamespacedServiceNameSpec:
    def test_str_without_namespace(self):
        spec = NamespacedServiceNameSpec(name="api")
        assert str(spec) == "api"

    def test_str_with_namespace(self):
        spec = NamespacedServiceNameSpec(name="api", namespace="default")
        assert str(spec) == "default/api"


class TestNamespacedServiceNamePlan:
    def test_str_includes_namespace(self):
        from portfwd.domain.models import NamespacedServiceNamePlan

        plan = NamespacedServiceNamePlan(name="api", namespace="default")
        assert str(plan) == "default/api"


class TestResolveLocalPort:
    def test_uses_configured_port(self):
        """Returns the configured local_port when a matching config entry exists."""
        config = PortFwdConfig(defaults=[_SVC_CONFIG])
        assert resolve_local_port("svc", "ns", 80, config) == 9000

    def test_uses_deterministic_port_when_free(self, mock_is_port_free):
        """Returns the deterministic port when no config match and the port is free."""
        mock_is_port_free.return_value = True
        config = PortFwdConfig()
        assert resolve_local_port("svc", "ns", 80, config) == _SVC_DETERMINISTIC_PORT

    def test_falls_back_to_free_port_when_deterministic_taken(
        self, mock_is_port_free, mock_find_free_port
    ):
        """Falls back to find_free_port when the deterministic port is already in use."""
        mock_is_port_free.return_value = False
        mock_find_free_port.return_value = _FALLBACK_PORT
        config = PortFwdConfig()
        assert resolve_local_port("svc", "ns", 80, config) == _FALLBACK_PORT

    def test_ignores_config_from_other_namespace(
        self, mock_is_port_free, mock_find_free_port
    ):
        """Does not use a config entry whose namespace does not match."""
        mock_is_port_free.return_value = False
        mock_find_free_port.return_value = _FALLBACK_PORT
        other_ns = ServicePortForwardDefaults(
            name="svc", namespace="other-ns", remote_port=80, local_port=9000
        )
        config = PortFwdConfig(defaults=[other_ns])
        assert resolve_local_port("svc", "ns", 80, config) == _FALLBACK_PORT


class TestResolveRemotePort:
    def test_returns_single_port(self):
        """Returns the port number when the service has exactly one port."""
        service = _make_service("svc", "ns", [8080])
        assert resolve_remote_port(service) == 8080

    def test_raises_when_no_ports(self):
        """NoServicePortsError is raised for services with no declared ports."""
        service = _make_service("svc", "ns", [])
        with pytest.raises(NoServicePortsError):
            resolve_remote_port(service)

    def test_raises_when_multiple_ports(self):
        """AmbiguousServicePortError is raised when the service exposes more than one port."""
        service = _make_service("svc", "ns", [80, 8080])
        with pytest.raises(AmbiguousServicePortError):
            resolve_remote_port(service)


class TestBuildPortForwardPlan:
    def test_uses_spec_ports_directly(self):
        """Ports declared in the spec are forwarded unchanged."""
        svc = _make_service("auth", "ns", [80])
        api = _make_api(namespace="ns", services={("ns", "auth"): svc})
        spec = ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
            remote_port=443,
            local_port=9443,
        )
        plan = build_port_forward_plan(spec, PortFwdConfig(), api)
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
        spec = ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(name="auth"),
            remote_port=80,
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, PortFwdConfig(), api)
        assert plan.target.namespace == "kube-public"

    def test_raises_when_namespace_missing(self):
        """MissingNamespaceError is raised when neither spec nor api supplies a namespace."""
        svc = _make_service("auth", "ns", [80])
        api = _make_api(namespace=None, services={("ns", "auth"): svc})
        spec = ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(name="auth"),
            remote_port=80,
            local_port=9000,
        )
        with pytest.raises(MissingNamespaceError):
            build_port_forward_plan(spec, PortFwdConfig(), api)

    def test_raises_when_service_not_found(self):
        """ServiceNotFoundError is raised when the Service does not exist in the namespace."""
        api = _make_api(namespace="ns")
        spec = ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(name="missing", namespace="ns"),
            remote_port=80,
            local_port=9000,
        )
        with pytest.raises(ServiceNotFoundError):
            build_port_forward_plan(spec, PortFwdConfig(), api)

    def test_resolves_remote_port_from_service(self):
        """When spec has no remote_port, it is read from the service's single declared port."""
        svc = _make_service("auth", "ns", [8080])
        api = _make_api(namespace="ns", services={("ns", "auth"): svc})
        spec = ServicePortForwardSpec(
            target=NamespacedServiceNameSpec(name="auth", namespace="ns"),
            local_port=9000,
        )
        plan = build_port_forward_plan(spec, PortFwdConfig(), api)
        assert plan.remote_port == 8080
