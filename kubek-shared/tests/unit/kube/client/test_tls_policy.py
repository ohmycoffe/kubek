from kubek.kube._infrastructure.client import KubeSession
from kubek.kube.config import KubeConfig


def _patch_kubeconfig(monkeypatch, captured):
    async def fake_load(*, config_file, context, client_configuration):
        captured["cfg"] = client_configuration

    async def fake_close(self):
        pass

    monkeypatch.setattr("kubek.kube._infrastructure.client.load_kube_config", fake_load)
    monkeypatch.setattr(
        "kubek.kube._infrastructure.client.list_kube_config_contexts",
        lambda config_file=None: ([], {"name": "ctx", "context": {"namespace": "ns"}}),
    )
    monkeypatch.setattr(
        "kubek.kube._infrastructure.client.client.ApiClient.close",
        fake_close,
    )


async def test_strict_x509_always_relaxed_and_verification_on_by_default(monkeypatch):
    captured = {}
    _patch_kubeconfig(monkeypatch, captured)

    async with await KubeSession.from_config(KubeConfig()) as session:
        assert captured["cfg"].disable_strict_ssl_verification is True
        assert captured["cfg"].verify_ssl is True
        assert session.current_config.namespace == "ns"


async def test_insecure_skip_tls_verify_disables_verification(monkeypatch):
    captured = {}
    _patch_kubeconfig(monkeypatch, captured)

    async with await KubeSession.from_config(KubeConfig(skip_tls_verify=True)):
        assert captured["cfg"].verify_ssl is False
        assert captured["cfg"].disable_strict_ssl_verification is True
