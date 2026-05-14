from pathlib import Path

import pytest
from portfwd.config import (
    GroupRef,
    PortFwdConfig,
    QualifiedName,
    ServiceConfig,
    load_config,
)
from pydantic import ValidationError

EXAMPLE_CONFIG = Path(__file__).parent.parent / "docs" / "example_config.yaml"


def test_should_load_config():
    """Parses the example YAML config from docs/ and checks it round-trips to the expected Config object."""
    assert EXAMPLE_CONFIG.exists()
    config = load_config(EXAMPLE_CONFIG)

    assert config.ports == [
        ServiceConfig(
            name="auth-service",
            namespace="kube-public",
            local_port=50013,
            remote_port=80,
        ),
        ServiceConfig(
            name="user-service",
            namespace="kube-public",
            local_port=50014,
            remote_port=80,
        ),
    ]
    assert config.groups == [
        GroupRef(
            name="backend",
            services=[
                QualifiedName(namespace="kube-public", name="auth-service"),
                QualifiedName(namespace="kube-public", name="user-service"),
            ],
        ),
        GroupRef(
            name="ddr",
            services=[
                QualifiedName(namespace="kube-public", name="auth-service"),
            ],
        ),
    ]


def test_load_config_missing_file_returns_defaults(tmp_path):
    """Returns a default Config when the config file does not exist."""
    config = load_config(tmp_path / "nonexistent.yaml")
    assert config == PortFwdConfig()


def test_load_config_invalid_schema_returns_defaults(tmp_path):
    """Returns a default Config when the YAML contains an unrecognised key."""
    bad = tmp_path / "config.yaml"
    bad.write_text("unknown_key: oops\n")
    config = load_config(bad)
    assert config == PortFwdConfig()


def test_load_config_invalid_yaml_returns_defaults(tmp_path):
    """Returns a default Config when the file is not valid YAML."""
    bad = tmp_path / "config.yaml"
    bad.write_text(": : :\n")
    config = load_config(bad)
    assert config == PortFwdConfig()


@pytest.mark.parametrize(
    "model,data",
    [
        (
            ServiceConfig,
            {"name": "svc", "namespace": "ns", "remote_port": 0, "local_port": 80},
        ),
        (
            ServiceConfig,
            {"name": "svc", "namespace": "ns", "remote_port": 80, "local_port": 65536},
        ),
        (
            ServiceConfig,
            {"name": "", "namespace": "ns", "remote_port": 80, "local_port": 80},
        ),
        (ServiceConfig, {"name": "svc", "namespace": "ns", "remote_port": 80}),
        (PortFwdConfig, {"unknown": "value"}),
    ],
)
def test_validation_rejects_invalid_input(model, data):
    """Rejects invalid model inputs with a ValidationError."""
    with pytest.raises(ValidationError):
        model.model_validate(data)
