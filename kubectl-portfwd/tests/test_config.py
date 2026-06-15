from pathlib import Path

import pytest
from portfwd.domain.config import GroupSpec, PortFwdConfig, ServicePortForwardDefaults
from portfwd.domain.errors import NoGroupsDefinedError, UnknownGroupError
from portfwd.domain.models import ServicePortForwardPlan
from portfwd.infrastructure import config_loader
from portfwd.infrastructure.config_loader import (
    get_default_service,
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
    monkeypatch.setattr(config_loader, "DEFAULT_CONFIG_PATH", tmp_path / "missing")
    assert load_config(None) == PortFwdConfig()


def test_load_config_default_invalid_yaml_returns_empty(tmp_path, monkeypatch):
    """Returns an empty config when the default path contains invalid YAML."""
    bad = tmp_path / "config.yaml"
    bad.write_text(": : :\n")
    monkeypatch.setattr(config_loader, "DEFAULT_CONFIG_PATH", bad)
    assert load_config(None) == PortFwdConfig()


def test_load_config_default_non_mapping_returns_empty(tmp_path, monkeypatch):
    """Returns an empty config when the default path root is not a mapping."""
    bad = tmp_path / "config.yaml"
    bad.write_text("- item\n")
    monkeypatch.setattr(config_loader, "DEFAULT_CONFIG_PATH", bad)
    assert load_config(None) == PortFwdConfig()


def test_load_config_default_invalid_schema_returns_empty(tmp_path, monkeypatch):
    """Returns an empty config when the default path fails validation."""
    bad = tmp_path / "config.yaml"
    bad.write_text("unknown_key: oops\n")
    monkeypatch.setattr(config_loader, "DEFAULT_CONFIG_PATH", bad)
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


def test_service_port_range_is_enforced():
    """Port numbers outside 1–65535 are rejected."""
    base = {"name": "svc", "namespace": "ns"}
    with pytest.raises(ValidationError):
        ServicePortForwardDefaults.model_validate(
            {**base, "remote_port": 0, "local_port": 80}
        )
    with pytest.raises(ValidationError):
        ServicePortForwardDefaults.model_validate(
            {**base, "remote_port": 80, "local_port": 65536}
        )


def test_get_default_service_returns_matching_entry():
    """Returns the config entry when name, namespace, and remote_port all match."""
    entry = ServicePortForwardDefaults(
        name="svc", namespace="ns", remote_port=80, local_port=9000
    )
    config = PortFwdConfig(defaults=[entry])
    assert get_default_service(config, "svc", "ns", 80) == entry


def test_get_default_service_returns_last_match_when_multiple_defaults_exist():
    """Returns the last matching entry when several defaults share the same key."""
    first = ServicePortForwardDefaults(
        name="svc", namespace="ns", remote_port=80, local_port=9000
    )
    second = ServicePortForwardDefaults(
        name="svc", namespace="ns", remote_port=80, local_port=9001
    )
    config = PortFwdConfig(defaults=[first, second])
    assert get_default_service(config, "svc", "ns", 80) == second


def test_get_default_service_returns_none_when_no_match():
    """Returns None when nothing in defaults matches the given service / namespace / port."""
    entry = ServicePortForwardDefaults(
        name="svc", namespace="ns", remote_port=80, local_port=9000
    )
    config = PortFwdConfig(defaults=[entry])
    assert get_default_service(config, "svc", "ns", 443) is None
    assert get_default_service(config, "svc", "other-ns", 80) is None
    assert get_default_service(config, "other-svc", "ns", 80) is None


def test_load_config_non_mapping_yaml_raises(tmp_path):
    """Raises ValueError when the YAML root is a sequence, not a mapping."""
    bad = tmp_path / "config.yaml"
    bad.write_text("- item1\n- item2\n")
    with pytest.raises(ValueError, match="must be a YAML mapping"):
        load_config(bad)


def test_get_group_returns_matching_group():
    """get_group returns the GroupSpec whose name matches."""
    group = GroupSpec(name="backend", services=[])
    config = PortFwdConfig(groups=[group])
    assert config.get_group("backend") == group


def test_get_group_raises_no_groups_defined_when_config_has_none():
    """get_group raises NoGroupsDefinedError when the config has no groups."""
    config = PortFwdConfig()
    with pytest.raises(NoGroupsDefinedError):
        config.get_group("any")


def test_get_group_raises_unknown_group_with_available_names():
    """get_group raises UnknownGroupError listing available names when the group is missing."""
    config = PortFwdConfig(
        groups=[
            GroupSpec(name="alpha", services=[]),
            GroupSpec(name="beta", services=[]),
        ]
    )
    with pytest.raises(UnknownGroupError, match="available: alpha, beta"):
        config.get_group("missing")


def test_to_plan_produces_correct_service_port_forward_plan():
    """to_plan() converts a defaults entry to a ServicePortForwardPlan."""
    defaults = ServicePortForwardDefaults(
        name="auth",
        namespace="kube-public",
        remote_port=80,
        local_port=9000,
    )
    plan = defaults.to_plan()
    assert isinstance(plan, ServicePortForwardPlan)
    assert plan.target.name == "auth"
    assert plan.target.namespace == "kube-public"
    assert plan.remote_port == 80
    assert plan.local_port == 9000
