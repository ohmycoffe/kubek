from pathlib import Path

import portfwd.config as config_module
import pytest
from portfwd.config import (
    GroupSpec,
    PortFwdConfig,
    ServicePortForwardDefaults,
    load_config,
)
from pydantic import ValidationError

EXAMPLE_CONFIG = Path(__file__).parent.parent / "docs" / "example_config.yaml"


def test_should_load_config():
    """Parses the example YAML config from docs/ and checks it round-trips to the expected Config object."""
    assert EXAMPLE_CONFIG.exists()
    config = load_config(EXAMPLE_CONFIG)

    assert config.defaults == [
        ServicePortForwardDefaults(
            name="auth-service",
            namespace="kube-public",
            local_port=50013,
            remote_port=80,
        ),
        ServicePortForwardDefaults(
            name="user-service",
            namespace="kube-public",
            local_port=50014,
            remote_port=80,
        ),
    ]
    assert config.groups == [
        GroupSpec(
            name="backend",
            services=[
                ServicePortForwardDefaults(
                    namespace="kube-public",
                    name="auth-service",
                    remote_port=80,
                    local_port=50013,
                ),
                ServicePortForwardDefaults(
                    namespace="kube-public",
                    name="user-service-2",
                    remote_port=80,
                    local_port=50010,
                ),
            ],
        )
    ]


def test_load_config_default_missing_returns_empty(tmp_path, monkeypatch):
    """Returns a default Config when the default path does not exist."""
    monkeypatch.setattr(config_module, "DEFAULT_CONFIG_PATH", tmp_path / "missing")
    assert load_config(None) == PortFwdConfig()


def test_load_config_explicit_missing_raises(tmp_path):
    """Raises FileNotFoundError when an explicit config path does not exist."""
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")


def test_load_config_invalid_schema_raises(tmp_path):
    """Raises ValidationError when the YAML contains an unrecognised key."""
    bad = tmp_path / "config.yaml"
    bad.write_text("unknown_key: oops\n")
    with pytest.raises(ValidationError):
        load_config(bad)


def test_load_config_invalid_yaml_raises(tmp_path):
    """Raises ValueError when the file is not valid YAML."""
    bad = tmp_path / "config.yaml"
    bad.write_text(": : :\n")
    with pytest.raises(ValueError, match="Invalid YAML"):
        load_config(bad)


def test_group_name_custom_is_reserved():
    """Rejects a group named 'custom' because it conflicts with interactive mode."""
    with pytest.raises(ValidationError):
        GroupSpec(name="custom", services=[])


@pytest.mark.parametrize(
    "model,data",
    [
        (
            ServicePortForwardDefaults,
            {"name": "svc", "namespace": "ns", "remote_port": 0, "local_port": 80},
        ),
        (
            ServicePortForwardDefaults,
            {"name": "svc", "namespace": "ns", "remote_port": 80, "local_port": 65536},
        ),
        (
            ServicePortForwardDefaults,
            {"name": "", "namespace": "ns", "remote_port": 80, "local_port": 80},
        ),
        (
            ServicePortForwardDefaults,
            {"name": "svc", "namespace": "ns", "remote_port": 80},
        ),
        (PortFwdConfig, {"unknown": "value"}),
    ],
)
def test_validation_rejects_invalid_input(model, data):
    """Rejects invalid model inputs with a ValidationError."""
    with pytest.raises(ValidationError):
        model.model_validate(data)
