from kubek.kube.api import KubeFacade
from kubek.kube.dto.kind import Kind
from kubek_test_utils.factories import make_deployment
from kubek_test_utils.fakes import FakeKubeClient


async def test_from_client_wires_repositories_and_config():
    client = FakeKubeClient().add_namespaced_resource(
        Kind.DEPLOYMENT,
        "api",
        make_deployment("api", "test-ns"),
        namespace="test-ns",
    )
    facade = KubeFacade.from_client(client)

    assert facade.current_config == client.current_config
    assert await facade.deployment.get(name="api", namespace="test-ns") is not None
    assert await facade.deployment.get(name="missing", namespace="test-ns") is None


async def test_from_config_opens_session_and_yields_facade(monkeypatch):
    fake_client = FakeKubeClient()
    entered: list[bool] = []
    exited: list[bool] = []

    class FakeSession:
        current_config = fake_client.current_config

        async def __aenter__(self):
            entered.append(True)
            return self

        async def __aexit__(self, *args):
            exited.append(True)

    @classmethod
    async def fake_session_from_config(cls, config=None):
        return FakeSession()

    monkeypatch.setattr(
        "kubek.kube.api.KubeSession.from_config",
        fake_session_from_config,
    )
    monkeypatch.setattr(
        "kubek.kube.api.KubernetesClient",
        lambda session: fake_client,
    )

    async with KubeFacade.from_config() as facade:
        assert facade.current_config == fake_client.current_config

    assert entered == [True]
    assert exited == [True]


def test_from_session_delegates_to_from_client(monkeypatch):
    fake_session = object()
    fake_client = FakeKubeClient()
    captured: list[object] = []

    def fake_kubernetes_client(session):
        captured.append(session)
        return fake_client

    monkeypatch.setattr(
        "kubek.kube.api.KubernetesClient",
        fake_kubernetes_client,
    )

    facade = KubeFacade.from_session(fake_session)  # type: ignore[arg-type]

    assert captured == [fake_session]
    assert facade.current_config == fake_client.current_config
