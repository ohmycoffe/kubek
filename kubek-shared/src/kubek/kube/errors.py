from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from kubek.core import KubekError


class KubeClientError(KubekError):
    """Base error for Kubernetes client failures."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.__context = dict(context or {})

    def context(self) -> Mapping[str, Any]:
        """Additional context about the error."""
        return deepcopy(self.__context)


class KubeConfigError(KubeClientError):
    """Failed to load or use kubeconfig."""


class KubeApiError(KubeClientError):
    """Kubernetes API request failed."""


class KubeApiNotFoundError(KubeApiError):
    """Kubernetes resource was not found."""


class KubeAuthenticationError(KubeApiError):
    """Authentication with Kubernetes failed."""


class KubeAccessDeniedError(KubeApiError):
    """Access to Kubernetes resource was denied."""


class KubeSecretKeyError(KubeClientError):
    """Expected key was not found in Kubernetes Secret."""


class KubeSecretDecodeError(KubeClientError):
    """Kubernetes Secret value could not be decoded."""
