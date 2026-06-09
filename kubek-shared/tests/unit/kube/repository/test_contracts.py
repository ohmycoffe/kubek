from collections.abc import Callable

import pytest
from kubek.kube._infrastructure.repositories.configmap import (
    KubernetesConfigMapRepository,
)
from kubek.kube._infrastructure.repositories.deployment import (
    KubernetesDeploymentRepository,
)
from kubek.kube._infrastructure.repositories.namespace import (
    KubernetesNamespaceRepository,
)
from kubek.kube._infrastructure.repositories.secret import KubernetesSecretRepository
from kubek.kube._infrastructure.repositories.service import KubernetesServiceRepository
from kubek.kube._infrastructure.repositories.workflowtemplate import (
    KubernetesWorkflowTemplateRepository,
)
from kubek.kube.dto.kind import Kind
from kubek_test_utils.factories import (
    make_configmap,
    make_deployment,
    make_namespace,
    make_secret,
    make_service,
    make_workflowtemplate,
)
from kubek_test_utils.fakes import FakeKubeClient

_TEST_NAMESPACE = "test-namespace-1"


_REPOSITORIES_MAP = {
    Kind.DEPLOYMENT: KubernetesDeploymentRepository,
    Kind.SECRET: KubernetesSecretRepository,
    Kind.CONFIGMAP: KubernetesConfigMapRepository,
    Kind.WORKFLOWTEMPLATE: KubernetesWorkflowTemplateRepository,
    Kind.NAMESPACE: KubernetesNamespaceRepository,
    Kind.SERVICE: KubernetesServiceRepository,
}


_EXPECTED_RESOURCES = [
    (Kind.DEPLOYMENT, _TEST_NAMESPACE, "deployment1"),
    (Kind.DEPLOYMENT, _TEST_NAMESPACE, "deployment2"),
    (Kind.SERVICE, _TEST_NAMESPACE, "service1"),
    (Kind.SERVICE, _TEST_NAMESPACE, "service2"),
    (Kind.SECRET, _TEST_NAMESPACE, "secret1"),
    (Kind.SECRET, _TEST_NAMESPACE, "secret2"),
    (Kind.CONFIGMAP, _TEST_NAMESPACE, "configmap1"),
    (Kind.CONFIGMAP, _TEST_NAMESPACE, "configmap2"),
    (Kind.WORKFLOWTEMPLATE, _TEST_NAMESPACE, "workflowtemplate1"),
    (Kind.WORKFLOWTEMPLATE, _TEST_NAMESPACE, "workflowtemplate2"),
]

_EXPECTED_NAMESPACES = [
    _TEST_NAMESPACE,
    "test-namespace-2",
]

_FACTORIES: dict[Kind, Callable[[str, str], dict]] = {
    Kind.DEPLOYMENT: make_deployment,
    Kind.SECRET: make_secret,
    Kind.CONFIGMAP: make_configmap,
    Kind.WORKFLOWTEMPLATE: make_workflowtemplate,
    Kind.SERVICE: make_service,
}


@pytest.fixture
def fake_client():
    fake_client = FakeKubeClient()

    for namespace in _EXPECTED_NAMESPACES:
        fake_client.add_namespace(
            namespace,
            make_namespace(namespace),
        )

    for resource, namespace, name in _EXPECTED_RESOURCES:
        factory = _FACTORIES[resource]
        fake_client.add_namespaced_resource(
            resource,
            name,
            factory(name, namespace),
            namespace=namespace,
        )
    return fake_client


class TestCommonKubernetesRepositories:
    @pytest.mark.parametrize(
        "kind",
        [
            Kind.DEPLOYMENT,
            Kind.SERVICE,
            Kind.SECRET,
            Kind.CONFIGMAP,
            Kind.WORKFLOWTEMPLATE,
        ],
    )
    def test_list_should_return_many(self, kind: Kind, fake_client):
        repo = _REPOSITORIES_MAP[kind](fake_client)
        result = repo.list(namespace=_TEST_NAMESPACE)

        expected = [
            name
            for k, ns, name in _EXPECTED_RESOURCES
            if ns == _TEST_NAMESPACE and k == kind
        ]
        assert len(result) == len(expected)
        assert [item.metadata.name for item in result] == expected

    @pytest.mark.parametrize(
        "kind",
        [
            Kind.DEPLOYMENT,
            Kind.SERVICE,
            Kind.SECRET,
            Kind.CONFIGMAP,
            Kind.WORKFLOWTEMPLATE,
        ],
    )
    def test_get_should_return_one(self, kind: Kind, fake_client):
        repo = _REPOSITORIES_MAP[kind](fake_client)
        expected = [
            name
            for k, ns, name in _EXPECTED_RESOURCES
            if ns == _TEST_NAMESPACE and k == kind
        ][0]
        result = repo.get(name=expected, namespace=_TEST_NAMESPACE)

        assert result is not None
        assert result.metadata.name == expected

    @pytest.mark.parametrize(
        "kind",
        [
            Kind.DEPLOYMENT,
            Kind.SERVICE,
            Kind.SECRET,
            Kind.CONFIGMAP,
            Kind.WORKFLOWTEMPLATE,
        ],
    )
    def test_list_should_return_empty_on_missing_namespace(
        self, kind: Kind, fake_client
    ):
        repo = _REPOSITORIES_MAP[kind](fake_client)
        result = repo.list(namespace="missing-namespace")

        assert result == []

    @pytest.mark.parametrize(
        "kind",
        [
            Kind.DEPLOYMENT,
            Kind.SERVICE,
            Kind.SECRET,
            Kind.CONFIGMAP,
            Kind.WORKFLOWTEMPLATE,
        ],
    )
    def test_get_should_return_none_on_missing(self, kind: Kind, fake_client):
        repo = _REPOSITORIES_MAP[kind](fake_client)
        expected = [
            name
            for k, ns, name in _EXPECTED_RESOURCES
            if ns == _TEST_NAMESPACE and k == kind
        ][0]
        # missing namespace should return None
        result = repo.get(name=expected, namespace="missing-namespace")

        assert result is None
        # ... missing name should return None as well
        result = repo.get(name="missing-name", namespace=_TEST_NAMESPACE)
        assert result is None


class TestKubernetesNamespaceRepository:
    def test_list_should_return_all_namespaces(self, fake_client):
        repo = KubernetesNamespaceRepository(fake_client)
        result = repo.list()

        assert len(result) == len(_EXPECTED_NAMESPACES)
        assert [item.metadata.name for item in result] == _EXPECTED_NAMESPACES

    def test_get_should_return_one_namespace(self, fake_client):
        repo = KubernetesNamespaceRepository(fake_client)
        expected = _EXPECTED_NAMESPACES[0]
        result = repo.get(name=expected)

        assert result is not None
        assert result.metadata.name == expected

    def test_get_should_return_none_on_missing_namespace(self, fake_client):
        repo = KubernetesNamespaceRepository(fake_client)
        # missing namespace should return None
        result = repo.get(name="missing-namespace")

        assert result is None
