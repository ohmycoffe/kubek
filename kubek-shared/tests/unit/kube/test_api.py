from kubek.kube._infrastructure.client import KubernetesClient
from kubek.kube.api import KubeFacade
from kubek.kube.dto.kind import Kind
from kubek_test_utils.factories import make_deployment
from kubek_test_utils.fakes import FakeKubeClient


def test_from_client_wires_repositories_and_config():
    client = FakeKubeClient().add_namespaced_resource(
        Kind.DEPLOYMENT,
        "api",
        make_deployment("api", "test-ns"),
        namespace="test-ns",
    )
    facade = KubeFacade.from_client(client)

    assert facade.current_config == client.current_config
    assert facade.deployment.get(name="api", namespace="test-ns") is not None
    assert facade.deployment.get(name="missing", namespace="test-ns") is None


def test_from_config_builds_facade_from_kubernetes_client(monkeypatch):
    fake_client = FakeKubeClient()
    monkeypatch.setattr(
        KubernetesClient,
        "from_config",
        classmethod(lambda cls, config=None: fake_client),
    )

    facade = KubeFacade.from_config()

    assert facade.current_config == fake_client.current_config
