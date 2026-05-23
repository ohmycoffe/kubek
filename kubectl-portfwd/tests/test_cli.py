import json

from kubek.kube.dto import Service, ServiceList
from portfwd.models import ServicePortForwardSpec
from portfwd.use_case import convert_services_to_specs as _convert_to_spec


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
