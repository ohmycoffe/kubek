from kubek.kube._infrastructure.repositories._base import BaseKubernetesRepository
from kubek.kube.contracts.repositories import SecretRepository
from kubek.kube.dto.secret import Secret, SecretList


class KubernetesSecretRepository(
    BaseKubernetesRepository[Secret, SecretList],
    SecretRepository,
):
    list_model = SecretList
    item_model = Secret

    def _fetch_list(self, namespace: str | None = None) -> dict:
        return self._client.get_secrets(namespace)

    def _fetch_one(self, name: str, namespace: str | None = None) -> dict:
        return self._client.get_secret(name=name, namespace=namespace)
