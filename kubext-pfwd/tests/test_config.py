from pathlib import Path

import pytest
from pfwd.config import Config, ServiceConfig, load_config
from pydantic import ValidationError

EXAMPLE_CONFIG = Path(__file__).parent.parent / "docs" / "example_config.toml"


def test_should_load_config():
    """Parses the example config from docs/ and checks it round-trips to the expected Config object."""
    assert EXAMPLE_CONFIG.exists()
    config = load_config(EXAMPLE_CONFIG)

    assert config == Config(
        default_namespace="kube-public",
        ports=[
            ServiceConfig(
                name="auth-service",
                namespace="kube-public",
                remote_port=80,
                local_port=50000,
            ),
            ServiceConfig(
                name="user-service",
                namespace="kube-public",
                remote_port=8080,
                local_port=50001,
            ),
        ],
    )


def test_load_config_missing_file_returns_defaults(tmp_path):
    """Returns a default Config when the config file does not exist."""
    config = load_config(tmp_path / "nonexistent.toml")
    assert config == Config()


def test_load_config_invalid_schema_returns_defaults(tmp_path):
    """Returns a default Config when the TOML contains an unrecognised key."""
    bad = tmp_path / "config.toml"
    bad.write_text('[ports]\nunknown_key = "oops"\n')
    config = load_config(bad)
    assert config == Config()


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
        (Config, {"unknown": "value"}),
    ],
)
def test_validation_rejects_invalid_input(model, data):
    """Rejects invalid model inputs with a ValidationError."""
    with pytest.raises(ValidationError):
        model.model_validate(data)
