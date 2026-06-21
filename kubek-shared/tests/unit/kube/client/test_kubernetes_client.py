from unittest.mock import MagicMock

import pytest
from kubek.kube._infrastructure.client import KubernetesClient
from kubek.kube.config import ResolvedKubeConfig


@pytest.fixture
def session():
    return MagicMock(
        current_config=ResolvedKubeConfig(context="test", namespace="default"),
    )


@pytest.fixture
def client(session):
    return KubernetesClient(session=session)


def _api_response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.to_dict.return_value = payload
    return response


@pytest.mark.parametrize(
    "method_name,api_attr,api_method,args,kwargs,expected_api_args",
    [
        (
            "get_namespaces",
            "core_v1",
            "list_namespace",
            (),
            {},
            (),
        ),
        (
            "get_namespace",
            "core_v1",
            "read_namespace",
            ("kube-system",),
            {},
            ("kube-system",),
        ),
        (
            "get_services",
            "core_v1",
            "list_namespaced_service",
            (),
            {},
            ("default",),
        ),
        (
            "get_service",
            "core_v1",
            "read_namespaced_service",
            ("api",),
            {},
            ("api", "default"),
        ),
        (
            "get_deployments",
            "apps_v1",
            "list_namespaced_deployment",
            (),
            {},
            ("default",),
        ),
        (
            "get_deployment",
            "apps_v1",
            "read_namespaced_deployment",
            ("web",),
            {},
            ("web", "default"),
        ),
        (
            "get_statefulsets",
            "apps_v1",
            "list_namespaced_stateful_set",
            (),
            {},
            ("default",),
        ),
        (
            "get_statefulset",
            "apps_v1",
            "read_namespaced_stateful_set",
            ("db",),
            {},
            ("db", "default"),
        ),
        (
            "get_daemonsets",
            "apps_v1",
            "list_namespaced_daemon_set",
            (),
            {},
            ("default",),
        ),
        (
            "get_daemonset",
            "apps_v1",
            "read_namespaced_daemon_set",
            ("agent",),
            {},
            ("agent", "default"),
        ),
        (
            "get_jobs",
            "batch_v1",
            "list_namespaced_job",
            (),
            {},
            ("default",),
        ),
        (
            "get_job",
            "batch_v1",
            "read_namespaced_job",
            ("worker",),
            {},
            ("worker", "default"),
        ),
        (
            "get_cronjobs",
            "batch_v1",
            "list_namespaced_cron_job",
            (),
            {},
            ("default",),
        ),
        (
            "get_cronjob",
            "batch_v1",
            "read_namespaced_cron_job",
            ("nightly",),
            {},
            ("nightly", "default"),
        ),
        (
            "get_secrets",
            "core_v1",
            "list_namespaced_secret",
            (),
            {},
            ("default",),
        ),
        (
            "get_secret",
            "core_v1",
            "read_namespaced_secret",
            ("db",),
            {},
            ("db", "default"),
        ),
        (
            "get_configmaps",
            "core_v1",
            "list_namespaced_config_map",
            (),
            {},
            ("default",),
        ),
        (
            "get_configmap",
            "core_v1",
            "read_namespaced_config_map",
            ("app",),
            {},
            ("app", "default"),
        ),
        (
            "get_workflowtemplates",
            "custom",
            "list_namespaced_custom_object",
            (),
            {},
            {
                "group": "argoproj.io",
                "version": "v1alpha1",
                "plural": "workflowtemplates",
                "namespace": "default",
            },
        ),
        (
            "get_workflowtemplate",
            "custom",
            "get_namespaced_custom_object",
            ("data-processor",),
            {},
            {
                "group": "argoproj.io",
                "version": "v1alpha1",
                "plural": "workflowtemplates",
                "namespace": "default",
                "name": "data-processor",
            },
        ),
    ],
)
def test_client_methods_call_kubernetes_api_and_return_dict(
    client,
    session,
    method_name,
    api_attr,
    api_method,
    args,
    kwargs,
    expected_api_args,
):
    payload = {"metadata": {"name": "x"}}
    api = getattr(session, api_attr)
    getattr(api, api_method).return_value = _api_response(payload)

    result = getattr(client, method_name)(*args, **kwargs)

    if isinstance(expected_api_args, dict):
        getattr(api, api_method).assert_called_once_with(**expected_api_args)
    else:
        getattr(api, api_method).assert_called_once_with(*expected_api_args)
    assert result == payload


def test_client_uses_explicit_namespace(session, client):
    session.core_v1.read_namespaced_service.return_value = _api_response(
        {"metadata": {"name": "api"}}
    )

    client.get_service("api", namespace="staging")

    session.core_v1.read_namespaced_service.assert_called_once_with("api", "staging")


def test_current_config_returns_session_config(session, client):
    assert client.current_config is session.current_config
