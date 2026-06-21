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


def test_container_ports_null_parses_as_none():
    """Container.ports accepts null from the Kubernetes API (omitted ports)."""
    container = Container.model_validate({"ports": None})

    assert container.ports is None


def test_container_port_protocol_is_optional():
    """ContainerPort.protocol is None when not present in the raw data."""
    raw = {"ports": [{"containerPort": 80}]}
    container = Container.model_validate(raw)

    assert container.ports[0].protocol is None


def test_env_value_from_parses_field_ref_camel_case():
    """EnvValueFrom.field_ref is populated from the camelCase 'fieldRef' field."""
    raw = {
        "env": [
            {
                "name": "MY_POD_NAME",
                "valueFrom": {"fieldRef": {"fieldPath": "metadata.name"}},
            }
        ]
    }
    container = Container.model_validate(raw)

    value_from = container.env[0].value_from
    assert value_from is not None
    assert value_from.field_ref is not None
    assert value_from.field_ref.field_path == "metadata.name"
    assert value_from.secret_key_ref is None
    assert value_from.config_map_key_ref is None


def test_env_value_from_parses_field_ref_snake_case():
    """EnvValueFrom.field_ref is populated from the snake_case 'field_ref' field (k8s client dicts)."""
    raw = {
        "env": [
            {
                "name": "MY_POD_NAMESPACE",
                "value_from": {"field_ref": {"field_path": "metadata.namespace"}},
            }
        ]
    }
    container = Container.model_validate(raw)

    value_from = container.env[0].value_from
    assert value_from is not None
    assert value_from.field_ref is not None
    assert value_from.field_ref.field_path == "metadata.namespace"


def test_env_value_from_parses_resource_field_ref():
    """EnvValueFrom.resource_field_ref is populated from 'resourceFieldRef'."""
    raw = {
        "env": [
            {
                "name": "CPU_LIMIT",
                "valueFrom": {
                    "resourceFieldRef": {
                        "containerName": "app",
                        "resource": "limits.cpu",
                    }
                },
            }
        ]
    }
    container = Container.model_validate(raw)

    value_from = container.env[0].value_from
    assert value_from is not None
    assert value_from.resource_field_ref is not None
    assert value_from.resource_field_ref.resource == "limits.cpu"
