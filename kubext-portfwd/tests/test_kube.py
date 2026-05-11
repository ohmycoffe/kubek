import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from portfwd.kube import (
    KubernetesService,
    RunningPortForward,
    find_running_port_forwards,
    parse_context,
    parse_namespaces,
    parse_services,
)


def _create_dummy_process_info(
    name: str, cmdline: list[str], pid: int
) -> SimpleNamespace:
    return SimpleNamespace(info={"name": name, "cmdline": cmdline, "pid": pid})


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("my-cluster\n", "my-cluster"),
        ("arn:aws:eks:us-east-1:123456789012:cluster/my-cluster", "my-cluster"),
        ("", ""),
        ("   \n", ""),
    ],
)
def test_parse_context(raw, expected):
    """Strips whitespace and extracts the cluster name from plain strings and EKS ARNs."""
    assert parse_context(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        (
            json.dumps(
                {
                    "items": [
                        {"metadata": {"name": "default"}},
                        {"metadata": {"name": "kube-system"}},
                    ]
                }
            ),
            ["default", "kube-system"],
        ),
        (json.dumps({"items": []}), []),
    ],
)
def test_parse_namespaces(raw, expected):
    """Parses namespace names from kubectl JSON output."""
    assert parse_namespaces(raw) == expected


def test_parse_services_basic():
    """Parses a single service with one port from kubectl JSON output."""
    raw = json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "my-svc"},
                    "spec": {"ports": [{"port": 80, "protocol": "TCP"}]},
                },
            ]
        }
    )
    tested = parse_services(raw)
    assert tested == [KubernetesService(name="my-svc", port=80, protocol="TCP")]


def test_parse_services_skips_kubernetes():
    """Excludes the built-in 'kubernetes' service from the parsed result."""
    raw = json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "kubernetes"},
                    "spec": {"ports": [{"port": 443, "protocol": "TCP"}]},
                },
                {
                    "metadata": {"name": "my-svc"},
                    "spec": {"ports": [{"port": 80, "protocol": "TCP"}]},
                },
            ]
        }
    )
    tested = parse_services(raw)
    assert tested == [KubernetesService(name="my-svc", port=80, protocol="TCP")]


def test_parse_services_multiple_ports_expanded():
    """Expands a service with multiple ports into one KubernetesService entry per port."""
    raw = json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "my-svc"},
                    "spec": {
                        "ports": [
                            {"port": 80, "protocol": "TCP"},
                            {"port": 8080, "protocol": "TCP"},
                        ]
                    },
                },
            ]
        }
    )
    tested = parse_services(raw)
    assert tested == [
        KubernetesService(name="my-svc", port=80, protocol="TCP"),
        KubernetesService(name="my-svc", port=8080, protocol="TCP"),
    ]


def test_parse_services_sorted_by_name_then_port():
    """Returns services sorted alphabetically by name, then by port number."""
    raw = json.dumps(
        {
            "items": [
                {
                    "metadata": {"name": "zebra"},
                    "spec": {"ports": [{"port": 80, "protocol": "TCP"}]},
                },
                {
                    "metadata": {"name": "alpha"},
                    "spec": {
                        "ports": [
                            {"port": 9000, "protocol": "TCP"},
                            {"port": 80, "protocol": "TCP"},
                        ]
                    },
                },
            ]
        }
    )
    tested = parse_services(raw)
    assert tested == [
        KubernetesService(name="alpha", port=80, protocol="TCP"),
        KubernetesService(name="alpha", port=9000, protocol="TCP"),
        KubernetesService(name="zebra", port=80, protocol="TCP"),
    ]


def test_parse_services_empty():
    """Returns an empty list when the items array contains no services."""
    assert parse_services(json.dumps({"items": []})) == []


def test_find_running_port_forwards_match():
    """Detects a running port-forward for a known service using the svc/ prefix."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        name="kubectl",
        cmdline=["kubectl", "port-forward", "svc/my-svc", "5000:80", "-n", "default"],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        result = find_running_port_forwards(services)
    assert result == [
        RunningPortForward(name="my-svc", remote_port=80, local_port=5000, pid=1234)
    ]


def test_find_running_port_forwards_port_only_uses_remote_as_local():
    """Uses the remote port as local_port when the cmdline specifies only a single port number."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        name="kubectl",
        cmdline=["kubectl", "port-forward", "svc/my-svc", "80", "-n", "default"],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        result = find_running_port_forwards(services)
    assert result == [
        RunningPortForward(name="my-svc", remote_port=80, local_port=80, pid=1234)
    ]


def test_find_running_port_forwards_service_prefix_variant():
    """Matches a port-forward using the service/ prefix in addition to svc/."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        "kubectl",
        cmdline=[
            "kubectl",
            "port-forward",
            "service/my-svc",
            "5000:80",
            "-n",
            "default",
        ],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        result = find_running_port_forwards(services)
    assert result == [
        RunningPortForward(name="my-svc", remote_port=80, local_port=5000, pid=1234)
    ]


def test_find_running_port_forwards_unknown_service_ignored():
    """Ignores a kubectl process forwarding a service not in the known services list."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        "kubectl",
        cmdline=[
            "kubectl",
            "port-forward",
            "svc/other-svc",
            "5000:80",
            "-n",
            "default",
        ],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        assert find_running_port_forwards(services) == []


def test_find_running_port_forwards_non_kubectl_process_ignored():
    """Ignores processes that are not kubectl, even if their cmdline contains port-forward args."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        name="python",
        cmdline=["python", "script.py", "svc/my-svc", "5000:80"],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        assert find_running_port_forwards(services) == []


def test_ignore_port_forwards_other_than_service():
    """Ignores kubectl processes forwarding a pod/ resource rather than a service."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    proc = _create_dummy_process_info(
        name="kubectl",
        cmdline=["kubectl", "port-forward", "pod/my-pod", "5000:80", "-n", "default"],
        pid=1234,
    )
    with patch("portfwd.kube.psutil.process_iter", return_value=[proc]):
        assert find_running_port_forwards(services) == []


def test_find_running_port_forwards_no_processes():
    """Returns an empty list when no running processes are found."""
    services = [KubernetesService(name="my-svc", port=80, protocol="TCP")]
    with patch("portfwd.kube.psutil.process_iter", return_value=[]):
        assert find_running_port_forwards(services) == []
