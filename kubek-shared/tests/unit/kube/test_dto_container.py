from kubek.kube.dto.container import Container


def test_container_parses_container_port_from_camel_case():
    """ContainerPort.container_port is populated from the camelCase 'containerPort' field."""
    raw = {"ports": [{"containerPort": 8080}]}
    container = Container.model_validate(raw)

    assert len(container.ports) == 1
    assert container.ports[0].container_port == 8080


def test_container_defaults_to_empty_ports():
    """Container.ports defaults to an empty list when no ports are declared."""
    container = Container.model_validate({})

    assert container.ports == []


def test_container_port_protocol_is_optional():
    """ContainerPort.protocol is None when not present in the raw data."""
    raw = {"ports": [{"containerPort": 80}]}
    container = Container.model_validate(raw)

    assert container.ports[0].protocol is None
