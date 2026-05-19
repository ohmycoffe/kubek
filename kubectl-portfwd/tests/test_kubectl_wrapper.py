from unittest.mock import AsyncMock, patch

import pytest
from kubek.kube.client import KubectlWrapper
from portfwd.kube import start_port_forward


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, []),
        ({"kubeconfig": "/tmp/kcfg"}, ["--kubeconfig", "/tmp/kcfg"]),
        ({"context": "ctx"}, ["--context", "ctx"]),
        (
            {"kubeconfig": "/tmp/kcfg", "context": "ctx", "namespace": "ns"},
            ["--kubeconfig", "/tmp/kcfg", "--context", "ctx", "--namespace", "ns"],
        ),
    ],
)
def test_global_kubectl_args(kwargs, expected):
    assert KubectlWrapper.global_kubectl_args(**kwargs) == expected


def test_wrapper_passes_kubeconfig_to_global_args():
    kubectl = KubectlWrapper(
        context="ctx", namespace="ns", kubeconfig="/path/to/config"
    )
    assert KubectlWrapper.global_kubectl_args(
        kubeconfig=kubectl.kubeconfig,
        context=kubectl.context,
        namespace=kubectl.namespace,
    ) == [
        "--kubeconfig",
        "/path/to/config",
        "--context",
        "ctx",
        "--namespace",
        "ns",
    ]


def test_start_port_forward_passes_kubeconfig_and_context():
    async def _run() -> None:
        with patch(
            "portfwd.kube.asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.pid = 1
            mock_exec.return_value = mock_proc
            await start_port_forward(
                namespace="ns",
                service="svc",
                local_port=5000,
                remote_port=80,
                context="my-ctx",
                kubeconfig="/tmp/kcfg",
            )

            cmd = mock_exec.call_args.args
            assert cmd[0] == "kubectl"
            assert list(cmd[1:6]) == [
                "--kubeconfig",
                "/tmp/kcfg",
                "--context",
                "my-ctx",
                "port-forward",
            ]

    import asyncio

    asyncio.run(_run())
