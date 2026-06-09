from abc import ABC, abstractmethod
from typing import Any, Generic, Protocol, TypeVar, cast

from pydantic import BaseModel

from kubek.kube.contracts import KubeClient
from kubek.kube.errors import KubeApiNotFoundError

T = TypeVar("T", bound=BaseModel)
L = TypeVar("L", bound=BaseModel)


class HasItems(Protocol[T]):
    items: list[T]


class BaseKubernetesRepository(ABC, Generic[T, L]):
    list_model: type[L]
    item_model: type[T]

    def __init__(self, client: KubeClient):
        self._client = client  # abstract dependency

    @abstractmethod
    def _fetch_list(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        pass

    @abstractmethod
    def _fetch_one(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        pass

    def list(self, *args: Any, **kwargs: Any) -> list[T]:
        try:
            raw = self._fetch_list(*args, **kwargs)
        except KubeApiNotFoundError:
            return []
        model = self.list_model.model_validate(raw)
        return cast("HasItems[T]", model).items

    def get(self, *args: Any, **kwargs: Any) -> T | None:
        try:
            raw = self._fetch_one(*args, **kwargs)
        except KubeApiNotFoundError:
            return None
        return self.item_model.model_validate(raw)
