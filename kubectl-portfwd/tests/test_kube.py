import json

from kubek.kube.schemas import Service, ServiceList


def _service_json(name: str, namespace: str, ports: list[dict]) -> dict:
    return {
        "metadata": {"name": name, "namespace": namespace},
        "spec": {"ports": ports},
    }


def test_service_list_parses_single_service():
    """Parses kubectl ServiceList JSON into pydantic models."""
    raw = json.dumps(
        {
            "items": [
                _service_json("my-svc", "ns", [{"port": 80, "protocol": "TCP"}]),
            ]
        }
    )
    services = ServiceList.model_validate_json(raw)
    assert services.items == [
        Service.model_validate(
            _service_json("my-svc", "ns", [{"port": 80, "protocol": "TCP"}])
        )
    ]


def test_service_list_empty():
    """Returns an empty list when the items array contains no services."""
    services = ServiceList.model_validate_json(json.dumps({"items": []}))
    assert services.items == []


def test_service_list_multiple_ports():
    """Parses a service with multiple ports."""
    item = _service_json(
        "my-svc",
        "ns",
        [
            {"port": 80, "protocol": "TCP"},
            {"port": 8080, "protocol": "TCP"},
        ],
    )
    services = ServiceList.model_validate_json(json.dumps({"items": [item]}))
    assert len(services.items[0].spec.ports) == 2
    assert [p.port for p in services.items[0].spec.ports] == [80, 8080]
