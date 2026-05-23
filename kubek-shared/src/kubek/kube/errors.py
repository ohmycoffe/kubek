from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from kubek.core import KubekException


class ClientException(KubekException):
    """Low-level Kubernetes/API error."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.__context = context or {}

    def context(self) -> Mapping[str, Any]:
        """Additional context about the error, guaranteed to be immutable."""
        return deepcopy(self.__context)


class NotFoundException(ClientException):
    """Resource not found."""


class AccessDeniedException(ClientException):
    """Unauthorized access."""
