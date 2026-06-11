import json
from types import SimpleNamespace

import pytest
from kubek.kube.dto import Service, ServiceList
from portfwd.application.queries import (
    _convert_services_to_specs as _convert_to_spec,
)
from portfwd.application.queries import (
    _resolve_group,
    fetch_services_for_namespaces,
)
from portfwd.domain.config import GroupSpec
from portfwd.domain.errors import NoGroupsDefinedError, UnknownGroupError
from portfwd.domain.models import ServicePortForwardSpec


def _service(name: str, namespace: str, ports: list[int]) -> Service:
    raw = {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": [{"port": p, "protocol": "TCP"} for p in ports]},
    }
    return Service.model_validate(raw)


def test_convert_to_spec_sorted_by_namespace_name_and_port():
    """Interactive picker specs are ordered for stable display."""
    services = [
        _service("zebra", "ns", [80]),
        _service("alpha", "ns", [9000, 80]),
    ]
    specs = _convert_to_spec(services)
    assert specs == [
        ServicePortForwardSpec.model_validate(
            {
                "target": {"namespace": "ns", "name": "alpha"},
                "remote_port": 80,
            }
        ),
        ServicePortForwardSpec.model_validate(
            {
                "target": {"namespace": "ns", "name": "alpha"},
                "remote_port": 9000,
            }
        ),
        ServicePortForwardSpec.model_validate(
            {
                "target": {"namespace": "ns", "name": "zebra"},
                "remote_port": 80,
            }
        ),
    ]


def test_convert_to_spec_accepts_unsorted_service_list_json():
    """Sorting applies even when kubectl returns items out of order."""
    raw = json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "zebra", "namespace": "b"},
                    "spec": {"ports": [{"port": 80, "protocol": "TCP"}]},
                },
                {
                    "metadata": {"name": "alpha", "namespace": "a"},
                    "spec": {"ports": [{"port": 80, "protocol": "TCP"}]},
                },
            ]
        }
    )
    services = ServiceList.model_validate_json(raw).items
    specs = _convert_to_spec(services)
    keys = [(s.target.namespace, s.target.name, s.remote_port) for s in specs]
    assert keys == [("a", "alpha", 80), ("b", "zebra", 80)]


def _make_group(name: str) -> GroupSpec:
    return GroupSpec(name=name, services=[])


def test_resolve_group_returns_matching_group():
    """Returns the GroupSpec whose name matches."""
    groups = [_make_group("alpha"), _make_group("beta")]
    assert _resolve_group("beta", groups).name == "beta"


def test_resolve_group_raises_unknown_group_with_available_names():
    """UnknownGroupError lists the available group names when the requested one is missing."""
    groups = [_make_group("alpha"), _make_group("beta")]
    with pytest.raises(UnknownGroupError, match="available: alpha, beta"):
        _resolve_group("missing", groups)


def test_resolve_group_raises_no_groups_defined_when_config_has_none():
    """NoGroupsDefinedError is raised when the config contains no groups at all."""
    with pytest.raises(NoGroupsDefinedError):
        _resolve_group("any", [])


def test_fetch_services_for_namespaces_combines_services_from_each_namespace():
    """Services from all requested namespaces are returned, sorted and flattened."""
    svc_a = _service("alpha", "ns-1", [80])
    svc_b = _service("beta", "ns-2", [443])

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return {"ns-1": [svc_a], "ns-2": [svc_b]}.get(namespace, [])

    api = SimpleNamespace(service=FakeServiceRepo())
    specs = fetch_services_for_namespaces(["ns-1", "ns-2"], api)

    keys = [(s.target.namespace, s.target.name, s.remote_port) for s in specs]
    assert ("ns-1", "alpha", 80) in keys
    assert ("ns-2", "beta", 443) in keys


def test_fetch_services_for_namespaces_returns_empty_for_empty_namespaces():
    """Returns an empty list when no namespaces are provided."""

    class FakeServiceRepo:
        def list(self, namespace: str) -> list[Service]:
            return []

    api = SimpleNamespace(service=FakeServiceRepo())
    assert fetch_services_for_namespaces([], api) == []
